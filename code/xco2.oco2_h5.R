######################################################################################
# This is an R script to create a raster map from OCO-2          .                   #   
# Input files are of a HDF (.h5) type taken from satellite observations.             #
# Files are downloaded from                                                          #
#     https://disc.gsfc.nasa.gov/datasets/OCO2_L2_Standard_11.2/summary (OCO-2)      #
# This script transforms a mosaic consisting of a number of satellite observations   #
#     to a dataframe.                                                                #
# The script interpolates points into raster by applying appropriate interpolation   #
#     method for the Indonesian region.                                              #
# Always change lines 148 and 159 to the last day of the previous month.             #
# Refer to below comments for more detailed instructions/explanations.               #
# Created by Alberth Nahas on 2022-07-15 08:00 pm WIB.                               #
# Email: alberth.nahas@bmkg.go.id                                                    #
# Version 1.0.0.                                                                     #
# Disclaimer: This is a free-to-share, free-to-use script. That said, it comes with  #
#             absolutely no warranty. User discretion is advised.                    #
######################################################################################


### CLEAR WORKSPACE ###
rm(list = ls())
#gc()
start.clock <- Sys.time()


### INCLUDE LIBRARIES ###
require(ncdf4)
require(sf)
require(tidyverse)
require(gstat)
require(readr)
require(raster)
require(rhdf5)
require(gdalUtilities)


### COLLECT .nc FILES ON A LIST ###
setwd("~/Documents/Satellite/oco2/1-data/")  # adjust to the right directory
year <- "24" # Use only two last digits of the year
month <- "12"
fpath <- getwd()
pattern <- paste0(year,month) # adjust to "oco3_" for OCO-3
fn <- NULL
flist <- list.files(path = fpath, 
                    pattern = pattern,   
                    all.files = FALSE, 
                    full.names = TRUE, 
                    recursive = TRUE)
fn <- do.call(c, list(flist, fn))
print(paste("There are ",length(fn), " h5 file(s) in this directory."))


### SOME NAMING ###
ncname <- paste0("CO2_mx_monthly_",month,"_20",year,".nc")
ncname2 <- paste0("CO2_sns_monthly_",month,"_20",year,".nc")
csvname <- paste0("CO2_monthly_",month,"_20",year,".csv")
transit <- "temp.nc"
transit2 <-"temp2.nc"


### CONSTRUCT A DATAFRAME FROM .nc FILES ###
co2df <- NULL
for (i in seq_along(fn)) {
  h5file <- fn[i]
  co2 <- h5read(h5file, "/RetrievalResults/xco2") * 1e6
  lat <- h5read(h5file, "/RetrievalGeometry/retrieval_latitude")
  lon <- h5read(h5file, "/RetrievalGeometry/retrieval_longitude")
  # concatenate the new data to the global data frame
  co2df <- rbind(co2df, data.frame(lat = lat, 
                                   lon = lon, 
                                   co2 = co2,
                                   aco2 = co2 - median(co2)))
}


### CREATE A .csv FILE TO BUILD THE RASTER FILE ###
co2df_sub <- subset(co2df, lat >= -15 & lat <= 30 & lon >= 90 & lon <= 145)
write.csv(co2df_sub, file = csvname, row.names = FALSE, quote = TRUE, na = "NA")
pts_CO2 <- read_csv(csvname,
                    col_types = cols(co2 = col_double(), aco2 = col_double(),
                                     lon = col_double(), lat = col_double())
) %>% 
  dplyr::select(lon, lat, co2, aco2)

print(pts_CO2)


### CREATE A SPATIAL FILE BASED ON xco2 ###
sf_CO2 <- st_as_sf(pts_CO2, coords = c("lon", "lat"), 
                   crs = "+proj=longlat +datum=WGS84 +no_defs")


### CREATE A RASTER TEMPLATE FILE ###
# Boundary box for max-min lat and lon
bbox <- c(
  "xmin" = 90,
  "ymin" = -15,
  "xmax" = 145,
  "ymax" = 30)
# Generate a grid template based on defined boundaries
# Grid cell size is given as "by" and might need to adjust
#    accordingly
grd_template <- expand.grid(
  X = seq(from = bbox["xmin"], to = bbox["xmax"], by = 0.5),
  Y = seq(from = bbox["ymin"], to = bbox["ymax"], by = 0.5))
# {raster} expects a PROJ.4 string, see https://epsg.io/4326
crs_raster_format <- "+proj=longlat +datum=WGS84 +no_defs"
# Rasterize the grid template
grd_template_raster <- grd_template %>% 
  dplyr::mutate(Z = 0) %>% 
  raster::rasterFromXYZ( 
    crs = crs_raster_format)


### INTERPOLATE POINT DATA TO RASTER TEMPLATE ###
# Build a formula to fit raster using Inverse Distance Weighted Method
fit_IDW_co2 <- gstat( 
  formula = co2 ~ 1,
  data = as(sf_CO2, "Spatial"),
  nmax = 20, nmin = 5,
  set = list(idp = 2.0)) # inverse distance power

fit_IDW_aco2 <- gstat(
  formula = aco2 ~ 1,
  data = as(sf_CO2, "Spatial"),
  nmax = 20, nmin = 5,
  set = list(idp = 2.0)) # inverse distance power

# Interpolate data using the formula
interp_IDW_co2 <- interpolate(grd_template_raster, fit_IDW_co2)
interp_IDW_aco2 <- interpolate(grd_template_raster, fit_IDW_aco2)


### CREATE A NETCDF OUTPUT FILE BASED ON THE INTERPOLATED VALUES ###
co2rst <- brick(interp_IDW_co2)
aco2rst <- brick(interp_IDW_aco2)
# Some file metadata are created, others may be added.
writeRaster(co2rst, 
            file = transit, 
            overwrite = TRUE, 
            format = "CDF", # A netcdf format
            varname = "co2", 
            varunit = "ppm", 
            longname = "CO2 mixing ratio",
            xname = "longitude",
            yname = "latitude", 
            zname = "time",
            zunit = "days since 2024-11-30") # Timestep and time origin are not specified
writeRaster(aco2rst,
            file = transit2,
            overwrite = TRUE,
            format = "CDF", # A netcdf format
            varname = "co2_diff",
            varunit = "ppm",
            longname = "Difference of CO2 mixing ratio from median",
            xname = "longitude",
            yname = "latitude",
            zname = "time",
            zunit = "days since 2024-11-30") # Timestep and time origin are not specified
# Add Coordinate Reference System
gdal_translate(transit, a_srs = "EPSG:4326", of = "netCDF", ncname)
gdal_translate(transit2, a_srs = "EPSG:4326", of = "netCDF", ncname2)


### HOUSEKEEPING ###
unlink(transit)
unlink(transit2)


### PRINT ELAPSED TIME ###
stop.clock <- Sys.time()
how.many <- round(as.numeric(difftime(stop.clock, start.clock, units = "mins")), 2)
time.spent <- paste("Work has been completed in", how.many,"minutes")
print(time.spent)


### END OF CODE ###
