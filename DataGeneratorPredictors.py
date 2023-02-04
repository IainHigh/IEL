from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import random

class Predictors:

    def __init__(self):
        self.qtrData = self.setUpQuarterHourly()
        self.dailyData = self.setUpDaily()

        self.quarterHourlyFlowAgainstLevel(plotGraph=False, displayStats=False)
        self.dailyLevelAgainstWaterDifference(plotGraph=False, displayStats=False)

    def setUpQuarterHourly(self):
        # Import the data
        flow = pd.read_csv('Data/Quater_Hourly_Readings/Quarter_Hourly_Flow_Rate.csv', delimiter=';')
        flow.rename(columns={'Value': 'Mean Flow (m3/s)'}, inplace=True)
        rain = pd.read_csv('Data/Quater_Hourly_Readings/Quarter_Hourly_Precipitation.csv', delimiter=';')
        rain.rename(columns={'Value': 'Precipitation (mm)'}, inplace=True)
        level = pd.read_csv('Data/Quater_Hourly_Readings/Quarter_Hourly_Level.csv', delimiter=';')
        level.rename(columns={'Value': 'Water Level (m)'}, inplace=True)

        # Merge the data
        merged = pd.merge(flow, rain, on='#Timestamp')
        merged = pd.merge(merged, level, on='#Timestamp')
        merged = merged.drop('Quality Code', axis=1)
        merged = merged.drop('Quality Code_x', axis=1)
        merged = merged.drop('Quality Code_y', axis=1)
        merged.dropna(inplace=True)

        return merged

    def setUpDaily(self):
        # Import the new data and create a dataframe
        daily_flow = pd.read_csv('Data/Daily_Averages/Daily_Mean_Flow_Rate.csv', delimiter=';')
        daily_flow.rename(columns={'Value': 'Mean Flow (m3/s)'}, inplace=True)
        daily_rain = pd.read_csv('Data/Daily_Averages/Daily_Precipitation.csv', delimiter=';')
        daily_rain.rename(columns={'Value': 'Daily Precipitation (mm)'}, inplace=True)
        daily_level = pd.read_csv('Data/Daily_Averages/Daily_Mean_Level.csv', delimiter=';')
        daily_level.rename(columns={'Value': 'Mean Water Level (m)'}, inplace=True)

        # Merge the 3 datasets into one
        merged = pd.merge(daily_flow, daily_rain, on=['#Timestamp'])
        merged = pd.merge(merged, daily_level, on=['#Timestamp'])
        merged = merged.drop('Quality Code_x', axis=1)
        merged = merged.drop('Quality Code_y', axis=1)
        merged = merged.drop('Quality Code', axis=1)
        merged.dropna(inplace=True)
        
        # Calculate the water difference TODO: Check this
        merged['Water Difference (m3)'] = merged['Daily Precipitation (mm)']*45000 - merged['Mean Flow (m3/s)']*86400

        # Calculate the level difference
        levelDerivative = []
        previous = merged['Mean Water Level (m)'][0]
        flag = True
        for i in merged['Mean Water Level (m)']:
            diff = i - previous
            if not flag:
                levelDerivative.append(diff)
            flag = False
            previous = i
        levelDerivative.append(0)
        merged['level_derivative'] = levelDerivative

        return merged

    def quarterHourlyFlowAgainstLevel(self, plotGraph = False, displayStats = False):
        # Only use water levels between 0.2 and 2
        normalRange = self.qtrData[(self.qtrData['Water Level (m)'] > 0.2) & (self.qtrData['Water Level (m)'] < 2)]
        X = normalRange['Water Level (m)'].values.reshape(-1, 1)
        y = normalRange['Mean Flow (m3/s)'].values.reshape(-1, 1)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
        quadratic = PolynomialFeatures(degree=3)
        X_quad = quadratic.fit_transform(X)
        X_quad_test = quadratic.fit_transform(X_test)
        lr = LinearRegression()
        lr.fit(X_quad, y)

        # Calculate and display the mean squared error and R^2
        if displayStats:
            y_quad_fit = lr.predict(X_quad)
            y_quad_pred = lr.predict(X_quad_test)
            print('MSE train: %.3f, test: %.3f' % (
                mean_squared_error(y, y_quad_fit),
                mean_squared_error(y_test, y_quad_pred)))
            print('R^2 train: %.3f, test: %.3f' % (
                r2_score(y, y_quad_fit),
                r2_score(y_test, y_quad_pred)))

        # Plot the polynomial curve
        if plotGraph:

            # Plot the data points
            X = self.qtrData['Water Level (m)'].values.reshape(-1, 1)
            y = self.qtrData['Mean Flow (m3/s)'].values.reshape(-1, 1)
            plt.scatter(X, y, label='data points', color='lightgray', marker='.')
            
            # For low water levels, we will use a line
            x = np.linspace(0, 0.2, 100)
            y = x*0.5
            plt.plot(x, y, label='predicted', color='red')

            # For normal water levels, we will use the polynomial curve
            x = np.linspace(0.2, 2, 1000)
            y = lr.predict(quadratic.fit_transform(x.reshape(-1, 1)))
            plt.plot(x, y, label='predicted', color='red')

            # For high water levels, we will use a line
            x = np.linspace(2, 4, 1000)
            offset = 60 - lr.predict(quadratic.fit_transform(np.array(2).reshape(-1, 1)))[0][0]
            y = x*30 - offset
            plt.plot(x, y, label='predicted', color='red')

            plt.legend(loc='upper left')
            plt.title('Regression of Flow Rate against Water Level')
            plt.xlabel('Water Level (m)')
            plt.ylabel('Flow Rate (m3/s)')
            plt.show()

        self.lr1 = lr

    def generateQuarterHourlyFlow(self, level):
        quadratic = PolynomialFeatures(degree=3)

        if (level < 0):
            return 0

        if (level <= 0.2):
            # If the level is below 0.2m, the flow rate is directly proportional to the level with tiny noise
            return level*0.5

        if (level >= 2):
            # If the level is above 2m, the flow rate is directly proportional to the level with tiny noise
            offset = 60 - self.lr1.predict(quadratic.fit_transform(np.array(2).reshape(-1, 1)))[0][0]
            return level*30 - offset
        
        level = np.array(level).reshape(-1, 1)
        temp = self.lr1.predict(quadratic.fit_transform(level))[0][0]
        return temp

    def dailyLevelAgainstWaterDifference(self, plotGraph = False, displayStats = False):
        # Remove days with water difference > 2000000 and > 2000000
        typical = self.dailyData[self.dailyData['Water Difference (m3)'] < 2000000]
        typical = typical[typical['Water Difference (m3)'] > -2000000]

        # Fit a polynomial curve of Water difference (independent) and level derivative (dependent)
        X = typical['Water Difference (m3)'].values.reshape(-1, 1)
        y = typical['level_derivative'].values.reshape(-1, 1)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
        quadratic = PolynomialFeatures(degree=1)
        X_quad = quadratic.fit_transform(X)
        X_quad_test = quadratic.fit_transform(X_test)
        lr = LinearRegression()
        lr.fit(X_quad, y)

        # Calculate and display the mean squared error and R^2
        y_quad_pred = lr.predict(X_quad_test)
        if displayStats:
            y_quad_fit = lr.predict(X_quad)
            print('MSE train: %.3f, test: %.3f' % (
                mean_squared_error(y, y_quad_fit),
                mean_squared_error(y_test, y_quad_pred)))
            print('R^2 train: %.3f, test: %.3f' % (
                r2_score(y, y_quad_fit),
                r2_score(y_test, y_quad_pred)))

        if plotGraph:
            # Plot the polynomial curve
            plt.scatter(X, y, label='data points', color='lightgray', marker='.')

            x = np.linspace(min(X), max(X), 1000)
            y = lr.predict(quadratic.fit_transform(x.reshape(-1, 1)))
            plt.plot(x, y, label='predicted', color='red')

            plt.xlim(-2000000, 2000000)
            plt.ylim(-1, 2)

            plt.legend(loc='upper left')
            plt.title('Regression of Flow Rate against Water Level')
            plt.xlabel('Water Difference (m3)')
            plt.ylabel('Level Derivative (m)')
            plt.show()

        # Calculate the standard deviation of the residuals
        residuals = y_quad_pred - y_test
        
        # Return the linear regression model, the residuals and the X values
        self.lr2 = lr
        self.residuals2 = residuals
        
    def generateLevelDerivativeFromWaterDifference(self, waterDifference):
        quadratic = PolynomialFeatures(degree=1)
        waterDifference = np.array(waterDifference).reshape(-1, 1)
        temp = self.lr2.predict(quadratic.fit_transform(waterDifference))[0][0]
        return random.gauss(temp, np.std(self.residuals2)) / 2