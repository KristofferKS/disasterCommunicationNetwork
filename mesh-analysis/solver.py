import json
import math

# ─────────────────────────────────────────────
#  Formula / Solver classes
# ─────────────────────────────────────────────

class Formula:
    def __init__(self, output, inputs, func, source=None):
        self.output = output
        self.inputs = inputs
        self.func   = func
        self.source = source  # which JSON file this came from

    def can_compute(self, known):
        return all(var in known for var in self.inputs) and self.output not in known

    def compute(self, known):
        values = [known[var] for var in self.inputs]
        return self.func(*values)


class Solver:
    def __init__(self):
        self.formulas = []           # all loaded formulas
        self._sources = {}           # path -> list[Formula]

    def load_file(self, path: str):
        """Load a JSON formula file and track which formulas came from it."""
        formulas = []
        with open(path) as f:
            data = json.load(f)
        for entry in data["formulas"]:
            args = ", ".join(entry["inputs"])
            fn   = eval(f"lambda {args}: {entry['expr']}", {"math": math})
            formula = Formula(entry["target"], entry["inputs"], fn, source=path)
            formulas.append(formula)
        self._sources[path] = formulas
        self.formulas.extend(formulas)
        return formulas

    def set_file_enabled(self, path: str, enabled: bool):
        """Enable or disable all formulas from a given file."""
        if path not in self._sources:
            return
        file_formulas = set(id(f) for f in self._sources[path])
        if enabled:
            # Re-add any from this file that aren't already present
            existing = set(id(f) for f in self.formulas)
            for f in self._sources[path]:
                if id(f) not in existing:
                    self.formulas.append(f)
        else:
            self.formulas = [f for f in self.formulas if id(f) not in file_formulas]

    def all_variables(self):
        variables = set()
        for f in self.formulas:
            variables.add(f.output)
            variables.update(f.inputs)
        return sorted(variables)

    def all_outputs(self):
        return sorted({f.output for f in self.formulas})

    def solve(self, known_values):
        known = dict(known_values)
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
        return known

    def get_missing(self, known_values, targets):
        solved = self.solve(known_values)
        missing = set()
        for target in targets:
            if target not in solved:
                for f in self.formulas:
                    if f.output == target:
                        for inp in f.inputs:
                            if inp not in solved:
                                missing.add(inp)
        return missing