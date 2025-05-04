# Processing Total Column CO<sub>2</sub> using NASA's OCO-2 Satellite Data
## NASA OCO-2 Satellite

Carbon dioxide (CO<sub>2</sub>) is one of the greenhouse gases whose increasing concentration in the atmosphere is considered an indicator of climate change. The rise in atmospheric CO<sub>2</sub> concentration has occurred globally, marked by its increase since the industrial revolution in 1750.

In the study of climate change, the increase in CO<sub>2</sub> concentration is essential to report. Therefore, measuring its concentration in the atmosphere is crucial for providing a profile of its rate of increase. Information about CO<sub>2</sub> concentration can be obtained using several methods, such as measurements with in situ instrumentation at a specific location, mobile measurements using ships and aircraft, satellite monitoring, and modeling.

One source of information about CO<sub>2</sub> concentration is NASA's Orbiting Carbon Observatory-2 (OCO-2) Satellite. CO<sub>2</sub> monitoring activities using the OCO-2 Satellite have been conducted by NASA since the satellite was launched on July 2, 2014. The OCO-2 Satellite is NASA's first satellite dedicated to monitoring CO<sub>2</sub> via remote sensing. Since it is observed from space, the CO<sub>2</sub> values provided represent the total column concentration of CO<sub>2</sub>. The total column CO<sub>2</sub> is the result of monitoring the CO<sub>2</sub> concentration from the Earth's surface to the top of the atmosphere within the satellite's spatial resolution.

To obtain the total column CO<sub>2</sub> values, this satellite combines three high-resolution spectrometers that measure the reflection of sunlight at wavelengths of 1.61 and 2.06 micrometers or in the near-infrared absorption region of CO<sub>2</sub>. The spatial resolution of the OCO-2 Satellite's swath is 2.25 km x 1.29 km, with a repeat time every 16 days.

More information about the OCO-2 Satellite can be seen in the following video.
[![Watch the video](https://img.youtube.com/vi/-uP_fqEfYWg/maxresdefault.jpg)](https://youtu.be/-uP_fqEfYWg)
<br></br>
## Data Download

The OCO-2 satellite data used in this processing comes from the OCO-2 Level 2 geolocated XCO2 retrievals results, physical model V11.2 (https://disc.gsfc.nasa.gov/datasets/OCO2_L2_Standard_11.2/summary). This version is the latest, and it was implemented in June 2024. This data is the output of the algorithm used to obtain the average total column CO<sub>2</sub> (XCO2).

Data download is carried out using a file clipping facility that can collectively gather .h5 files within the coordinate boundaries of Indonesia. This data can be accessed via the link above by selecting the Get Data menu. For convenience, data collection is processed using wget. Instructions on how to use wget for data download on Windows, MacOS, and Linux operating systems can be found at the following link: https://disc.gsfc.nasa.gov/data-access. Data download can only be processed if you have a NASA Earthdata account (https://wiki.earthdata.nasa.gov/display/EL/How+To+Register+For+an+EarthData+Login+Profile). 
<br></br>
## Data Processing

Data processing is conducted on the downloaded data for monthly periods. The processing is done using an R script. In this script, the total column CO<sub>2</sub> (xco2) values, along with the latitude and longitude coordinates at the points with xco2 values, are extracted from the satellite data (in .h5 format). These points are then interpolated using the Inverse Distance Weighting (IDW) method at a spatial resolution of 0.5 degrees. The output of this process is a binary file in .nc format.
Another approach using Python is also available.

Visualization of the processed data results is done using a GrADS script that displays the total column CO<sub>2</sub> for the Indonesian region (90°E - 145°E, 10°N - 15°S).

![](https://github.com/alberthnahas/OCO-2/blob/main/ghg-indonesia.gif)

The R codes were developed on Ubuntu 24.04 LTS operating system.

<i>Note: Data for August 2017 is not available.</i>
