"""
This file models a simple model of the worst case duty cycles for the communication nodes
"""

class DutyCycleModel:
    def __init__(self, N, C_cs):
        self.N = N
        self.C_cs = C_cs

    def delta_cs(self):
        return 1 / self.N *self.C_cs
    
    def delta_Tx(self):
        return 1 / self.N - self.delta_cs()

    def delta_Rx(self):
        return (self.N - 1) * self.delta_Tx()
    
    def delta_idle(self):
        return 1 - self.delta_Tx() - self.delta_Rx() - self.delta_cs()
    
    def plot(self):
        import matplotlib.pyplot as plt
        plt.figure(figsize=(8, 5))
        plt.plot(self.N, self.delta_Tx(), label="Tx")
        plt.plot(self.N, self.delta_Rx(), label="Rx")
        plt.plot(self.N, self.delta_cs(), label="CS")
        plt.plot(self.N, self.delta_idle(), label="Idle")
        plt.xlabel("Number of nodes (N)")
        plt.ylabel("Duty cycle")
        plt.title(f"Duty cycles vs number of nodes (C_cs={self.C_cs})")
        plt.legend()
        plt.grid()
        plt.show()



if __name__ == "__main__":
    import numpy as np

    N = np.linspace(2, 30, 29)    
    C_cs = 0.1
    model = DutyCycleModel(N, C_cs)
    model.plot()