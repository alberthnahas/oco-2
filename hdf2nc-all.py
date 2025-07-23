######################################################################################
# This is a Python script to create monthly raster maps from OCO-2 .h5 files.        #
#                                                                                    #
# Key Features:                                                                      #
# - Processes data in a batch loop for a specified date range.                       #
# - Calculates REGIONAL ANOMALY using a GeoJSON for regional definitions.            #
# - Uses an IMPROVED Inverse Distance Weighting (IDW) with cross-validation          #
#   to find the optimal interpolation power.                                         #
# - Outputs data into CF-compliant NetCDF files with yyyymm filenames.               #
#                                                                                    #
# Original script by Alberth Nahas                                                   #
# Version 1.0.5 (Python) (2025-07-20)                                                #
######################################################################################

import os
import time
import glob
import pandas as pd
import numpy as np
import xarray as xr
import h5py
import geopandas as gpd
import rioxarray 
from scipy.spatial import cKDTree

# --- SCRIPT SETUP ---
overall_start_clock = time.time()
print("Script started: Batch processing OCO-2 HDF5 files with regional anomaly.")

# 1. Define base directories
base_dir = os.path.expanduser("./")
data_dir = os.path.join(base_dir, "./")
output_dir = os.path.join(base_dir, "./")
os.makedirs(output_dir, exist_ok=True)
print(f"Searching for HDF5 files in: {os.path.abspath(data_dir)}")
print(f"All output NetCDF files will be saved in: {os.path.abspath(output_dir)}")

# 2. Define the date range for the main processing loop
date_range = pd.date_range(start='2025-06-01', end='2025-06-30', freq='MS')
print(f"Processing data for {len(date_range)} months, from {date_range[0].date()} to {date_range[-1].date()}.")

# 3. Pre-load static data (GeoJSON regions and grid definition)
print("Pre-loading static data (GeoJSON regions and interpolation grid)...")
try:
    geojson_path = "indonesia_38prov.geojson"
    admin_boundaries = gpd.read_file(geojson_path)
    PROVINCE_COLUMN = 'provinsi'
    conditions = [
        admin_boundaries[PROVINCE_COLUMN].str.upper().isin(['ACEH', 'SUMATERA UTARA', 'SUMATERA BARAT', 'RIAU', 'KEPULAUAN RIAU', 'JAMBI', 'BENGKULU', 'SUMATERA SELATAN', 'KEPULAUAN BANGKA BELITUNG', 'LAMPUNG']),
        admin_boundaries[PROVINCE_COLUMN].str.upper().isin(['BANTEN', 'DKI JAKARTA', 'JAWA BARAT', 'JAWA TENGAH', 'DI YOGYAKARTA', 'JAWA TIMUR']),
        admin_boundaries[PROVINCE_COLUMN].str.upper().isin(['BALI', 'NUSA TENGGARA BARAT', 'NUSA TENGGARA TIMUR']),
        admin_boundaries[PROVINCE_COLUMN].str.upper().isin(['KALIMANTAN BARAT', 'KALIMANTAN TENGAH', 'KALIMANTAN SELATAN', 'KALIMANTAN TIMUR', 'KALIMANTAN UTARA']),
        admin_boundaries[PROVINCE_COLUMN].str.upper().isin(['SULAWESI UTARA', 'GORONTALO', 'SULAWESI TENGAH', 'SULAWESI BARAT', 'SULAWESI SELATAN', 'SULAWESI TENGGARA']),
        admin_boundaries[PROVINCE_COLUMN].str.upper().isin(['MALUKU', 'MALUKU UTARA', 'PAPUA BARAT', 'PAPUA', 'PAPUA SELATAN', 'PAPUA TENGAH', 'PAPUA PEGUNUNGAN', 'PAPUA BARAT DAYA'])
    ]
    regions = ['Sumatra', 'Java', 'Bali-Nusa Tenggara', 'Kalimantan', 'Sulawesi', 'Maluku-Papua']
    admin_boundaries['region'] = np.select(conditions, regions, default='Other/Sea')
    regions_gdf = admin_boundaries[['region', 'geometry']].dissolve(by='region', aggfunc='sum').reset_index()
    print("Successfully loaded and processed GeoJSON regions.")
except Exception as e:
    print(f"FATAL ERROR: Could not load or process GeoJSON file '{geojson_path}'. Please ensure it exists and is valid.")
    print(f"Error details: {e}")
    exit()

