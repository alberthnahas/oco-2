import os
import time
import h5py
import numpy as np
import pandas as pd
import xarray as xr
from scipy.spatial import cKDTree

# === START CLOCK ===
start_time = time.time()

# === SET PARAMETERS ===
year = "25"
month = "04"
date_string = f"20{year}-{month}-01"
base_dir = os.path.expanduser("~/Documents/Satellite/oco2")
data_dir = os.path.join(base_dir, "1-data")
csv_dir = os.path.join(base_dir, "4-csv")
nc_dir = os.path.join(base_dir, "3-netcdf")
os.makedirs(csv_dir, exist_ok=True)
os.makedirs(nc_dir, exist_ok=True)

pattern = f"{year}{month}"
csvname = os.path.join(csv_dir, f"CO2_monthly_{month}_20{year}.csv")
ncname = os.path.join(nc_dir, f"CO2_mx_monthly_{month}_20{year}.nc")
ncname2 = os.path.join(nc_dir, f"CO2_sns_monthly_{month}_20{year}.nc")

# === FIND FILES ===
file_list = []
for root, _, files in os.walk(data_dir):
    for file in files:
        if pattern in file and file.endswith(".h5"):
            file_list.append(os.path.join(root, file))
print(f"There are {len(file_list)} h5 file(s) in this directory.")

# === READ DATA FROM FILES ===
records = []
for file in file_list:
    with h5py.File(file, "r") as f:
        co2 = f["/RetrievalResults/xco2"][()] * 1e6
        lat = f["/RetrievalGeometry/retrieval_latitude"][()]
        lon = f["/RetrievalGeometry/retrieval_longitude"][()]
        print(f"File: {os.path.basename(file)} → shape: co2={co2.shape}, lat={lat.shape}, lon={lon.shape}")
        co2 = co2.flatten()
        lat = lat.flatten()
        lon = lon.flatten()
        med = np.median(co2)
        records.extend([{"lat": la, "lon": lo, "co2": c, "aco2": c - med}
                        for la, lo, c in zip(lat, lon, co2)])

if not records:
    raise ValueError("No valid data extracted from HDF5 files. Please check contents.")

df = pd.DataFrame(records)
if not all(col in df.columns for col in ['lat', 'lon']):
    raise KeyError("Missing 'lat' or 'lon' columns in DataFrame.")

# === FILTER AND SAVE TO CSV ===
df = df[(df["lat"] >= -15) & (df["lat"] <= 30) & (df["lon"] >= 90) & (df["lon"] <= 145)]
df.to_csv(csvname, index=False, float_format="%.6f", na_rep="NA", quoting=1)

# === GRID TEMPLATE ===
lon_vals = np.arange(90, 145.5, 0.5).astype(np.float32)
lat_vals = np.arange(-15, 30.5, 0.5).astype(np.float32)
grid_lon, grid_lat = np.meshgrid(lon_vals, lat_vals)

# === IDW INTERPOLATION FUNCTION ===
def idw_interpolation(xy, values, xi, yi, power=2, k=10):
    grid_shape = xi.shape
    interp_points = np.column_stack((xi.ravel(), yi.ravel()))
    tree = cKDTree(xy)
    dists, idxs = tree.query(interp_points, k=k, p=2, workers=-1)
    dists[dists == 0] = 1e-10
    weights = 1.0 / dists**power
    weights /= weights.sum(axis=1, keepdims=True)
    zi = np.sum(weights * values[idxs], axis=1)
    return zi.reshape(grid_shape)

# === PERFORM IDW INTERPOLATION ===
xy = df[["lon", "lat"]].values
co2_idw = idw_interpolation(xy, df["co2"].values, grid_lon, grid_lat)
aco2_idw = idw_interpolation(xy, df["aco2"].values, grid_lon, grid_lat)

# === CREATE XARRAY DATASET (with [time, lon, lat]) ===
def create_dataset(grid, varname, longname):
    data_array = xr.DataArray(
        data=grid[np.newaxis, :, :],  # [time, lat, lon]
        dims=["time", "lat", "lon"],
        coords={
            "time": [np.datetime64(date_string)],
            "lat": ("lat", lat_vals),
            "lon": ("lon", lon_vals)
        },
        name=varname,
        attrs={
            "units": "ppm",
            "long_name": longname
        }
    )
    # CF-1.6 axis metadata so GrADS' sdfopen can auto-detect X/Y
    data_array.lon.attrs["standard_name"] = "longitude"
    data_array.lon.attrs["units"] = "degrees_east"
    data_array.lon.attrs["axis"] = "X"

    data_array.lat.attrs["standard_name"] = "latitude"
    data_array.lat.attrs["units"] = "degrees_north"
    data_array.lat.attrs["axis"] = "Y"    
    
    data_array.lon.encoding['_FillValue'] = None
    data_array.lat.encoding['_FillValue'] = None
    return data_array

da_co2 = create_dataset(co2_idw, "co2", "CO2 mixing ratio")
da_aco2 = create_dataset(aco2_idw, "aco2", "Difference of CO2 from median")

# === SAVE TO NETCDF ===
ds_co2 = xr.Dataset({"co2": da_co2})
ds_aco2 = xr.Dataset({"aco2": da_aco2})
ds_co2.attrs["title"] = "Interpolated CO2 Data (IDW)"
ds_aco2.attrs["title"] = "Interpolated CO2 Difference (IDW)"
ds_co2.attrs["Conventions"] = "CF-1.6"
ds_aco2.attrs["Conventions"] = "CF-1.6"
ds_co2.to_netcdf(ncname)
ds_aco2.to_netcdf(ncname2)

# === END CLOCK ===
elapsed = round((time.time() - start_time) / 60, 2)
print(f"✅ NetCDF saved in [time, lon, lat]. Time taken: {elapsed} minutes.")

