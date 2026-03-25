"""
Power model for node in cluster, based on duty cycles and power consumption of different states (Tx, Rx, CS, Idle)
"""

class PowerModel:
    def __init__(self, lambda_m, M, N, time_cs, tech, C_bat):
        self.lambda_m = lambda_m
        self.M = M
        self.N = N
        self.time_cs = time_cs
        self.tech = tech
        self.C_bat = C_bat

    def delta_Tx(self):
        return self.lambda_m * self.M / self.tech["eta"] / self.tech["R_raw"]
    
    def delta_Rx(self):
        return (self.N - 1) * self.lambda_m * self.M / self.tech["eta"] / self.tech["R_raw"]
    
    def delta_cs(self):
        return self.lambda_m * self.time_cs
    
    def delta_idle(self):
        return 1 - self.delta_Tx() - self.delta_Rx() - self.delta_cs()
    
    def power_model(self):
        d_tx   = self.delta_Tx()
        d_rx   = self.delta_Rx()
        d_cs   = self.delta_cs()
        d_idle = self.delta_idle()

        if d_tx + d_rx >= 1:
            print(f"duty cycle saturation. this tech is not viable, larger throughput required to meet requirements.")
            return None

        I_bar  = (self.tech["I_base"]
                + d_idle * self.tech["I_idle"]
                + d_tx   * self.tech["I_tx"]
                + d_rx   * self.tech["I_rx"]
                + d_cs   * self.tech["I_cs"])

        T_life = self.C_bat / I_bar                                          # hours
        

        return dict(d_tx=d_tx, d_rx=d_rx, d_cs=d_cs, d_idle=d_idle,
                    I_bar=I_bar, T_life=T_life)

# class for visualizing output of power model, e.g. plotting T_life vs lambda_m for different technologies, or T_life vs cluster size for different technologies
class PowerModelVisualizer:
    def __init__(self, results):
        self.results = results

    def plot_T_life_vs_lambda_m(self):
        pass

    def plot_T_life_vs_cluster_size(self):
        pass

    def plot_T_life_vs_M(self):
        pass

import json
import os

# Helper function to load technology parameters from JSON file
def load_technologies():
    # Load Technology Parameters from JSON
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _tech_file_path = os.path.join(_current_dir, 'technologies.json')
    with open(_tech_file_path, 'r') as f:
        TECHNOLOGIES = json.load(f)
    return TECHNOLOGIES


# Scenario Parameters     
M          = 32_000    # bits    message size (10 s @ 3.2 kbit/s Codec2)
lambda_m   = 10 / 60    # msg/s   message rate per node (1 per minute)
N          = 16         # —       nodes per cluster
C_bat      = 3000      # mAh     battery capacity
T_lat_max  = 5.0       # s       max acceptable latency budget
time_cs    = 0.1       # s       time spent in channel sensing per message


if __name__ == "__main__":

    import matplotlib.pyplot as plt

    TECHNOLOGIES = load_technologies()

    results = {}
    for tech_name, tech_params in TECHNOLOGIES.items():
        if not tech_params["viable"]:
            print(f"{tech_name} is not viable:")
            continue

        model = PowerModel(lambda_m, M, N, time_cs, tech=tech_params, C_bat=C_bat)
        results[tech_name] = model.power_model()
        print(f"{tech_name}: {results[tech_name]}\n")
