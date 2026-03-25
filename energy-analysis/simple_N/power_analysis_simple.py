from duty_cycles_simple import DutyCycleModel

class PowerModel:
    def __init__(self, duty_cycle_model, P_Tx, P_Rx, P_cs, P_idle):
        self.duty_cycle_model = duty_cycle_model
        self.P_Tx = P_Tx
        self.P_Rx = P_Rx
        self.P_cs = P_cs
        self.P_idle = P_idle

    def power_consumption(self):
        delta_Tx = self.duty_cycle_model.delta_Tx()
        delta_Rx = self.duty_cycle_model.delta_Rx()
        delta_cs = self.duty_cycle_model.delta_cs()
        delta_idle = self.duty_cycle_model.delta_idle()

        return (delta_Tx * self.P_Tx +
                delta_Rx * self.P_Rx +
                delta_cs * self.P_cs +
                delta_idle * self.P_idle)
    

if __name__ == "__main__":
    import numpy as np
    import matplotlib.pyplot as plt

    N = np.linspace(2, 30, 29)    
    C_cs = 0.1
    duty_cycle_model = DutyCycleModel(N, C_cs)

    P_Tx = 100  # mW
    P_Rx = 50   # mW
    P_cs = 50   # mW
    P_idle = 5  # mW

    power_model = PowerModel(duty_cycle_model, P_Tx, P_Rx, P_cs, P_idle)
    power_consumption = power_model.power_consumption()

    plt.figure(figsize=(8, 5))
    plt.plot(N, power_consumption, label="Power Consumption (mW)")
    plt.xlabel("Number of nodes (N)")
    plt.ylabel("Power Consumption (mW)")
    plt.title(f"Power Consumption vs Number of Nodes (C_cs={C_cs})")
    plt.legend()
    plt.grid()
    plt.show()