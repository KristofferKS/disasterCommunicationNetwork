import math


class Formula:
    def __init__(self, output, inputs, func):
        """
        output: str → variable this formula computes
        inputs: list[str] → required variables
        func: function → calculation
        """
        self.output = output
        self.inputs = inputs
        self.func = func

    def can_compute(self, known):
        return all(var in known for var in self.inputs) and self.output not in known

    def compute(self, known):
        values = [known[var] for var in self.inputs]
        return self.func(*values)


class Solver:
    def __init__(self):
        self.formulas = []

    def add_formula(self, output, inputs, func):
        self.formulas.append(Formula(output, inputs, func))

    def solve(self, known_values):
        known = dict(known_values)  # copy

        changed = True
        while changed:
            changed = False

            for formula in self.formulas:
                if formula.can_compute(known):
                    try:
                        known[formula.output] = formula.compute(known)
                        changed = True
                    except Exception:
                        pass  # skip invalid computations (e.g. log(negative))

        return known

    def explain_missing(self, known_values, target):
        """Explains why a target variable cannot be computed."""
        known = dict(known_values)

        # First, solve as far as possible
        solved = self.solve(known)

        if target in solved:
            return f"'{target}' can already be computed: {solved[target]}"

        # Find all formulas that could produce the target
        candidate_formulas = [f for f in self.formulas if f.output == target]

        if not candidate_formulas:
            return f"'{target}' has no formula defined."

        lines = [f"Cannot compute '{target}'. Tried {len(candidate_formulas)} formula(s):"]
        for f in candidate_formulas:
            missing = [var for var in f.inputs if var not in solved]
            lines.append(f"  needs {f.inputs} → missing: {missing}")

        return "\n".join(lines)

    def dependency_chain(self, target, known_values=None, _depth=0, _visited=None):
        """
        Prints the full dependency tree for a target variable.
        known_values: optionally highlight which vars are already known.
        """
        if _visited is None:
            _visited = set()
        if known_values is None:
            known_values = {}

        indent = "  " * _depth

        # Already known — leaf node
        if target in known_values:
            print(f"{indent}✓ {target} = {known_values[target]}")
            return

        # Find all formulas that can produce this target
        candidate_formulas = [f for f in self.formulas if f.output == target]

        if not candidate_formulas:
            print(f"{indent}✗ {target} (no formula)")
            return

        # Avoid infinite recursion
        if target in _visited:
            print(f"{indent}↩ {target} (already expanded above)")
            return
        _visited.add(target)

        for i, formula in enumerate(candidate_formulas):
            print(f"{indent}→ {target}  [via: {', '.join(formula.inputs)}]")
            for inp in formula.inputs:
                self.dependency_chain(inp, known_values, _depth + 1, _visited.copy())

    def solve_interactive(self, known_values, constants: set):
        """
        Like solve(), but asks the user for missing values when stuck.
        constants: set of variable names that are true inputs (never derived).
        Returns only the constant values — derived values are stripped out.
        """
        known = dict(known_values)

        # Initial solve pass
        changed = True
        while changed:
            changed = False
            for formula in self.formulas:
                if formula.can_compute(known):
                    try:
                        known[formula.output] = formula.compute(known)
                        changed = True
                    except Exception:
                        pass

        # Ask for missing values
        asked = set()
        progress = True
        while progress:
            progress = False
            for formula in self.formulas:
                if formula.output in known:
                    continue
                missing = [v for v in formula.inputs if v not in known]
                for var in missing:
                    if var in asked:
                        continue
                    asked.add(var)
                    raw = input(f"  Do you have a value for '{var}'? (enter value or leave blank to skip): ").strip()
                    if raw:
                        try:
                            known[var] = float(raw)
                            constants.add(var)  # mark as a user-provided constant
                            progress = True
                            # Re-run solver with new info
                            changed = True
                            while changed:
                                changed = False
                                for f in self.formulas:
                                    if f.can_compute(known):
                                        try:
                                            known[f.output] = f.compute(known)
                                            changed = True
                                        except Exception:
                                            pass
                        except ValueError:
                            print(f"  Invalid number, skipping '{var}'.")

        # Only return the constants — strip all derived values
        return {k: v for k, v in known.items() if k in constants}


solver = Solver()

import json, math


def load_formulas(solver, path: str):
    with open(path) as f:
        data = json.load(f)
    for entry in data["formulas"]:
        args = ", ".join(entry["inputs"])
        fn = eval(f"lambda {args}: {entry['expr']}", {"math": math})
        solver.add_formula(entry["target"], entry["inputs"], fn)


if __name__ == "__main__":
    import numpy as np
    import matplotlib.pyplot as plt

    load_formulas(solver, "mesh-analysis/formulas.json")
    load_formulas(solver, "mesh-analysis/mesh_formulas.json")

    lambda_m_values = np.linspace(0.1, 10, 50)
    minimum_k_results = []
    delta_Tx_results = []

    # True constants — only these survive the interactive solve
    CONSTANTS = {"k", "n", "R", "C", "R_max", "mu"}

    base_known = {
        "k": 4,
        "n": 100,
        "R": 3_456_000,
        "C": 2,
        "R_max": 5_000_000,
        "mu": 0.7,
    }

    # Check once with a sample value if anything is missing
    sample = solver.solve({**base_known, "lambda_m": lambda_m_values[0]})
    if sample.get("delta_Tx") is None or sample.get("minimum_k") is None:
        print("\nSome values could not be computed. Let me ask for missing inputs...\n")
        # solve_interactive returns only constants — no derived values leak in
        base_known = solver.solve_interactive(
            {**base_known, "lambda_m": lambda_m_values[0]},
            constants=CONSTANTS
        )

    # Now run the sweep — lambda_m varies, everything else is a clean constant
    for lambda_m in lambda_m_values:
        known = {**base_known, "lambda_m": lambda_m}
        results = solver.solve(known)
        minimum_k_results.append(results.get("minimum_k"))
        delta_Tx_results.append(results.get("delta_Tx"))

    plt.plot(lambda_m_values, delta_Tx_results)
    plt.xlabel("lambda_m")
    plt.ylabel("delta_Tx")
    plt.title("Required delta_Tx vs lambda_m")
    plt.grid()
    plt.show()