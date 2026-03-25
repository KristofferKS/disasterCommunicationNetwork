"""
Power model for node in cluster, based on duty cycles and power consumption of different states (Tx, Rx, Idle)
"""

class PowerModel:
    def __init__(self, lambda_m, M, N, tech, C_bat):
        self.lambda_m = lambda_m
        self.M = M
        self.N = N
        self.tech = tech
        self.C_bat = C_bat

    def delta_Tx(self, tech_params):
        print(type(tech_params))
        return self.lambda_m * self.M / tech_params["eta"] / tech_params["R_raw"]
    
    def delta_Rx(self, tech_params):
        return (self.N - 1) * self.lambda_m * self.M / tech_params["eta"] / tech_params["R_raw"]
    
    def delta_idle(self, tech_params):
        return 1 - self.delta_Tx(tech_params) - self.delta_Rx(tech_params)

    def power_model(self, tech_params):
        d_tx   = self.delta_Tx(tech_params)
        d_rx   = self.delta_Rx(tech_params)
        d_idle = self.delta_idle(tech_params)

        if d_tx + d_rx >= 1:
            print(f"duty cycle saturation. this tech is not viable, larger throughput required to meet requirements.")
            return None

        I_bar  = (tech_params["I_base"]
                + d_idle * tech_params["I_idle"]
                + d_tx   * tech_params["I_tx"]
                + d_rx   * tech_params["I_rx"])

        T_life = self.C_bat / I_bar                                     # hours

        return dict(d_tx=d_tx, d_rx=d_rx, d_idle=d_idle,
                    I_bar=I_bar, T_life=T_life)

# class for visualizing output of power model, e.g. plotting T_life vs lambda_m for different technologies, or T_life vs cluster size for different technologies
class PowerModelVisualizer(PowerModel):

    def plot(self, x_values, xlabel, ylabel, title):
        plt.figure(figsize=(10, 6))
        for tech, data in self.results.items():
            if "T_life" in data and len(data["T_life"]) == len(x_values):
                plt.plot(x_values, data["T_life"], label=tech)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)
        plt.legend()
        plt.grid()
        plt.show()

    def plot_T_life_vs_lambda_m(self, lambda_m_values):
        """Plot T_life vs lambda_m for different technologies"""
        self.lambda_m_values = lambda_m_values
        
        self.results = {}
        for key, value in self.tech.items():
            if value["viable"]:
                self.results[key] = {"T_life": []}

        for lambda_m in self.lambda_m_values:
            self.lambda_m = lambda_m
            for key, value in self.tech.items():
                if not value["viable"]:
                    continue
                pm = self.power_model(value)
                if pm is not None:
                    self.results[key]["T_life"].append(pm["T_life"])
                else:
                    self.results[key]["T_life"].append(None)
                    
        self.plot(self.lambda_m_values, xlabel="Message Rate (msg/s)", ylabel="Battery Life (hours)", title="Battery Life vs Message Rate for Different Technologies")
    
    def plot_T_life_vs_cluster_size(self):
        pass

    def plot_T_life_vs_M(self):
        pass

    def plot_T_life_vs_Bat_capacity(self):
        pass

    def barPlot_cycle(self):
        pass

# Helper function to load technology parameters from JSON file
def load_technologies():
    # Load Technology Parameters from JSON
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _tech_file_path = os.path.join(_current_dir, 'technologies.json')
    with open(_tech_file_path, 'r') as f:
        TECHNOLOGIES = json.load(f)
    return TECHNOLOGIES

# Helper function to load scenario parameters from JSON file
def load_parameters():
    # Load Parameters from JSON
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _param_file_path = os.path.join(_current_dir, 'parameters.json')
    with open(_param_file_path, 'r') as f:
        params = json.load(f)
    
    lambda_m = params["lambda_m"] # msg/s   message rate per node (1 per minute)
    M = params["M"] # bits    message size (10 s @ 3.2 kbit/s Codec2)
    N = params["N"] # —       nodes per cluster
    C_bat = params["C_bat"] # mAh     battery capacity

    return lambda_m, M, N, C_bat

if __name__ == "__main__":

    import json
    import os
    import matplotlib.pyplot as plt
    import numpy as np

    TECHNOLOGIES = load_technologies()
    lambda_m, M, N, C_bat = load_parameters()

    plotter = PowerModelVisualizer(lambda_m, M, N, tech=TECHNOLOGIES, C_bat=C_bat)

    lambda_m_linspace = np.linspace(0.01, 2, 100)
    plotter.plot_T_life_vs_lambda_m(lambda_m_linspace)

    """
    results = {}
    for tech_name, tech_params in TECHNOLOGIES.items():
        if not tech_params["viable"]:
            print(f"{tech_name} is not viable:")
            continue

        model = PowerModel(lambda_m, M, N, tech=tech_params, C_bat=C_bat)
        results[tech_name] = model.power_model()
        print(f"{tech_name}: {results[tech_name]}\n")
    """
