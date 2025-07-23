#!/usr/bin/env python3
"""extract_regional-co2.py

Extract gridded CO₂ from a NetCDF file to two tabular CSV products:

1. Province‑level averages (38 provinces)  ->  co2_by_province.csv
   Columns: date,province,co2

2. Kabupaten/Kota‑level averages (516 regions) ->  co2_by_municipality.csv
   Columns: date,province,kabupaten,co2

The script is geometry‑aware and works even for very small regions (e.g.,
DKI Jakarta) by falling back to the nearest grid cell when no cell centres
fall inside the polygon.

Dependencies
------------
numpy, pandas, xarray, shapely>=2.0, fiona, tqdm  (install with pip)

Usage
-----
$ python extract-regional-co2.py \
        --nc co2.nc \
        --prov indonesia_38prov.geojson \
        --kab  indonesia_kabkota_38prov.geojson

The output CSVs are written to the current directory.
"""

import argparse
import numpy as np
import pandas as pd
import xarray as xr
import fiona
from shapely.geometry import shape, Point
from shapely.prepared import prep
from tqdm import tqdm


def build_latlon_grids(ds):
    """Return 2‑D grids of lat, lon corresponding to data array indices."""
    lats = ds['latitude'].values
    lons = ds['longitude'].values
    lon2d, lat2d = np.meshgrid(lons, lats)
    return lat2d, lon2d


def mean_for_region(co2_2d, lat2d, lon2d, geom, geom_prep):
    """Average CO₂ inside *geom* or nearest cell to the centroid as fallback."""
    minx, miny, maxx, maxy = geom.bounds
    mask = (lon2d >= minx) & (lon2d <= maxx) & (lat2d >= miny) & (lat2d <= maxy)
    idxs = np.where(mask)
    values = []

    for y_idx, x_idx in zip(*idxs):
        if geom_prep.contains(Point(lon2d[y_idx, x_idx], lat2d[y_idx, x_idx])):
            val = co2_2d[y_idx, x_idx]
            if np.isfinite(val):
                values.append(val)

    if values:
        return float(np.mean(values))

    # --- fallback: nearest grid‑cell to region centroid ----------------------
    cent = geom.centroid
    y_idx = np.abs(lat2d[:, 0] - cent.y).argmin()
    x_idx = np.abs(lon2d[0, :] - cent.x).argmin()
    return float(co2_2d[y_idx, x_idx])


def read_province_regions(path):
    """Return list of province dicts with prepared geometry."""
    regions = []
    with fiona.open(path) as src:
        for feat in src:
            props = feat['properties']
            name = (props.get('provinsi') or props.get('PROVINSI') or
                    props.get('province') or props.get('PROVINCE'))
            geom = shape(feat['geometry'])
            regions.append({
                'province': name.strip().upper(),
                'geometry': geom,
                'prep': prep(geom)
            })
    assert len(regions) == 38, f"Expected 38 provinces, got {len(regions)}"
    return regions


def read_kabupaten_regions(path):
    """Return list of kabupaten/kota dicts with prepared geometry."""
    regions = []
    with fiona.open(path) as src:
        for feat in src:
            props = feat['properties']
            kab = (props.get('kabupaten') or props.get('KABUPATEN') or
                   props.get('kabkot') or props.get('KABKOT'))
            prov = (props.get('provinsi') or props.get('PROVINSI') or
                    props.get('province') or props.get('PROVINCE'))
            geom = shape(feat['geometry'])
            regions.append({
                'province': prov.strip().upper(),
                'kabupaten': kab.strip().upper(),
                'geometry': geom,
                'prep': prep(geom)
            })
    assert len(regions) == 516, f"Expected 516 kabupaten/kota, got {len(regions)}"
    return regions


def extract(nc_path, prov_geojson, kab_geojson,
            out_prov_csv='new_co2_by_province.csv',
            out_kab_csv='_new_co2_by_municipality.csv'):
    ds = xr.open_dataset(nc_path)
    var = ds['co2'] if 'co2' in ds.data_vars else ds[list(ds.data_vars)[0]]

    lat2d, lon2d = build_latlon_grids(ds)
    provinces = read_province_regions(prov_geojson)
    kabupaten = read_kabupaten_regions(kab_geojson)

    prov_records = []
    kab_records = []

    for t in tqdm(var['time'].values, desc='Processing timesteps'):
        date_str = np.datetime_as_string(t, unit='D')
        co2_2d = var.sel(time=t).values

        # Province level
        for reg in provinces:
            mean_val = mean_for_region(co2_2d, lat2d, lon2d,
                                       reg['geometry'], reg['prep'])
            prov_records.append({
                'date': date_str,
                'province': reg['province'],
                'co2': round(mean_val, 6)
            })

        # Kabupaten/Kota level
        for reg in kabupaten:
            mean_val = mean_for_region(co2_2d, lat2d, lon2d,
                                       reg['geometry'], reg['prep'])
            kab_records.append({
                'date': date_str,
                'province': reg['province'],
                'kabupaten': reg['kabupaten'],
                'co2': round(mean_val, 6)
            })

    pd.DataFrame(prov_records).to_csv(out_prov_csv, index=False)
    pd.DataFrame(kab_records).to_csv(out_kab_csv, index=False)
    print(f"✔ Saved {out_prov_csv} and {out_kab_csv}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Extract province/kabupaten CO₂ stats")
    parser.add_argument('--nc', required=True, help='Input NetCDF with CO₂')
    parser.add_argument('--prov', required=True, help='GeoJSON for 38 provinces')
    parser.add_argument('--kab', required=True, help='GeoJSON for 516 kabupaten/kota')
    parser.add_argument('--out-prov', default='co2_by_province.csv', help='Province CSV')
    parser.add_argument('--out-kab', default='co2_by_municipality.csv', help='Kabupaten CSV')
    opts = parser.parse_args()

    extract(opts.nc, opts.prov, opts.kab, opts.out_prov, opts.out_kab)

