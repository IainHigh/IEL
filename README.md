# IEL
Project for the Informatics Experiential Learning course

## Data
This directory contains both the real data accessed from the SEPA API and the generated data which was generated from DataGenerator.py
#### Real Data
More information about this can be found in the README.md in the ReadData directory
#### Generated Data
Contains the data generated from the DateGenerator.py script. Also contains the simplified data generated from the simplifyData function in the DataGenerator.py script. More information about the simplified data can be found in the simplifyData function definition.

## Notebooks
This directory contains two Jupyter notebooks - "Generated Data Exploration.ipynb" and "Real Data Exploration.ipynb". These notebooks contain the code used to explore the data and the results of the exploration. Can be used to check the accuracy and realism of the generated data by comparing the output of "Generated Data Exploration.ipynb" to the output of "Real Data Exploration.ipynb".

## DataGenerator.py
This script contains the code used to generate the data. This script can be run from the command line using the following command:
>>> python3 DataGenerator.py

## DataGeneratorPredictors.py
This is a helper class for the DataGenerator.py script. This class contains the code used to create ML models using sklearn on the real data and then use these models to predict the values of the generated data. This class is used by the DataGenerator.py script to predict the values of the generated data.