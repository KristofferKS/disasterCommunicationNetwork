class PowerModel:
    def __init__(self, lambda_m, M, N, tech, C_bat):
        self.lambda_m = self.lambda_m_base = lambda_m
        self.M = self.M_base = M
        self.N = self.N_base = N
        self.C_bat = self.C_bat_base = C_bat
        self.tech = tech

    def return_to_base(self):
        self.lambda_m = self.lambda_m_base
        self.M = self.M_base
        self.N = self.N_base
        self.C_bat = self.C_bat_base

    def delta_Tx(self, tech_params):
        return self.lambda_m * self.M / (tech_params["eta"] * tech_params["R_raw"])
    
    def delta_Rx(self, tech_params):
        return (self.N - 1) * self.lambda_m * self.M / (tech_params["eta"] * tech_params["R_raw"])
    
    def delta_idle(self, tech_params):
        return 1 - self.delta_Tx(tech_params) - self.delta_Rx(tech_params)

    def power_model(self, tech_params):
        d_tx   = self.delta_Tx(tech_params)
        d_rx   = self.delta_Rx(tech_params)
        d_idle = self.delta_idle(tech_params)

        if d_tx + d_rx >= 1:
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

    def plot(self, x_values, y_var, xlabel, ylabel, title):
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 6))
        for tech, data in self.results.items():
            if y_var in data and len(data[y_var]) == len(x_values):
                plt.plot(x_values, data[y_var], label=tech)
        
        if xlabel == "lambda_m":
            from matplotlib.ticker import LogFormatterMathtext, LogLocator
            plt.xscale("log", base=10)
            axis = plt.gca().xaxis
            axis.set_major_locator(LogLocator(base=10))
            axis.set_major_formatter(LogFormatterMathtext(base=10))
        

        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)
        plt.legend()
        plt.grid()
        plt.show()

        self.return_to_base() # reset parameters after plotting

    def modellerXvY(self, x_values, x_var_name, y_var, ylabel, title):
        """Plot T_life vs lambda_m for different technologies"""
        self.x_values = x_values

        self.results = {}
        for key, value in self.tech.items():
            if value["viable"]:
                self.results[key] = {y_var: []}

        for x_value in self.x_values:
            setattr(self, x_var_name, x_value)
            for key, value in self.tech.items():
                if not value["viable"]:
                    continue
                pm = self.power_model(value)
                if pm is not None:
                    self.results[key][y_var].append(pm[y_var])
                else:
                    self.results[key][y_var].append(None)

        self.plot(self.x_values, y_var=y_var, xlabel=x_var_name, ylabel=ylabel, title=title)