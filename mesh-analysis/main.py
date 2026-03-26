import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass

@dataclass
class MeshParameters:
    n: float          # Number of nodes
    k: float          # Average number of neighbors
    C: float          # Topology-dependent constant
    lambda_m: float   # Messages per second per node
    M: float          # Message size
    R: float          # Data rate


class MeshCalculator:
    def __init__(self, params: MeshParameters):
        self.p = params

    @property
    def BC(self):
        return self.p.n / self.p.k

    @property
    def average_shortest_path_length(self):
        return np.log(self.p.n) / np.log(self.p.k)

    @property
    def clustering_coefficient(self):
        return self.p.k / self.p.n

    @property
    def minimum_degree(self):
        return max(1, np.log(self.p.n))

    @property
    def failure_tolerance(self):
        if self.p.k <= 1:
            raise ValueError("k must be > 1 for failure tolerance")
        return 1 - (1 / (self.p.k - 1))

    @property
    def total_data(self):
        return self.p.lambda_m * self.p.M * self.p.n

    @property
    def minimum_k(self):
        return self.p.C * (self.total_data * self.p.n / (2 * self.p.R))

    def results(self):
        return {
            "BC": self.BC,
            "average_shortest_path_length": self.average_shortest_path_length,
            "clustering_coefficient": self.clustering_coefficient,
            "minimum_degree": self.minimum_degree,
            "failure_tolerance": self.failure_tolerance,
            "total_data": self.total_data,
            "minimum_k": self.minimum_k,
        }

def sweep_parameter(base_params: MeshParameters, param_name: str, values, metric: str):
    """
    Vary ANY parameter and compute ANY metric (vectorized).
    """
    values = np.array(values)

    params = {k: getattr(base_params, k) for k in vars(base_params)}

    params[param_name] = values

    n = params['n']
    k = params['k']
    C = params['C']
    lambda_m = params['lambda_m']
    M = params['M']
    R = params['R']

    D_total = lambda_m * M * n

    results = {
        "BC": n / k,
        "average_shortest_path_length": np.log(n) / np.log(k),
        "clustering_coefficient": k / n,
        "minimum_degree": np.maximum(1, np.log(n)),
        "failure_tolerance": 1 - (1 / (k - 1)),
        "total_data": D_total,
        "minimum_k": C * (D_total * n / (2 * R)),
    }

    if metric not in results:
        raise ValueError(f"Unknown metric: {metric}")

    return values, results[metric]


def plot_sweep(base_params, param_name, values, metric):
    x, y = sweep_parameter(base_params, param_name, values, metric)

    plt.plot(x, y)
    plt.xlabel(param_name)
    plt.ylabel(metric)
    plt.title(f"{metric} vs {param_name}")
    plt.grid()
    plt.show()


if __name__ == "__main__":

    params = MeshParameters(
        n=100,
        k=4,
        C=1,
        lambda_m=1,
        M=2800,
        R=3_456_000
    )

    calculator = MeshCalculator(params)

    n_values = np.linspace(10, 100, 100)
    plot_sweep(params, "n", n_values, "minimum_k")

    R_values = np.linspace(1e6, 1e7, 100)
    plot_sweep(params, "R", R_values, "minimum_k")

    k_values = np.linspace(2, 20, 100)
    plot_sweep(params, "k", k_values, "failure_tolerance")