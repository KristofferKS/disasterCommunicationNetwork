"""
Power model for node in cluster, based on duty cycles and power consumption of different states (Tx, Rx, Idle)
"""

from visualizer import PowerModelVisualizer


# Helper function to load technology parameters from JSON file
def load_technologies():
    # Load Technology Parameters from JSON
    _current_dir = path.dirname(path.abspath(__file__))
    _tech_file_path = path.join(_current_dir, 'technologies.json')
    with open(_tech_file_path, 'r') as f:
        TECHNOLOGIES = load(f)
    return TECHNOLOGIES

# Helper function to load scenario parameters from JSON file
def load_parameters():
    # Load Parameters from JSON
    _current_dir = path.dirname(path.abspath(__file__))
    _param_file_path = path.join(_current_dir, 'parameters.json')
    with open(_param_file_path, 'r') as f:
        params = load(f)
    
    lambda_m = params["lambda_m"] # msg/s   message rate per node (1 per minute)
    M = params["M"] # bits    message size (10 s @ 3.2 kbit/s Codec2)
    N = params["N"] # —       nodes per cluster
    C_bat = params["C_bat"] # mAh     battery capacity

    return lambda_m, M, N, C_bat

if __name__ == "__main__":

    from json import load
    from os import path
    from numpy import linspace

    TECHNOLOGIES = load_technologies()
    lambda_m, M, N, C_bat = load_parameters()

    plotter = PowerModelVisualizer(lambda_m, M, N, tech=TECHNOLOGIES, C_bat=C_bat)

    lambda_m_linspace = linspace(0.001, 3, 10000)
    M_linspace = linspace(10, 10000, 1000)
    N_linspace = linspace(1, 300, 1000)
    C_bat_linspace = linspace(100, 4000, 1000)

    plotter.modellerXvY(lambda_m_linspace, "lambda_m", y_var="T_life", ylabel="Battery Life (hours)", title="Battery Life vs Message Rate for Different Technologies")
    plotter.modellerXvY(M_linspace, "M", y_var="T_life", ylabel="Battery Life (hours)", title="Battery Life vs Message Size for Different Technologies")
    plotter.modellerXvY(N_linspace, "N", y_var="T_life", ylabel="Battery Life (hours)", title="Battery Life vs Cluster Size for Different Technologies")
    plotter.modellerXvY(C_bat_linspace, "C_bat", y_var="T_life", ylabel="Battery Life (hours)", title="Battery Life vs Battery Capacity for Different Technologies")
