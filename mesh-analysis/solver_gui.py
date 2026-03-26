import math
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from solver import Solver, Formula



# ─────────────────────────────────────────────
#  Theme
# ─────────────────────────────────────────────

DARK_BG    = "#1a1a2e"
PANEL_BG   = "#16213e"
ACCENT     = "#0f3460"
HIGHLIGHT  = "#e94560"
SUCCESS    = "#2ecc71"
TEXT       = "#eaeaea"
TEXT_DIM   = "#8892a4"
INPUT_BG   = "#0d1b2a"
FONT_MONO  = ("Consolas", 10)
FONT_LABEL = ("Segoe UI", 10)
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_HEAD  = ("Segoe UI", 10, "bold")


# ─────────────────────────────────────────────
#  Main Application
# ─────────────────────────────────────────────

class SolverApp(tk.Tk):
    def __init__(self, solver: Solver, json_paths: list[str]):
        super().__init__()
        self.solver     = solver
        self.json_paths = list(json_paths)  # initial files

        self.title("Mesh Network Solver")
        self.configure(bg=DARK_BG)
        self.resizable(True, True)
        self.minsize(960, 620)

        # file path -> BoolVar (enabled?)
        self.file_enabled: dict[str, tk.BooleanVar] = {}

        # var_name -> (BoolVar enabled, StringVar value)
        self.const_vars: dict[str, tuple] = {}

        self.sweep_var   = tk.StringVar()
        self.y_var       = tk.StringVar()
        self.sweep_from  = tk.StringVar(value="0.1")
        self.sweep_to    = tk.StringVar(value="10")
        self.sweep_steps = tk.StringVar(value="100")
        self.status_var  = tk.StringVar(value="Ready.")

        # References we need to rebuild
        self._const_list_frame = None
        self._sweep_combo      = None
        self._y_combo          = None

        self._build_ui()

    # ─── UI ──────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_left_panel()
        self._build_right_panel()

    def _build_left_panel(self):
        self._left_outer = tk.Frame(self, bg=PANEL_BG)
        self._left_outer.grid(row=0, column=0, sticky="nsew")
        self._left_outer.rowconfigure(1, weight=1)
        self._left_outer.columnconfigure(0, weight=1)

        # Title
        tk.Label(self._left_outer, text="MESH SOLVER", font=FONT_TITLE,
                 bg=PANEL_BG, fg=HIGHLIGHT, padx=18, pady=14).grid(
            row=0, column=0, sticky="w")

        # Scrollable inner area
        self._scroll_canvas = tk.Canvas(
            self._left_outer, bg=PANEL_BG, highlightthickness=0, width=320)
        self._scrollbar = ttk.Scrollbar(
            self._left_outer, orient="vertical", command=self._scroll_canvas.yview)
        self._inner = tk.Frame(self._scroll_canvas, bg=PANEL_BG)

        self._inner.bind("<Configure>", lambda e: self._scroll_canvas.configure(
            scrollregion=self._scroll_canvas.bbox("all")))
        self._scroll_canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._scroll_canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scroll_canvas.grid(row=1, column=0, sticky="nsew")
        self._scrollbar.grid(row=1, column=1, sticky="ns")

        def _on_wheel(event):
            self._scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self._scroll_canvas.bind("<MouseWheel>", _on_wheel)
        self._inner.bind("<MouseWheel>", _on_wheel)

        self._build_inner_content()

        # Bottom bar (always visible)
        bottom = tk.Frame(self._left_outer, bg=PANEL_BG, padx=18, pady=10)
        bottom.grid(row=2, column=0, columnspan=2, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        tk.Button(bottom, text="▶  PLOT", font=("Segoe UI", 11, "bold"),
                  bg=HIGHLIGHT, fg="white", activebackground="#c73652",
                  activeforeground="white", relief="flat",
                  padx=16, pady=8, cursor="hand2",
                  command=self._on_plot).grid(row=0, column=0, sticky="ew")

        tk.Label(bottom, textvariable=self.status_var, font=FONT_SMALL,
                 bg=PANEL_BG, fg=TEXT_DIM, wraplength=260,
                 justify="left").grid(row=1, column=0, sticky="w", pady=(6, 0))

    def _build_inner_content(self):
        """Build (or rebuild) the scrollable section inside the left panel."""
        for widget in self._inner.winfo_children():
            widget.destroy()
        self.const_vars.clear()

        # ── JSON Files section ────────────────
        self._section_label(self._inner, "Formula Files")
        tk.Label(self._inner,
                 text="Toggle files to enable/disable their formulas.",
                 font=FONT_SMALL, bg=PANEL_BG, fg=TEXT_DIM, padx=18).pack(anchor="w")

        files_frame = tk.Frame(self._inner, bg=PANEL_BG, padx=18)
        files_frame.pack(fill="x", pady=(6, 0))

        for path in self.json_paths:
            if path not in self.file_enabled:
                self.file_enabled[path] = tk.BooleanVar(value=True)

            row = tk.Frame(files_frame, bg=PANEL_BG)
            row.pack(fill="x", pady=3)

            var = self.file_enabled[path]
            short = path.replace("\\", "/").split("/")[-1]

            cb = tk.Checkbutton(
                row, variable=var,
                text=short, font=FONT_MONO, anchor="w",
                bg=PANEL_BG, fg=SUCCESS if var.get() else TEXT_DIM,
                activebackground=PANEL_BG, activeforeground=HIGHLIGHT,
                selectcolor=ACCENT, cursor="hand2",
                command=lambda p=path, v=var, r=row: self._on_file_toggle(p, v, r))
            cb.pack(side="left", fill="x", expand=True)

            tk.Button(row, text="✕", font=FONT_SMALL,
                      bg=PANEL_BG, fg=TEXT_DIM,
                      activebackground=HIGHLIGHT, activeforeground="white",
                      relief="flat", cursor="hand2", padx=4,
                      command=lambda p=path: self._remove_file(p)).pack(side="right")

        # Add file button
        add_frame = tk.Frame(files_frame, bg=PANEL_BG)
        add_frame.pack(fill="x", pady=(6, 0))
        tk.Button(add_frame, text="+ Add JSON file", font=FONT_SMALL,
                  bg=ACCENT, fg=TEXT, activebackground=HIGHLIGHT,
                  activeforeground="white", relief="flat", padx=8, pady=4,
                  cursor="hand2", command=self._add_file).pack(side="left")

        self._separator(self._inner)

        # ── Constants list ────────────────────
        self._section_label(self._inner, "Constants")
        tk.Label(self._inner, text="✓ check a variable  |  enter its value",
                 font=FONT_SMALL, bg=PANEL_BG, fg=TEXT_DIM, padx=18).pack(anchor="w")

        self._const_list_frame = tk.Frame(self._inner, bg=PANEL_BG, padx=18)
        self._const_list_frame.pack(fill="x", pady=(6, 0))
        self._rebuild_const_list()

        self._separator(self._inner)

        # ── Sweep (X axis) ────────────────────
        self._section_label(self._inner, "Sweep — X Axis")
        sf = tk.Frame(self._inner, bg=PANEL_BG, padx=18)
        sf.pack(fill="x", pady=(4, 0))

        all_vars = self.solver.all_variables()
        if not self.sweep_var.get() or self.sweep_var.get() not in all_vars:
            self.sweep_var.set("lambda_m" if "lambda_m" in all_vars else (all_vars[0] if all_vars else ""))

        self._sweep_combo = ttk.Combobox(sf, textvariable=self.sweep_var,
                                         values=all_vars, state="readonly",
                                         font=FONT_MONO, width=26)
        self._sweep_combo.pack(fill="x", pady=(0, 8))

        rf = tk.Frame(sf, bg=PANEL_BG)
        rf.pack(fill="x")
        for col, (lbl, var) in enumerate([("From",  self.sweep_from),
                                           ("To",    self.sweep_to),
                                           ("Steps", self.sweep_steps)]):
            tk.Label(rf, text=lbl, font=FONT_LABEL, bg=PANEL_BG, fg=TEXT).grid(
                row=0, column=col * 2, sticky="w", padx=(0, 4))
            tk.Entry(rf, textvariable=var, font=FONT_MONO,
                     bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
                     relief="flat", width=7,
                     highlightthickness=1, highlightbackground=ACCENT,
                     highlightcolor=HIGHLIGHT).grid(
                row=0, column=col * 2 + 1, sticky="ew", padx=(0, 12))

        self._separator(self._inner)

        # ── Y axis ────────────────────────────
        self._section_label(self._inner, "Y Axis")
        yf = tk.Frame(self._inner, bg=PANEL_BG, padx=18)
        yf.pack(fill="x", pady=(4, 16))

        all_outputs = self.solver.all_outputs()
        if not self.y_var.get() or self.y_var.get() not in all_outputs:
            self.y_var.set("delta_Tx" if "delta_Tx" in all_outputs else (all_outputs[0] if all_outputs else ""))

        self._y_combo = ttk.Combobox(yf, textvariable=self.y_var,
                                     values=all_outputs, state="readonly",
                                     font=FONT_MONO, width=26)
        self._y_combo.pack(fill="x")

    def _rebuild_const_list(self):
        """Rebuild just the constants list when variables change."""
        if self._const_list_frame is None:
            return

        # Remember current values so they survive a rebuild
        previous = {name: (en.get(), val.get())
                    for name, (en, val) in self.const_vars.items()}

        for w in self._const_list_frame.winfo_children():
            w.destroy()
        self.const_vars.clear()

        for var_name in self.solver.all_variables():
            prev_en, prev_val = previous.get(var_name, (False, ""))

            row = tk.Frame(self._const_list_frame, bg=PANEL_BG)
            row.pack(fill="x", pady=2)

            enabled = tk.BooleanVar(value=prev_en)
            value   = tk.StringVar(value=prev_val)

            cb = tk.Checkbutton(row, variable=enabled, text=var_name,
                                font=FONT_MONO, width=22, anchor="w",
                                bg=PANEL_BG, fg=TEXT,
                                activebackground=PANEL_BG, activeforeground=HIGHLIGHT,
                                selectcolor=ACCENT, cursor="hand2")
            cb.pack(side="left")

            entry = tk.Entry(row, textvariable=value, font=FONT_MONO,
                             bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
                             relief="flat", width=11,
                             highlightthickness=1, highlightbackground=ACCENT,
                             highlightcolor=HIGHLIGHT)
            entry.pack(side="left", padx=(4, 0))

            def _toggle(e=enabled, ent=entry):
                ent.config(highlightbackground=HIGHLIGHT if e.get() else ACCENT)
            enabled.trace_add("write", lambda *_, fn=_toggle: fn())
            _toggle()  # set initial state

            self.const_vars[var_name] = (enabled, value)

    def _refresh_after_toggle(self):
        """Update combo boxes and constants list after files change."""
        all_vars    = self.solver.all_variables()
        all_outputs = self.solver.all_outputs()

        if self._sweep_combo:
            self._sweep_combo.config(values=all_vars)
            if self.sweep_var.get() not in all_vars:
                self.sweep_var.set(all_vars[0] if all_vars else "")

        if self._y_combo:
            self._y_combo.config(values=all_outputs)
            if self.y_var.get() not in all_outputs:
                self.y_var.set(all_outputs[0] if all_outputs else "")

        self._rebuild_const_list()

        # Force scroll canvas to recalculate
        self._inner.update_idletasks()
        self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))

    def _on_file_toggle(self, path, var, row_frame):
        enabled = var.get()
        self.solver.set_file_enabled(path, enabled)
        # Update checkbox text colour
        for child in row_frame.winfo_children():
            if isinstance(child, tk.Checkbutton):
                child.config(fg=SUCCESS if enabled else TEXT_DIM)
        self._refresh_after_toggle()
        name = path.replace("\\", "/").split("/")[-1]
        self.status_var.set(f"{'Enabled' if enabled else 'Disabled'}: {name}")

    def _add_file(self):
        path = filedialog.askopenfilename(
            title="Add formula JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not path or path in self.json_paths:
            return
        try:
            self.solver.load_file(path)
            self.json_paths.append(path)
            self.file_enabled[path] = tk.BooleanVar(value=True)
            # Rebuild the whole inner content so the new file appears in the list
            self._build_inner_content()
            self.status_var.set(f"Loaded: {path.split('/')[-1]}")
        except Exception as e:
            messagebox.showerror("Load error", str(e))

    def _remove_file(self, path):
        self.solver.set_file_enabled(path, False)
        del self.solver._sources[path]
        self.json_paths.remove(path)
        if path in self.file_enabled:
            del self.file_enabled[path]
        self._build_inner_content()
        self.status_var.set(f"Removed: {path.split('/')[-1]}")

    def _build_right_panel(self):
        right = tk.Frame(self, bg=DARK_BG, padx=12, pady=12)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        self.fig, self.ax = plt.subplots(figsize=(7, 5))
        self.fig.patch.set_facecolor(DARK_BG)
        self.ax.set_facecolor(INPUT_BG)
        self._style_axes()

        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    # ─── Helpers ─────────────────────────────

    def _section_label(self, parent, text):
        tk.Label(parent, text=text, font=FONT_HEAD,
                 bg=PANEL_BG, fg=TEXT_DIM, padx=18).pack(anchor="w", pady=(10, 2))

    def _separator(self, parent):
        tk.Frame(parent, bg=ACCENT, height=1).pack(fill="x", padx=18, pady=10)

    def _style_axes(self):
        self.ax.tick_params(colors=TEXT_DIM, labelsize=9)
        self.ax.xaxis.label.set_color(TEXT)
        self.ax.yaxis.label.set_color(TEXT)
        self.ax.title.set_color(TEXT)
        for spine in self.ax.spines.values():
            spine.set_edgecolor(ACCENT)
        self.ax.grid(True, color=ACCENT, alpha=0.4, linestyle="--", linewidth=0.6)

    # ─── Plot ─────────────────────────────────

    def _on_plot(self):
        try:
            sweep_key  = self.sweep_var.get()
            y_key      = self.y_var.get()
            sweep_from = float(self.sweep_from.get())
            sweep_to   = float(self.sweep_to.get())
            steps      = int(self.sweep_steps.get())
        except ValueError:
            messagebox.showerror("Input error", "Invalid sweep range or steps.")
            return

        if not sweep_key or not y_key:
            messagebox.showerror("Input error", "Please select X and Y axis variables.")
            return

        base_known = {}
        for var_name, (enabled, value) in self.const_vars.items():
            if not enabled.get() or var_name == sweep_key:
                continue
            raw = value.get().strip()
            if not raw:
                messagebox.showwarning("Missing value",
                    f"'{var_name}' is checked but has no value entered.")
                return
            try:
                base_known[var_name] = float(raw)
            except ValueError:
                messagebox.showerror("Input error",
                    f"Invalid number for '{var_name}': {raw}")
                return

        sweep_values = np.linspace(sweep_from, sweep_to, steps)
        y_results = []
        failed = 0

        for val in sweep_values:
            known = {**base_known, sweep_key: val}
            results = self.solver.solve(known)
            y = results.get(y_key)
            y_results.append(y)
            if y is None:
                failed += 1

        xs = [x for x, y in zip(sweep_values, y_results) if y is not None]
        ys = [y for y in y_results if y is not None]

        if not ys:
            missing = self.solver.get_missing(base_known, [y_key])
            self.status_var.set(
                f"Cannot compute '{y_key}'.\n"
                f"Missing: {', '.join(missing) or 'unknown'}")
            return

        self.ax.clear()
        self._style_axes()
        self.ax.plot(xs, ys, color=HIGHLIGHT, linewidth=2)
        self.ax.set_xlabel(sweep_key)
        self.ax.set_ylabel(y_key)
        self.ax.set_title(f"{y_key}  vs  {sweep_key}")
        self.fig.tight_layout()
        self.canvas.draw()

        status = f"Plotted {len(ys)} points."
        if failed:
            status += f"  ({failed} skipped — undefined)"
        self.status_var.set(status)
