import json
import csv
import pandas as pd
import random
from urllib.request import urlopen
from DataGeneratorPredictors import Predictors
from tqdm import tqdm

class DataGenerator():
    
    def __init__(self,
                numOfSamples : int = 100,                   # Number of quarter-hourly samples to generate data for
                rainfall : list() = None,                   # List of rainfall values for each quarter-hourly sample (mm)
                startingWaterLevel : float = 0.45,          # The starting water level of the river (m)
                volumeOfWaterComingFromDamn: list() = None, # The volume of water coming from the damn (m3)
                catchementArea: float = 58.5,               # The catchment area of rainfall which feeds into the river (km2)
                pollutants: list() = None,                  # A list of tuples of (Source, Pollutant, Concentration) pairs
                property_flooding_level: float = 1.0,       # The level at which property flooding occurs (m)
                low_lying_land_flooding_level: float = 1.0, # The level at which low lying land flooding occurs (e.g. farm, marshland) (m)
                predictors : Predictors = None):

        self.numOfSamples = numOfSamples
        self.rainfall = rainfall
        self.startingWaterLevel = startingWaterLevel
        self.catchementArea = catchementArea
        self.pollutants = pollutants
        self.property_flooding_level = property_flooding_level
        self.low_lying_land_flooding_level = low_lying_land_flooding_level

        # If the volume of water coming from the damn is not specified, set it to 0
        if volumeOfWaterComingFromDamn is None:
            self.volumeOfWaterComingFromDamn = [0.0] * numOfSamples
        else:
            self.volumeOfWaterComingFromDamn = volumeOfWaterComingFromDamn

        # If a predictor hasn't been calculated in advance, calculate it now. Not recommended as training the predictor takes a few seconds.
        if predictors is None:
            self.predictors = Predictors()
        else:
            self.predictors = predictors

        
    def calculate_quarter_hourly_flow_rate(self, quarterHourlyLevels = None):
        # Calculate the flow rate for each quarter-hourly sample.
        # If the levels are provided then use them for more accurate calculations.
        # Otherwise just assume the water level is constant throughout the day.
        curWaterLevel = self.startingWaterLevel

        if (quarterHourlyLevels is None):
            return [self.predictors.generateQuarterHourlyFlow(curWaterLevel)] * self.numOfSamples

        flowRate = [0.0]*self.numOfSamples

        for i in range(self.numOfSamples):
            curWaterLevel = quarterHourlyLevels[i]
            flowRate[i] = self.predictors.generateQuarterHourlyFlow(curWaterLevel)
    
        return flowRate

    def calculate_quarter_hourly_water_diff(self, flowRate):
        # Calculate the difference in water volume for each quarter-hourly sample.
        # Rainfall measured in mm
        # flowRate and volumeOfWaterComingFromDamn measured in m3/s

        # 0.72 = percent of rainfall which feeds into the river; 1000000 = convert km2 to m2; 0.001 = convert mm to m.
        # 900 = Number of seconds in 15 minutes.
        rainMultiplier = 0.001 * 0.72 * self.catchementArea * 1000000

        return [(y*rainMultiplier + (x - z)*900) for x, y, z in zip(self.volumeOfWaterComingFromDamn, self.rainfall, flowRate)]

    def calculateDailyLevelDerivative(self, dailyWaterDifference, startingHeight):
        # Use the ML models in the Predictor class to estimate a value for the daily change in water level.
        predicted = self.predictors.generateLevelDerivativeFromWaterDifference(dailyWaterDifference)

        # Try to prevent the water level from going below 0.2m
        if startingHeight + predicted < 0.2:
            return 0.2 - startingHeight

        return predicted

    def calculateQuarterHourlyLevelDifference(self, dailyLevelDifference, quarterHourlyWaterDifference):
        quarter_hourly_water_difference = [0.0] * len(quarterHourlyWaterDifference)
        temp = dailyLevelDifference / len(quarterHourlyWaterDifference)
        totalWaterDifference = sum(quarterHourlyWaterDifference)
        for i in range(len(quarterHourlyWaterDifference)):
            ratio = quarterHourlyWaterDifference[i] / totalWaterDifference
            quarter_hourly_water_difference[i] = (daily_level_difference * ratio) + random.gauss(0, 0.0001)

        return quarter_hourly_water_difference

    def calculateQuarterHourlyLevel(self, quarterHourlyLevelDerivative):
        # Calculate the water level for each quarter-hourly sample.
        level = [0.0]*len(quarterHourlyLevelDerivative)
        level[0] = self.startingWaterLevel

        for i in range(1, len(quarterHourlyLevelDerivative)):
            level[i] = level[i-1] + quarterHourlyLevelDerivative[i]

            # Hardcode minimum and maximum water level
            if level[i] < 0.1:
                level[i] = 0.1  
            if level[i] > 2.6:
                level[i] = 2.6           

        return level

    def write_to_qtrhrl_csv(self, quarter_hourly_flow_rate, quarter_hourly_levels):
        # Write the rainfall, flow rate, water difference and water level to a csv file
        f = open('/home/iain/Desktop/IEL/Data/Generated Data/Quarter_Hourly_Generated_Data.csv', 'w')
        writer = csv.writer(f)
        writer.writerow(["Rainfall", "Flow Rate", "Water Level"])
        for i in range(len(quarter_hourly_flow_rate)):
            row = [round(self.rainfall[i], 1), round(quarter_hourly_flow_rate[i], 3), round(quarter_hourly_levels[i], 3)]
            writer.writerow(row)
        f.close()

    def write_to_day_csv(self, quarter_hourly_flow_rate, quarter_hourly_levels):
        # Write the rainfall, flow rate, water difference and water level to a csv file
        samples = len(quarter_hourly_flow_rate)
        numberOfDays = samples // 96
        f = open('/home/iain/Desktop/IEL/Data/Generated Data/Daily_Generated_Data.csv', 'w')
        writer = csv.writer(f)
        # Rainfall is cumulative (total); Flow Rate and Water Levels are both mean values.
        writer.writerow(["Rainfall", "Flow Rate", "Water Level"])
        for i in range(numberOfDays):
            precip = sum(self.rainfall[i*96:(i+1)*96])
            flow = sum(quarter_hourly_flow_rate[i*96:(i+1)*96])/96
            level = sum(quarter_hourly_levels[i*96:(i+1)*96])/96
            row = [round(precip, 1), round(flow, 3), round(level, 3)]
            writer.writerow(row)
        f.close()

    def read_rainfall_from_SEPA_api(self, stationName : str = "Dippen", samples = 100):
        # Read the rainfall data from the SEPA API
        # Can be provided other stations by changing the stationName parameter.

        # Get the id of the station. This is required to get the data.
        url = "https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getTimeseriesList&station_name=" + stationName + "&format=json"
        response = urlopen(url)
        data_json = json.loads(response.read())
        for entry in data_json:
            if entry[4] == "15minute.Total" and entry[6] == "Precip": # Get the id of the entry with "15minute.Total" and "Precip"
                id = entry[3]
                break

        # Calculate the period to use in the API request.
        number_of_days = (samples // 96) if (samples % 96 == 0) else (samples // 96) + 1
        period = "P" + str(number_of_days) + "D"

        # Get the rainfall data.
        url = "https://timeseries.sepa.org.uk/KiWIS/KiWIS?service=kisters&type=queryServices&datasource=0&request=getTimeseriesValues&ts_id=" + str(id) + "&period=" + period + "&returnfields=Timestamp,%20Value,%20Quality%20Code&format=json"
        response = urlopen(url)
        data_json = json.loads(response.read())
        rainfallData = [x[1] for x in data_json[0]["data"]][0:samples]
        return rainfallData, len(rainfallData)

    def read_rainfall_from_csv(self, filename, samples):
        # Read the rainfall data from a pre-downloaded CSV file. Useful if there's no internet connection available.
        rainfall = []
        
        with open(filename, 'r') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=';')
            # Skip the header row
            next(csvreader)
            
            # Read each row of data and extract the rainfall value
            for row in csvreader:
                try:
                    rainfall_value = float(row[1])
                    rainfall.append(rainfall_value)
                except ValueError:
                    # Skip rows that don't have valid rainfall data
                    pass
                
        # Truncate the data to the specified number of samples
        rainfall = rainfall[:samples]
        
        # Return the data and its length
        return rainfall, len(rainfall)
    
    def simplifyData(self, csvFileName, outputFilePath):
        # Read the data from the csv file and save to a pandas dataframe
        df = pd.read_csv(csvFileName, sep=',')

        # Calculate the bottom quartile and top quartile of the rainfall excluding where the rainfall is 0
        temp = df[df['Rainfall'] != 0]
        mean = temp['Rainfall'].mean()

        # Calculate the bottom quartile and top quartile of the flow rate
        bottomQuartileFlow = df['Flow Rate'].quantile(0.25)
        topQuartileFlow = df['Flow Rate'].quantile(0.75)

        # Calculate the bottom quartile and top quartile of the water level
        bottomQuartileLevel = df['Water Level'].quantile(0.25)
        topQuartileLevel = df['Water Level'].quantile(0.75)

        # Create a new dataframe with simplified data:
            # "Low" is used if the value is below the bottom quartile
            # "Medium" is used if the value is between the bottom and top quartile
            # "High" is used if the value is above the top quartile

        df2 = pd.DataFrame(columns=['Rainfall', 'Flow Rate', 'Water Level'])
        df2['Rainfall'] = df['Rainfall'].apply(lambda x: "Dry" if x == 0 else ("Light Rainfall" if x < mean else "Heavy Rainfall"))
        df2['Flow Rate'] = df['Flow Rate'].apply(lambda x: "Slow" if x < bottomQuartileFlow else ("Steady" if x < topQuartileFlow else "Fast"))
        df2['Water Level'] = df['Water Level'].apply(lambda x: "Low" if x < bottomQuartileLevel else ("Medium" if x < topQuartileLevel else "High"))

        # Save the simplified data to a csv file
        df2.to_csv(outputFilePath, index=False)     

