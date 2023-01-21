Whereas the old data came from multiple different sources (National river flow archive, SEPA, and RiverLevels UK) this new data all comes from the one source - SEPA Data API.

Parametertype_name meaning:
Precip: Precipitation (mm)
Q: Flow rate (m3/s)
S: level (m)

Quality Code Meaning:
Quality code is a measure of how good the data is. The following codes are used:
50 - Good
100 - Estimated
140 - Provisional
150 - Suspect
200 - Unchecked (imported from legacy databases)
254 - Unchecked

To get the list of all stations, use the following URL:
https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getStationList

To get a list of paramaters and measurable timeseries for a station, use the following URL (replacing <STATION_ID> with the station ID):
https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getTimeseriesList&station_name=<STATION_NAME>
for example:
https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getTimeseriesList&station_name=Dippen

Once you have the list of the timeseries, you can get the data for a timeseries using the following URL (replace <TIMESERIES_ID> with the timeseries ID and <PERIOD> with either 'complete' for the daily data or 'P3125D' for the quater-hourly data):
https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getTimeseriesValues&ts_id=<TIMESERIES_ID>&period=<PERIOD>&returnfields=Timestamp,%20Value,%20Quality%20Code

Finally to download the data, use the following URL(replace <TIMESERIES_ID> with the timeseries ID and <PERIOD> with either 'complete' for the daily data or 'P3125D' for the quater-hourly data):
https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getTimeseriesValues&ts_id=<TIMESERIES_ID>&period=<PERIOD>&returnfields=Timestamp,%20Value,%20Quality%20Code&format=csv

For anything else please refer to the documentation of SEPA Data API:
https://timeseriesdoc.sepa.org.uk/