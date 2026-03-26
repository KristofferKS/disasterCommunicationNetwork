# disasterCommunicationNetwork

## Energy Analysis
This repository contains a small energy-analysis tool for comparing communication technologies in a disaster communication network. It estimates node battery life from message traffic, cluster size, and battery capacity, and visualizes results across multiple technology profiles.

### How to use

1. Install dependencies:
	```bash
	pip install -r requirements.txt
	```
2. Configure scenario values in `energy-analysis/parameters.json`:
	- `lambda_m` (message rate per node, msg/s)
	- `M` (message size, bits)
	- `N` (nodes per cluster)
	- `C_bat` (battery capacity, mAh)
3. Configure or adjust technology parameters in `energy-analysis/technologies.json`.
4. Run the analysis script:
	```bash
	python energy-analysis/main.py
	```
5. change modelling linspaces
    If necessary the ranges for the modelling can be changed as well as, labels, titles and so on in the __main__
6. Review the generated plots for battery life versus:
	- message rate
	- message size
	- cluster size
	- battery capacity


## Mesh analysis
This repository contains a mesh-analysis application for creating graphs using some formulas given in a json format and some constants in the GUI.

### How to use

1. Install dependencies:
	```bash
	pip install -r requirements.txt
	```
2. For manually adding additional json file add the path to the paths list in mesh-analysis/main.py. The format for a formula is:

	```
	{
      "target": TARGET_VARIABLE_NAME_STRING,
      "inputs": INPUT_VARIABLE_NAMES_LIST[STRING],
      "expr": FORMULA_EXPRESSION_STRING
    }
	```
	example:
	```
	{
      "target": "R",
      "inputs": ["delta_Tx", "lambda_m", "M"],
      "expr": "delta_Tx * M / lambda_m"
    }
	```
3. Run the script
	```
	python mesh-analysis/main.py
	```
4. In case off pressing PLOT and no graph is given look bellow the button and add the required constants
