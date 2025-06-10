import os
import time
import geopandas as gpd
import xarray as xr
import rioxarray
import pandas as pd

# === START TIMER ===
start_time = time.time()

# === SET WORKING DIRECTORY ===
base_dir = os.path.expanduser("~/Documents/Satellite/oco2/2-spatial/")
os.chdir(base_dir)

# === DEFINE FILES ===
shapefile_path = "Indonesia_38_Provinsi.shp"
netcdf_file = "CO2_mx_monthly_05_2025.nc"
output_csv = "oco2.provinsi.202505.csv"

# === LOAD SHAPEFILE ===
gdf = gpd.read_file(shapefile_path)
gdf = gdf.to_crs("EPSG:4326")

# === OPEN NETCDF FILE ===
ds = xr.open_dataset(netcdf_file)
print("Available variables:", ds.data_vars)

# === IDENTIFY THE CO2 VARIABLE ===
co2_varname = list(ds.data_vars.keys())[0]
co2_data = ds[co2_varname]

if not co2_data.rio.crs:
    co2_data = co2_data.rio.write_crs("EPSG:4326", inplace=False)

co2_layer = co2_data.isel(time=0)

# === ZONAL STATISTICS PER PROVINCE ===
oco2_list = []

for i, row in gdf.iterrows():
    prov_name = row['PROVINSI']
    print(f"Processing: {prov_name}")
    
    try:
        clipped = co2_layer.rio.clip([row.geometry], gdf.crs, drop=True)
        if clipped.notnull().any():
            co2_mean = float(clipped.mean(skipna=True).values)
        else:
            raise ValueError("No data found in clipped region")
    except Exception as e:
        print(f"  → Polygon clip failed: {e}")
        try:
            centroid = row.geometry.centroid
            nearest_value = co2_layer.sel(
                lat=centroid.y, lon=centroid.x, method="nearest"
            ).values.item()
            co2_mean = float(nearest_value)
            print(f"  → Used centroid value: {co2_mean}")
        except Exception as e2:
            print(f"  → Centroid fallback also failed: {e2}")
            co2_mean = float("nan")

    date_str = pd.to_datetime(str(ds.time.values[0])).strftime("%Y-%m-%d")
    year = int(date_str[:4])
    month = int(date_str[5:7])

    oco2_list.append({
        "Year": year,
        "Month": month,
        "Provinsi": prov_name,
        "CO2": co2_mean
    })

# === CREATE DATAFRAME ===
oco2_df = pd.DataFrame(oco2_list)

# === SUMMARY STATS ===
valid_data = oco2_df.dropna(subset=["CO2"])
avg_val = valid_data["CO2"].mean()
min_val = valid_data["CO2"].min()
max_val = valid_data["CO2"].max()
prov_min = valid_data.loc[valid_data["CO2"].idxmin(), "Provinsi"]
prov_max = valid_data.loc[valid_data["CO2"].idxmax(), "Provinsi"]

# === ADD SUMMARY ROWS ===
summary_rows = pd.DataFrame([
    {},  # blank row
    {"Year": "", "Month": "", "Provinsi": "Average CO2", "CO2": round(avg_val, 2)},
    {"Year": "", "Month": "", "Provinsi": f"Maximum CO2 ({prov_max})", "CO2": round(max_val, 2)},
    {"Year": "", "Month": "", "Provinsi": f"Minimum CO2 ({prov_min})", "CO2": round(min_val, 2)}
])

final_df = pd.concat([oco2_df, summary_rows], ignore_index=True)

# === SAVE TO CSV ===
final_df.to_csv(output_csv, index=False, na_rep="NA", quoting=1)

# === PRINT SUMMARY TO CONSOLE ===
print(f"\nSummary for {month:02}/{year}:")
print(f"  • Average CO2: {avg_val:.2f} ppm")
print(f"  • Maximum CO2: {max_val:.2f} ppm in {prov_max}")
print(f"  • Minimum CO2: {min_val:.2f} ppm in {prov_min}")

# === PRINT TIME INFO ===
elapsed = round((time.time() - start_time) / 60, 2)
print(f"\nWork has been completed in {elapsed} minutes")
print(f"This information was collected on {pd.Timestamp.now().date()}")

