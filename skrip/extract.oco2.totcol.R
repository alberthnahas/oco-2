######################################################################################
# This is an R script to exract monthly total column CO2 from OCO-2 Satellite.       #   
# Input files are of a NETCDF (.nc) type taken from OCO-2 L2 Standard.               #
# Info:                                                                              #
#     https://disc.gsfc.nasa.gov/datasets/OCO2_L2_Standard_11/summary                #
# This script uses SHP file with Indonesian provincies to extract the value          #
#     following the administrative borders.                                          #
# Refer to below comments for more detailed instructions/explanations.               #
# Created by Alberth Nahas on 2022-07-20 07:30 am WIB.                               #
# Email: alberth.nahas@bmkg.go.id                                                    #
# Version 1.0.0 (2022-07-20)                                                         #
# Disclaimer: This is a free-to-share, free-to-use script. That said, it comes with  #
#             absolutely no warranty. User discretion is advised.                    #
######################################################################################

### CLEAR WORKSPACE ###
rm(list=ls())
gc()
start.clock <- Sys.time()

### CALL LIBRARY ###
library(terra)

### SET WORKING DIRECTORY ###
setwd("~/Documents/BMKG/Spatial_CO2/tableau/")

### DEFINE OBJECTS ###
# The shapeflie needs to be in SpatVector format
shp_provinsi <- "Indonesia_37_Provinsi.shp"
vec_provinsi <- vect(shp_provinsi)
# The raster file needs to be in SpatRaster format
ras_oco2 <- rast("CO2_mx_monthly_201709_202206.nc")


### CONSTRUCT THE DATABASE ###
oco2_df <- NULL
for (i in 1:58) {
  ras_oco2run <- ras_oco2[[i]]
  ext <- extract(x = ras_oco2run, 
                 y = vec_provinsi, 
                 fun = mean, 
                 weights = TRUE, 
                 na.rm = TRUE)
  Date <- time(ras_oco2run)
  oco2_df <- rbind(oco2_df, 
                    data.frame(Year = as.numeric(substr(Date, start = 1, stop = 4)),
                               Month = as.numeric(substr(Date, start = 6, stop = 7)),
                               Provinsi = vec_provinsi$PROVINSI,
                               CO2 = ext[,2]))
  complete <- paste0("Task completed for ", time(ras_oco2run))
  print(complete)
}

### WRITE CSV FILE ###
write.csv(oco2_df, 
          file = "oco2.provinsi.201709_202206.csv", 
          row.names = FALSE, 
          quote = TRUE, 
          na = "NA")

### PRINT ELAPSED TIME ###
stop.clock <- Sys.time()
how.many <- round(as.numeric(difftime(stop.clock, start.clock, units = "mins")), 2)
time.spent <- paste("Work has been completed in", how.many,"minutes")
collecting.date <- paste("This information was collected on", Sys.Date())
print(time.spent)
print(collecting.date)


### END OF LINE ###