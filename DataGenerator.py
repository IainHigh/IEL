import json
import csv
from enum import Enum
from urllib.request import urlopen
from DataGeneratorPredictors import Predictors
from tqdm import tqdm

class DataGenerator():
    
    def __init__(self,
                numOfSamples : int = 100,
                rainfall : list() = None, 
                startingWaterLevel : float = 0.45,
                volumeOfWaterComingFromDamn: list() = None,
                catchementArea: float = 58.5,
                pollutants: list() = None,
                property_flooding_level: float = 1.0,
                low_lying_land_flooding_level: float = 1.0,
                predictors : Predictors = None):
        
        # Volume of water coming from damn is in m3/s
        # Flow rate is in m3/s
        # Rainfall is in mm
        # Catchement area is in km2
        # Water level is in m

        self.numOfSamples = numOfSamples # Number of quarter hourly samples we should generate

        # If the volume of water coming from the damn is not specified, set it to 0
        if volumeOfWaterComingFromDamn is None:
            volumeOfWaterComingFromDamn = [0.0] * numOfSamples
        else:
            self.volumeOfWaterComingFromDamn = volumeOfWaterComingFromDamn

        if predictors is None:
            self.predictors = Predictors()
        else:
            self.predictors = predictors

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
        rainMultiplier = 0.001 * 0.72 * self.catchementArea * 1000000
        return [(y*rainMultiplier + (x - z)*900) for x, y, z in zip(self.volumeOfWaterComingFromDamn, self.rainfall, flowRate)]

    def calculateDailyWaterDifference(self, qtrHourlySamples):
        # 96 quarter-hourly samples per day
        return sum(qtrHourlySamples)

    def calculateDailyLevelDerivative(self, dailyWaterDifference, startingHeight):
        predicted = self.predictors.generateLevelDerivativeFromWaterDifference(dailyWaterDifference)
        if startingHeight + predicted < 0.2:
            return 0.2 - startingHeight
        return predicted

    def calculateQuarterHourlyLevelDerivative(self, dailyLevelDerivative, dailyWaterDifference, qtrHourlyWaterDifference):
        if dailyWaterDifference == 0:
            return [0.0]*96

        return [(dailyLevelDerivative / 96)] * 96

        # samples = [0.0]*96
        # for j in range(96):
        #     samples[j] = (qtrHourlyWaterDifference[j] / dailyWaterDifference) * dailyLevelDerivative
        # return samples

    def calculateQuarterHourlyLevel(self, quarterHourlyLevelDerivative):
        level = [0.0]*len(quarterHourlyLevelDerivative)
        level[0] = self.startingWaterLevel
        for i in range(1, len(quarterHourlyLevelDerivative)):
            if (level[i-1] + quarterHourlyLevelDerivative[i]) < 0:
                level[i] = 0
            else:
                level[i] = level[i-1] + quarterHourlyLevelDerivative[i]
                if level[i] > 4:
                    level[i] = 4
        return level

    def write_to_qtrhrl_csv(self, quarter_hourly_flow_rate, quarter_hourly_levels):
        # Write the rainfall, flow rate, water difference and water level to a csv file
        f = open('Quarter_Hourly_Generated_Data.csv', 'w')
        writer = csv.writer(f)
        writer.writerow(["Rainfall", "Flow Rate", "Water Level"])
        for i in range(self.numOfSamples):
            row = [self.rainfall[i], quarter_hourly_flow_rate[i], quarter_hourly_levels[i]]
            writer.writerow(row)
        f.close()

    def write_to_day_csv(self, quarter_hourly_flow_rate, quarter_hourly_levels):
        samples = len(quarter_hourly_flow_rate)
        numberOfDays = (samples // 96) if (samples % 96 == 0) else (samples // 96) + 1
        f = open('Daily_Generated_Data.csv', 'w')
        writer = csv.writer(f)
        writer.writerow(["Total Rainfall", "Average Flow Rate", "Average Water Level"])
        for i in range(numberOfDays):
            row = [sum(self.rainfall[i*96:(i+1)*96]), sum(quarter_hourly_flow_rate[i*96:(i+1)*96])/96, sum(quarter_hourly_levels[i*96:(i+1)*96])/96]
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
        rainfallData = [x[1] for x in data_json[0]["data"]][0:samples]
        assert len(rainfallData) == samples, "The number of samples returned from the SEPA API is not equal to the number of samples requested"
        return rainfallData

class eventEnum(Enum):
    STORM = 1
    DROUGHT = 2
    FREEZE = 3
    FLOOD = 4
    BURST_DAM = 5

if __name__ == "__main__":

    print("1: Initialising ML Model")
    samples = 96 * 100
    number_of_days = (samples // 96) if (samples % 96 == 0) else (samples // 96) + 1
    predictor = Predictors()
    rainfall = DataGenerator(numOfSamples=samples, predictors=predictor).read_rainfall_from_SEPA_api(samples = samples)
    starting_height = 0.5

    all_flow_rates = []
    all_levels = []

    print("2: Generating Data")
    for i in tqdm(range(number_of_days)):
        dg = DataGenerator(numOfSamples=96, rainfall=rainfall[i*96:(i+1)*96], startingWaterLevel=starting_height, predictors=predictor)
        quarter_hourly_levels = None
        # For each day
        for i in range(10):
            quarter_hourly_flow_rate = dg.calculate_quarter_hourly_flow_rate(quarter_hourly_levels)
            quarter_hourly_water_difference = dg.calculate_quarter_hourly_water_diff(quarter_hourly_flow_rate)
            daily_water_difference = dg.calculateDailyWaterDifference(quarter_hourly_water_difference)
            daily_level_difference = dg.calculateDailyLevelDerivative(daily_water_difference, starting_height)
            quarter_hourly_level_difference = dg.calculateQuarterHourlyLevelDerivative(daily_level_difference, daily_water_difference, quarter_hourly_water_difference)
            quarter_hourly_levels = dg.calculateQuarterHourlyLevel(quarter_hourly_level_difference)
            quarter_hourly_flow_rate = dg.calculate_quarter_hourly_flow_rate(quarter_hourly_levels)

        starting_height = quarter_hourly_levels[-1]
        all_flow_rates += quarter_hourly_flow_rate
        all_levels += quarter_hourly_levels

    print("3: Writing Data to CSV")
    dg = DataGenerator(numOfSamples=samples, rainfall=rainfall, predictors=predictor)
    dg.write_to_qtrhrl_csv(all_flow_rates, all_levels)
    dg.write_to_day_csv(all_flow_rates, all_levels)
    print("4: Done")