"""
Power model for node in cluster, based on duty cycles and power consumption of different states (Tx, Rx, Idle)

How to use:
1. Define parameters of technologies in technologies.json
2. Define scenario parameters in parameters.json
3. Run this script to generate plots of battery life vs message rate, message size, cluster size, and battery capacity for different technologies
"""

from power_model import PowerModelVisualizer

# Helper function to load technology parameters and scenario parameters from JSON file
def load_tech_and_param():
    
    _current_dir = path.dirname(path.abspath(__file__))
    files = ['technologies.json', 'parameters.json']
    for i in range(2):
        _tech_file_path = path.join(_current_dir, files[i])
        with open(_tech_file_path, 'r') as f:
            if i == 0:
                TECHNOLOGIES = load(f)          # Technology specific parameters [dictionary of dictionaries, one per technology]
            else:
                params = load(f)
                lambda_m = params["lambda_m"]   # msg/s   message rate per node (1 per minute)
                M = params["M"]                 # bits    message size (10 s @ 3.2 kbit/s Codec2)
                N = params["N"]                 # —       nodes per cluster
                C_bat = params["C_bat"]         # mAh     battery capacity

    
    return TECHNOLOGIES, lambda_m, M, N, C_bat


if __name__ == "__main__":

    from json import load
    from os import path
    from numpy import linspace

    TECHNOLOGIES, lambda_m, M, N, C_bat = load_tech_and_param()

    plotter = PowerModelVisualizer(lambda_m, M, N, tech=TECHNOLOGIES, C_bat=C_bat)

    lambda_m_linspace = linspace(0.001, 3, 10000)
    M_linspace = linspace(10, 10000, 1000)
    N_linspace = linspace(1, 300, 1000)
    C_bat_linspace = linspace(100, 4000, 1000)

    info_lambda_m = [
        lambda_m_linspace,
        "lambda_m",
        "T_life",
        "Battery Life vs Message Rate for Different Technologies",
        "Message Rate (msg/s)",
        "Battery Life (hours)"
    ]
    info_M = [
        M_linspace,
        "M",
        "T_life",
        "Battery Life vs Message Size for Different Technologies",
        "Message Size (bits)",
        "Battery Life (hours)"
    ]
    info_N = [
        N_linspace,
        "N",
        "T_life",
        "Battery Life vs Cluster Size for Different Technologies",
        "Cluster Size (nodes)",
        "Battery Life (hours)"
    ]
    info_C_bat = [
        C_bat_linspace,
        "C_bat",
        "T_life",
        "Battery Life vs Battery Capacity for Different Technologies",
        "Battery Capacity (mAh)",
        "Battery Life (hours)"
    ]

    plotter.modellerXvY(info_lambda_m)
    plotter.modellerXvY(info_M)
    plotter.modellerXvY(info_N)
    plotter.modellerXvY(info_C_bat)
