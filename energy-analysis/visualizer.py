from power_model import PowerModel

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