# 4. Define interpolation grid
bbox = {"xmin": 95, "ymin": -11, "xmax": 141, "ymax": 6}
resolution = 0.05
grid_x = np.arange(bbox["xmin"], bbox["xmax"], resolution).astype(np.float32)
grid_y = np.arange(bbox["ymin"], bbox["ymax"], resolution).astype(np.float32)
grid_xx, grid_yy = np.meshgrid(grid_x, grid_y)
target_points_flat = np.vstack((grid_xx.ravel(), grid_yy.ravel())).T

print("Setup complete. Starting main processing loop.")


# --- MODIFIED: IDW Function ---
# The function now returns a flat array to be compatible with both
# single-point cross-validation and full-grid interpolation.
def idw_interpolation(source_pts, source_vals, target_pts, n_neighbors=10, p=2.0):
    """Performs IDW interpolation using SciPy's cKDTree for efficiency."""
    kdtree = cKDTree(source_pts)
    distances, indices = kdtree.query(target_pts, k=n_neighbors, workers=-1)
    
    # Handle cases where only one point is queried
    if distances.ndim == 1:
        distances = distances.reshape(-1, n_neighbors)
        indices = indices.reshape(-1, n_neighbors)

    # Avoid division by zero for exact matches
    distances[distances == 0] = 1e-12 
    weights = 1.0 / (distances ** p)
    
    # Calculate weighted sum
    sum_of_weights = np.sum(weights, axis=1, keepdims=True)
    # Avoid division by zero if all neighbors have zero weight (or are NaN)
    np.divide(weights, sum_of_weights, out=weights, where=sum_of_weights!=0)
    
    neighbor_values = source_vals[indices]
    interpolated_values = np.sum(neighbor_values * weights, axis=1)
    
    # Return the flat array of interpolated values
    return interpolated_values


