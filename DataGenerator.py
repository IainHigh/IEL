import json
import csv
from enum import Enum
from urllib.request import urlopen
from DataGeneratorPredictors import Predictors

class DataGenerator():
    
    def __init__(self,
                numOfSamples : int = 100,
                rainfall : list() = None, 
                startingWaterLevel : float = 0.4,
                volumeOfWaterComingFromDamn: list() = None,
                catchementArea: float = 58.5,
                pollutants: list() = None,
                property_flooding_level: float = 1.0,
                low_lying_land_flooding_level: float = 1.0):
        
        # Volume of water coming from damn is in m3/s
        # Flow rate is in m3/s
        # Rainfall is in mm
        # Catchement area is in km2
        # Water level is in m

        # If the volume of water coming from the damn is not specified, set it to 0
        if volumeOfWaterComingFromDamn is None:
            volumeOfWaterComingFromDamn = [0.0] * numOfSamples

        self.predictors = Predictors()

        self.numOfSamples = numOfSamples # Number of quarter hourly samples we should generate
        
        if rainfall is None:
            self.rainfall = self.read_rainfall_from_SEPA_api(samples = numOfSamples)
        else:
            self.rainfall = rainfall

        self.startingWaterLevel = startingWaterLevel                    # The starting water level of the river
        self.volumeOfWaterComingFromDamn = volumeOfWaterComingFromDamn  # The volume of water coming from the damn
        self.catchementArea = catchementArea                            # The area of the catchement
        self.pollutants = pollutants                                    # The pollutants in the river
        self.property_flooding_level = property_flooding_level              # The level at which property flooding occurs
        self.low_lying_land_flooding_level = low_lying_land_flooding_level  # The level at which low lying land flooding occurs (e.g. farm, marshland)

    def calculate_quarter_hourly_flow_rate(self, quarterHourlyLevels = None):
        curWaterLevel = self.startingWaterLevel
        flowRate = [0.0]*self.numOfSamples


        for i in range(self.numOfSamples):
            flowRate[i] = self.predictors.generateQuarterHourlyFlow(curWaterLevel)

            if quarterHourlyLevels is not None:
                curWaterLevel = quarterHourlyLevels[i]

        return flowRate

    def calculate_quarter_hourly_water_diff(self, flowRate):
        # Convert the mm of rainfall to m3/s
        # 1mm of precipitation per 15 minutes per km2 = 0.9m3/s * catchmentarea
        # However, only 72% of the water is actually available to the river
        rainfallVol = [x * self.catchementArea * 0.9 * 0.72 for x in self.rainfall]
        return [x + y - z for x, y, z in zip(self.volumeOfWaterComingFromDamn, rainfallVol, flowRate)]

    def calculateDailyWaterDifference(self, qtrHourlySamples):
        # 96 quarter-hourly samples per day
        numOfDays = (self.numOfSamples // 96) if (self.numOfSamples % 96 == 0) else (self.numOfSamples // 96) + 1
        samples = [0.0]*numOfDays
        for i in range(numOfDays):
            samples[i] = sum(qtrHourlySamples[i*96:(i+1)*96])
            
        return samples

    def calculateDailyLevelDerivative(self, dailyWaterDifference):
        return self.predictors.generateLevelDerivativeFromWaterDifference(dailyWaterDifference)

    def calculateQuarterHourlyLevelDerivative(self, dailyLevelDerivative, dailyWaterDifference, qtrHourlyWaterDifference):
        numOfDays = (self.numOfSamples // 96) if (self.numOfSamples % 96 == 0) else (self.numOfSamples // 96) + 1
        samples = [0.0]*self.numOfSamples
        for i in range(numOfDays):
            for j in range(96):
                samples[i*96 + j] = (qtrHourlyWaterDifference[i*96] / dailyWaterDifference[i]) * dailyLevelDerivative[i]
        return samples

    def calculateQuarterHourlyLevel(self, quarterHourlyLevelDerivative):
        level = [0.0]*len(quarterHourlyLevelDerivative)
        level[0] = self.startingWaterLevel
        for i in range(1, len(quarterHourlyLevelDerivative)):
            level[i] = level[i-1] + quarterHourlyLevelDerivative[i]
        return level

    def calculateWaterDifference(self, flowRate, rainfall, volumeOfWaterComingFromDamn):
        return (volumeOfWaterComingFromDamn + sum(rainfall)) - sum(flowRate)

    def write_to_csv(self, quarter_hourly_flow_rate, quarter_hourly_levels, quarter_hourly_water_difference):
        # Write the rainfall, flow rate, water difference and water level to a csv file
        f = open('test.csv', 'w')
        writer = csv.writer(f)
        writer.writerow(["Rainfall", "Flow Rate", "Water Difference", "Water Level"])
        for i in range(self.numOfSamples):
            row = [self.rainfall[i], quarter_hourly_flow_rate[i], quarter_hourly_water_difference[i], quarter_hourly_levels[i]]
            writer.writerow(row)
        f.close()

    def read_rainfall_from_SEPA_api(self, stationName : str = "Dippen", samples = 100):
        url = "https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getTimeseriesList&station_name=" + stationName + "&format=json"
  
        # store the response of URL
        response = urlopen(url)
  
        # storing the JSON response 
        # from url in data
        data_json = json.loads(response.read())
  
        # Get the id of the entry with "15minute.Total" and "Precip"
        for entry in data_json:
            if entry[4] == "15minute.Total" and entry[6] == "Precip":
                id = entry[3]
                break

        period = "P" + str((samples // 4) + 4) + "H"
        url = "https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getTimeseriesValues&ts_id=" + str(id) + "&period=" + period + "&returnfields=Timestamp,%20Value,%20Quality%20Code&format=json"
        
        response = urlopen(url)
        data_json = json.loads(response.read())

        return [x[1] for x in data_json[0]["data"]][0:samples]

class eventEnum(Enum):
    STORM = 1
    DROUGHT = 2
    FREEZE = 3
    FLOOD = 4
    BURST_DAM = 5

if __name__ == "__main__":
    # 96 samples = 24 hours
    dg = DataGenerator(numOfSamples=96*4)
    quarter_hourly_levels = None

    for i in range(20):
        quarter_hourly_flow_rate = dg.calculate_quarter_hourly_flow_rate(quarter_hourly_levels)
        quarter_hourly_water_difference = dg.calculate_quarter_hourly_water_diff(quarter_hourly_flow_rate)
        daily_water_difference = dg.calculateDailyWaterDifference(quarter_hourly_water_difference)
        daily_level_difference = [dg.calculateDailyLevelDerivative(x) for x in daily_water_difference]
        quarter_hourly_level_difference = dg.calculateQuarterHourlyLevelDerivative(daily_level_difference, daily_water_difference, quarter_hourly_water_difference)
        quarter_hourly_levels = dg.calculateQuarterHourlyLevel(quarter_hourly_level_difference)

    dg.write_to_csv(quarter_hourly_flow_rate, quarter_hourly_levels, quarter_hourly_water_difference)

    