from solver import Solver
from solver_gui import SolverApp

# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    paths = [
        "mesh-analysis/Calculation-Formulas/formulas.json",
        "mesh-analysis/Calculation-Formulas/mesh_formulas.json",
    ]

    solver = Solver()
    for p in paths:
        solver.load_file(p)

    app = SolverApp(solver, json_paths=paths)
    app.mainloop()