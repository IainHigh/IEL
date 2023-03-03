This directory contains the real data accessed from the SEPA API. This file describes the process of accessing this data.

To get the list of all stations, use the following URL:
https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getStationList

To get a list of paramaters and measurable timeseries for a station, use the following URL (replacing <STATION_ID> with the station ID):
https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getTimeseriesList&station_name=<STATION_NAME>
for example:
https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getTimeseriesList&station_name=Dippen

Parametertype_name meaning:
Precip: Precipitation (mm)
Q: Flow rate (m3/s)
S: level (m)

Once you have the list of the timeseries, you can get the data for a timeseries using the following URL (replace <TIMESERIES_ID> with the timeseries ID and <PERIOD> with either 'complete' for the daily data or 'P3125D' for the quater-hourly data):
https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getTimeseriesValues&ts_id=<TIMESERIES_ID>&period=<PERIOD>&returnfields=Timestamp,%20Value,%20Quality%20Code

Finally to download the data, use the following URL(replace <TIMESERIES_ID> with the timeseries ID and <PERIOD> with either 'complete' for the daily data or 'P3125D' for the quater-hourly data):
https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getTimeseriesValues&ts_id=<TIMESERIES_ID>&period=<PERIOD>&returnfields=Timestamp,%20Value,%20Quality%20Code&format=csv

For anything else please refer to the documentation of SEPA Data API:
https://timeseriesdoc.sepa.org.uk/