# --- MAIN PROCESSING LOOP ---
for process_date in date_range:
    month_start_time = time.time()
    
    year_str_yy = process_date.strftime('%y')
    month_str = process_date.strftime('%m')
    full_year_str = process_date.strftime('%Y')
    
    print(f"\n--- Processing data for {full_year_str}-{month_str} ---")

    try:
        # Part 1: Find data files
        search_pattern = f"*{year_str_yy}{month_str}*_B11213_*.h5"
        search_path = os.path.join(data_dir, "**", search_pattern)
        print(f"Searching with pattern: {search_path}")
        file_list = glob.glob(search_path, recursive=True)
        
        if not file_list:
            print(f"Warning: No OCO-2 HDF5 files found for {full_year_str}-{month_str}. Skipping.")
            continue
        print(f"Found {len(file_list)} HDF5 file(s) for this month.")
        
        # Part 2: Read data from HDF5 files
        records = []
        for file_path in file_list:
            try:
                with h5py.File(file_path, "r") as f:
                    if "/RetrievalResults/xco2" in f and \
                       "/RetrievalGeometry/retrieval_latitude" in f and \
                       "/RetrievalGeometry/retrieval_longitude" in f:
                        
                        co2 = f["/RetrievalResults/xco2"][:] * 1e6
                        lat = f["/RetrievalGeometry/retrieval_latitude"][:]
                        lon = f["/RetrievalGeometry/retrieval_longitude"][:]
                        
                        records.extend([{"lat": la, "lon": lo, "co2": c}
                                        for la, lo, c in zip(lat.flatten(), lon.flatten(), co2.flatten())])
            except Exception as read_e:
                print(f"  - Warning: Could not read file {os.path.basename(file_path)}. Error: {read_e}")

        if not records:
            print("Warning: No valid data could be extracted from files this month. Skipping.")
            continue
        
        co2_df = pd.DataFrame(records)
        co2_df.dropna(subset=['lat', 'lon', 'co2'], inplace=True)
        co2_df = co2_df[(co2_df["lat"] >= bbox["ymin"]) & (co2_df["lat"] <= bbox["ymax"]) & 
                          (co2_df["lon"] >= bbox["xmin"]) & (co2_df["lon"] <= bbox["xmax"])]
        
        if co2_df.empty:
            print("Warning: Dataframe is empty after initial filtering. Skipping month.")
            continue
        print(f"Loaded {len(co2_df)} data points.")

        # Part 3: Regional Anomaly Calculation
        print("Calculating regional anomalies...")
        co2_gdf = gpd.GeoDataFrame(co2_df, geometry=gpd.points_from_xy(co2_df.lon, co2_df.lat), crs="EPSG:4326")
        points_with_region = gpd.sjoin(co2_gdf, regions_gdf, how="left", predicate="within")
        points_with_region.dropna(subset=['region'], inplace=True)
        
        if points_with_region.empty:
            print("Warning: No data points fall within the defined GeoJSON regions. Skipping.")
            continue

        print("  -> Grouping by region and calculating medians...")
        regional_medians = points_with_region.groupby('region')['co2'].transform('median')
        points_with_region['aco2'] = points_with_region['co2'] - regional_medians
        final_df = points_with_region[['lon', 'lat', 'co2', 'aco2']].copy()
        
        source_points = final_df[['lon', 'lat']].values
        source_values_co2 = final_df['co2'].values
        source_values_aco2 = final_df['aco2'].values

        # --- MODIFIED: Improved IDW Interpolation with Cross-Validation ---
        # Part 4: Find optimal IDW power and perform interpolation
        print("Optimizing IDW power parameter with cross-validation...")
        cv_sample_size = min(500, len(final_df))
        cv_indices = np.random.choice(len(final_df), cv_sample_size, replace=False)
        cv_points, cv_values = source_points[cv_indices], source_values_co2[cv_indices]
        
        best_p, lowest_rmse = 2.0, np.inf
        p_values_to_test = [1.5, 2.0, 2.5, 3.0]
        
        for p in p_values_to_test:
            errors_sq = []
            for i in range(cv_sample_size):
                # Leave one out: select one point for validation
                validation_pt, validation_val = cv_points[i:i+1], cv_values[i]
                # Use the rest for training
                training_pts, training_vals = np.delete(cv_points, i, axis=0), np.delete(cv_values, i, axis=0)
                
                # Predict the value of the validation point
                predicted_val = idw_interpolation(training_pts, training_vals, validation_pt, n_neighbors=10, p=p)[0]
                if not np.isnan(predicted_val): 
                    errors_sq.append((predicted_val - validation_val) ** 2)
            
            if errors_sq:
                rmse = np.sqrt(np.mean(errors_sq))
                print(f"  -> Power (p) = {p}, RMSE = {rmse:.4f}")
                if rmse < lowest_rmse: 
                    lowest_rmse, best_p = rmse, p
        
        print(f"Optimal power (p) found: {best_p}. Performing final interpolation...")
        # Perform final interpolation on the full grid using the best power
        interp_co2_grid = idw_interpolation(source_points, source_values_co2, target_points_flat, p=best_p).reshape(grid_xx.shape)
        interp_aco2_grid = idw_interpolation(source_points, source_values_aco2, target_points_flat, p=best_p).reshape(grid_xx.shape)
        
        # Part 5: Create and save NetCDF files
        print("Creating and saving NetCDF output...")
        yyyymm_str = f"{full_year_str}{month_str}"
        ncname = os.path.join(output_dir, f"{yyyymm_str}_CO2_mx_interpolated.nc")
        ncname2 = os.path.join(output_dir, f"{yyyymm_str}_CO2_sns_interpolated.nc")

        time_coord = pd.to_datetime([process_date])

        # Create DataArray for CO2
        da_co2 = xr.DataArray(
            data=np.expand_dims(interp_co2_grid, axis=0),
            dims=["time", "latitude", "longitude"],
            coords={"time": time_coord, "longitude": grid_x, "latitude": grid_y},
            attrs={"long_name": f"CO2 mixing ratio (IDW p={best_p:.1f} from OCO-2)", "units": "ppm"},
            name="co2"
        )
        da_co2.rio.write_crs("EPSG:4326", inplace=True)
        da_co2.to_netcdf(ncname, mode='w', format='NETCDF4', engine='netcdf4')

        # Create DataArray for Regional Anomaly
        da_aco2 = xr.DataArray(
            data=np.expand_dims(interp_aco2_grid, axis=0),
            dims=["time", "latitude", "longitude"],
            coords={"time": time_coord, "longitude": grid_x, "latitude": grid_y},
            attrs={"long_name": f"Regional CO2 anomaly (IDW p={best_p:.1f} from OCO-2)", "units": "ppm"},
            name="aco2"
        )
        da_aco2.rio.write_crs("EPSG:4326", inplace=True)
        da_aco2.to_netcdf(ncname2, mode='w', format='NETCDF4', engine='netcdf4')
        
        print(f"Successfully created NetCDF files: {os.path.basename(ncname)} and {os.path.basename(ncname2)}")

    except Exception as e:
        import traceback
        print(f"\nAN ERROR OCCURRED while processing {full_year_str}-{month_str}: {e}")
        traceback.print_exc()
        print("Skipping to the next month.\n")
        continue
    
    finally:
        month_end_time = time.time()
        print(f"Time taken for this month: {round(month_end_time - month_start_time, 2)} seconds.")

# --- FINAL REPORT ---
overall_end_clock = time.time()
print(f"\n--- Batch processing complete. ---")
print(f"Total time taken: {round((overall_end_clock - overall_start_clock) / 60, 2)} minutes.")