if __name__ == "__main__":

    # Number of days to generate data for. Must be between 1 and 3125.
    numberOfDays = 20
    samples = 96 * numberOfDays
    assert numberOfDays <= 3125 and numberOfDays > 0, "Number of days must be between 1 and 3125"

    # Train the ML models to be used later.
    print("1: Initialising ML Model")
    predictor = Predictors()

    # Attempt to read the rainfall data from the SEPA API. If this fails, read the data from the csv file.
    try:
        print("2: Attempting to read rainfall data from SEPA API")
        rainfall, samples = DataGenerator(numOfSamples=samples, predictors=predictor).read_rainfall_from_SEPA_api(samples = samples)
    except:
        print("2: Couldn't access SEPA API, reading local CSV")
        rainfall, samples = DataGenerator(numOfSamples=samples, predictors=predictor).read_rainfall_from_csv("/home/iain/Desktop/IEL/Data/Quater_Hourly_Readings/Quarter_Hourly_Precipitation.csv", samples = samples)
    
    # Initialise the starting water level.
    starting_height = 0.5

    # Might not have been able to read the exact number of samples requested. Update the number of days to generate.
    numberOfDays = samples // 96

    # Keep a list of all flow rates and levels generated.
    all_flow_rates = []
    all_levels = []

    # Generate the data. Look at the Final_Plan.ipynb notebook for more information.
    # tqdm is just used to get a loading bar in the terminal.
    print("3: Generating Data")
    for i in tqdm(range(numberOfDays)):
        dg = DataGenerator(numOfSamples=96, rainfall=rainfall[i*96:(i+1)*96], startingWaterLevel=starting_height, predictors=predictor)
        quarter_hourly_flow_rate = dg.calculate_quarter_hourly_flow_rate(None)

        # Loop through 35 times, to get the measurements to be stable.
        for i in range(35):
            quarter_hourly_water_difference = dg.calculate_quarter_hourly_water_diff(quarter_hourly_flow_rate)
            daily_water_difference = sum(quarter_hourly_water_difference)
            daily_level_difference = dg.calculateDailyLevelDerivative(daily_water_difference, starting_height)
            quarter_hourly_level_difference = dg.calculateQuarterHourlyLevelDifference(daily_level_difference, quarter_hourly_water_difference)
            quarter_hourly_levels = dg.calculateQuarterHourlyLevel(quarter_hourly_level_difference)
            quarter_hourly_flow_rate = dg.calculate_quarter_hourly_flow_rate(quarter_hourly_levels)

        quarter_hourly_water_difference = dg.calculate_quarter_hourly_water_diff(quarter_hourly_flow_rate)
        daily_water_difference = sum(quarter_hourly_water_difference)
        daily_level_difference = quarter_hourly_levels[-1] - starting_height
        
        starting_height = quarter_hourly_levels[-1]
        all_flow_rates += quarter_hourly_flow_rate
        all_levels += quarter_hourly_levels

    # Finally write to the CSV files.
    print("4: Writing Data to CSV")
    dg = DataGenerator(numOfSamples=samples, rainfall=rainfall, predictors=predictor)
    dg.write_to_qtrhrl_csv(all_flow_rates, all_levels)
    dg.write_to_day_csv(all_flow_rates, all_levels)
    print("5: Done")

    dg.simplifyData("/home/iain/Desktop/IEL/Data/Generated Data/Quarter_Hourly_Generated_Data.csv", "/home/iain/Desktop/IEL/Data/Generated Data/Simplified Generated Data/Simplified_Quarter_Hourly_Data.csv")
    dg.simplifyData("/home/iain/Desktop/IEL/Data/Generated Data/Daily_Generated_Data.csv", "/home/iain/Desktop/IEL/Data/Generated Data/Simplified Generated Data/Simplified_Daily_Data.csv")