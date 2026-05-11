"""
Network test graph explorer — GUI version.

Usage:
    python plot_tests_gui.py                     # opens file dialog to pick DB
    python plot_tests_gui.py --db path/to/my.db  # load DB directly

Requirements:  pip install matplotlib pandas
tkinter ships with standard Python.
"""

import argparse
import sqlite3
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ── constants ─────────────────────────────────────────────────────────────────
METRICS = [
    ("throughput",        "Throughput (Kbps)"),
    ("rtt_ms",            "RTT (ms)"),
    ("jitter_ms",         "Jitter (ms)"),
    ("packet_loss_iperf", "Packet loss — iperf (%)"),
    ("packet_loss_ping",  "Packet loss — ping (%)"),
    ("duration",          "Duration (s)"),
]

X_AXES = [
    ("packet_size",       "Packet size (bytes)"),
    ("number_of_packets", "Number of packets"),
    ("distance",          "Distance (m)"),
    ("environment",       "Environment"),
]

COLORS = ["#378add", "#D85A30", "#1D9E75", "#7F77DD", "#BA7517", "#5DCAA5", "#F09995"]


# ── data loading ──────────────────────────────────────────────────────────────
def load_data(db_path: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        """
        SELECT t.test_name, t.environment, t.distance,
               t.packet_size, t.number_of_packets,
               a.throughput, a.jitter_ms,
               a.packet_loss_iperf, a.packet_loss_ping,
               a.rtt_ms, a.duration
        FROM averages a
        JOIN tests t ON a.test_id = t.id
        """,
        conn,
    )
    conn.close()
    return df


# ── main application ──────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self.df = df
        self._chart_ready = False   # guard: skip refresh until chart exists

        self.title("Network test explorer")
        self.configure(bg="#f5f5f5")
        self.minsize(1150, 680)

        # ── tk variables ──────────────────────────────────────────────────────
        self.check_vars: dict[tuple, tk.BooleanVar] = {}
        self.dist_min_var  = tk.DoubleVar()
        self.dist_max_var  = tk.DoubleVar()
        self.y_var         = tk.StringVar(value=METRICS[0][0])
        self.x_var         = tk.StringVar(value=X_AXES[0][0])
        self.split_env_var = tk.BooleanVar(value=False)

        # Build left panel first (sets dist vars), then chart
        self._build_left_panel()
        self._build_right_panel()

        # Chart exists now — safe to draw
        self._chart_ready = True
        self._refresh_chart()

    # ── left panel ────────────────────────────────────────────────────────────
    def _build_left_panel(self):
        container = tk.Frame(self, bg="#f0f0f0", width=270)
        container.pack(side=tk.LEFT, fill=tk.Y)
        container.pack_propagate(False)

        self._left_canvas = tk.Canvas(container, bg="#f0f0f0", highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=self._left_canvas.yview)
        self._left_canvas.configure(yscrollcommand=sb.set)

        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(self._left_canvas, bg="#f0f0f0")
        self._left_canvas.create_window((0, 0), window=inner, anchor="nw", tags="inner")

        inner.bind("<Configure>", lambda e: self._left_canvas.configure(
            scrollregion=self._left_canvas.bbox("all")
        ))
        self._left_canvas.bind("<Configure>", lambda e: self._left_canvas.itemconfig(
            "inner", width=e.width
        ))

        # Mouse-wheel: Linux Button-4/5, Windows/macOS MouseWheel
        def _on_wheel(event):
            if event.num == 4:
                self._left_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self._left_canvas.yview_scroll(1, "units")
            else:
                self._left_canvas.yview_scroll(-1 * int(event.delta / 120), "units")

        self._left_canvas.bind("<MouseWheel>", _on_wheel)
        self._left_canvas.bind("<Button-4>",   _on_wheel)
        self._left_canvas.bind("<Button-5>",   _on_wheel)

        self._populate_left(inner)

    def _section_label(self, parent: tk.Frame, title: str):
        tk.Frame(parent, bg="#d8d8d8", height=1).pack(fill=tk.X, pady=(10, 0))
        tk.Label(
            parent, text=title.upper(), bg="#f0f0f0",
            fg="#777777", font=("Helvetica", 9, "bold"),
            anchor="w", padx=10, pady=5,
        ).pack(fill=tk.X)

    def _populate_left(self, parent: tk.Frame):
        tk.Label(
            parent, text="Network test explorer",
            bg="#f0f0f0", font=("Helvetica", 12, "bold"),
            anchor="w", padx=10, pady=12,
        ).pack(fill=tk.X)

        # ── Checkboxes: packet_size, number_of_packets, environment ──────────
        for col, label in [
            ("packet_size",       "Packet size (bytes)"),
            ("number_of_packets", "Number of packets"),
            ("environment",       "Environment"),
        ]:
            self._section_label(parent, label)
            f = tk.Frame(parent, bg="#f0f0f0")
            f.pack(fill=tk.X, padx=10, pady=(0, 4))

            # "all / none" toggle
            def make_toggle(c=col):
                def toggle():
                    vals = [v for (cc, _), v in self.check_vars.items() if cc == c]
                    new_state = not all(v.get() for v in vals)
                    for v in vals:
                        v.set(new_state)
                    self._refresh_chart()
                return toggle

            tk.Button(
                f, text="all / none", font=("Helvetica", 8),
                bg="#f0f0f0", relief="flat", cursor="hand2",
                fg="#555555", activeforeground="#000000",
                command=make_toggle(),
            ).pack(anchor="w")

            for v in sorted(self.df[col].unique()):
                var  = tk.BooleanVar(value=True)
                self.check_vars[(col, v)] = var
                text = str(int(v)) if col != "environment" else str(v)
                tk.Checkbutton(
                    f, text=text, variable=var, bg="#f0f0f0",
                    activebackground="#f0f0f0", anchor="w",
                    font=("Helvetica", 10), command=self._refresh_chart,
                ).pack(fill=tk.X)

        # ── Distance sliders ──────────────────────────────────────────────────
        dist_vals = self.df["distance"].dropna()
        dmin, dmax = float(dist_vals.min()), float(dist_vals.max())
        self.dist_min_var.set(dmin)
        self.dist_max_var.set(dmax)

        self._section_label(parent, "Distance (m)")
        df_frame = tk.Frame(parent, bg="#f0f0f0")
        df_frame.pack(fill=tk.X, padx=10, pady=(0, 4))

        for lbl_text, var, lbl_attr, default in [
            ("Min", self.dist_min_var, "_lbl_dist_min", dmin),
            ("Max", self.dist_max_var, "_lbl_dist_max", dmax),
        ]:
            row = tk.Frame(df_frame, bg="#f0f0f0")
            row.pack(fill=tk.X, pady=(4, 0))
            tk.Label(row, text=lbl_text, width=4, anchor="w",
                     bg="#f0f0f0", font=("Helvetica", 10)).pack(side=tk.LEFT)
            lbl = tk.Label(row, text=f"{default:.1f}", width=8, anchor="e",
                           bg="#f0f0f0", font=("Helvetica", 10, "bold"))
            lbl.pack(side=tk.RIGHT)
            setattr(self, lbl_attr, lbl)

            sl = ttk.Scale(
                df_frame, from_=dmin, to=dmax, variable=var,
                orient="horizontal", command=self._on_dist_change,
            )
            sl.set(default)
            sl.pack(fill=tk.X, pady=(0, 2))

        # ── Y axis ────────────────────────────────────────────────────────────
        self._section_label(parent, "Y axis — metric")
        yf = tk.Frame(parent, bg="#f0f0f0")
        yf.pack(fill=tk.X, padx=10, pady=(0, 4))
        for col, label in METRICS:
            tk.Radiobutton(
                yf, text=label, variable=self.y_var, value=col,
                bg="#f0f0f0", activebackground="#f0f0f0", anchor="w",
                font=("Helvetica", 10), command=self._refresh_chart,
            ).pack(fill=tk.X)

        # ── X axis ────────────────────────────────────────────────────────────
        self._section_label(parent, "X axis — group by")
        xf = tk.Frame(parent, bg="#f0f0f0")
        xf.pack(fill=tk.X, padx=10, pady=(0, 4))
        for col, label in X_AXES:
            tk.Radiobutton(
                xf, text=label, variable=self.x_var, value=col,
                bg="#f0f0f0", activebackground="#f0f0f0", anchor="w",
                font=("Helvetica", 10), command=self._refresh_chart,
            ).pack(fill=tk.X)

        # ── Options ───────────────────────────────────────────────────────────
        self._section_label(parent, "Options")
        of = tk.Frame(parent, bg="#f0f0f0")
        of.pack(fill=tk.X, padx=10, pady=(0, 20))
        tk.Checkbutton(
            of, text="Split lines by environment", variable=self.split_env_var,
            bg="#f0f0f0", activebackground="#f0f0f0", anchor="w",
            font=("Helvetica", 10), command=self._refresh_chart,
        ).pack(fill=tk.X)

    # ── right panel ───────────────────────────────────────────────────────────
    def _build_right_panel(self):
        right = tk.Frame(self, bg="#ffffff")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        self.fig.patch.set_facecolor("#ffffff")

        self._canvas_widget = FigureCanvasTkAgg(self.fig, master=right)
        self._canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self._status_var = tk.StringVar(value="")
        tk.Label(
            right, textvariable=self._status_var,
            bg="#ffffff", fg="#999999", font=("Helvetica", 10),
            anchor="w", padx=16,
        ).pack(fill=tk.X, pady=(0, 6))

    # ── distance slider handler ───────────────────────────────────────────────
    def _on_dist_change(self, _=None):
        lo = self.dist_min_var.get()
        hi = self.dist_max_var.get()
        if lo > hi:
            self.dist_min_var.set(hi)
            lo = hi
        self._lbl_dist_min.config(text=f"{lo:.1f}")
        self._lbl_dist_max.config(text=f"{hi:.1f}")
        self._refresh_chart()

    # ── filtering ─────────────────────────────────────────────────────────────
    def _get_filtered(self) -> pd.DataFrame:
        df = self.df.copy()
        for col in ("packet_size", "number_of_packets", "environment"):
            allowed = [v for (c, v), var in self.check_vars.items() if c == col and var.get()]
            if not allowed:
                return df.iloc[0:0]
            df = df[df[col].isin(allowed)]
        lo, hi = self.dist_min_var.get(), self.dist_max_var.get()
        return df[(df["distance"] >= lo) & (df["distance"] <= hi)]

    # ── chart refresh ─────────────────────────────────────────────────────────
    def _refresh_chart(self, _=None):
        if not self._chart_ready:
            return

        df      = self._get_filtered()
        x_col   = self.x_var.get()
        y_col   = self.y_var.get()
        x_label = next(lbl for col, lbl in X_AXES  if col == x_col)
        y_label = next(lbl for col, lbl in METRICS if col == y_col)

        # Convert throughput from bits/s → Kbps for display
        if y_col == "throughput" and not df.empty:
            df = df.copy()
            df["throughput"] = df["throughput"] / 1000
            y_label = "Throughput (Kbps)"
        split_env = self.split_env_var.get()

        self.ax.clear()
        self.ax.set_facecolor("#ffffff")
        self.ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.55, zorder=0)
        self.ax.spines[["top", "right"]].set_visible(False)

        if df.empty or y_col not in df.columns or df[y_col].isna().all():
            self.ax.text(
                0.5, 0.5, "No data matches current filters",
                transform=self.ax.transAxes, ha="center", va="center",
                fontsize=13, color="#bbbbbb",
            )
            self._status_var.set("0 rows match current filters")
            self._canvas_widget.draw()
            return

        is_numeric_x = pd.api.types.is_numeric_dtype(df[x_col])

        if is_numeric_x:
            # Determine which column to use for splitting into separate lines.
            # If the X axis is packet_size  → split by number_of_packets (and optionally env)
            # If the X axis is number_of_packets → split by packet_size (and optionally env)
            # Otherwise (distance) → split by environment if requested, else one line
            if x_col == "packet_size":
                line_col = "number_of_packets"
                line_label = "packets"
            elif x_col == "number_of_packets":
                line_col = "packet_size"
                line_label = "bytes"
            else:
                line_col = "environment" if split_env else None
                line_label = "env"

            if line_col is not None:
                line_vals = sorted(df[line_col].unique())
            else:
                line_vals = [None]

            # Secondary split by environment on top (only when not already splitting by env)
            if split_env and line_col != "environment":
                env_vals = sorted(df["environment"].unique())
            else:
                env_vals = [None]

            color_idx = 0
            for env in env_vals:
                edf = df[df["environment"] == env] if env is not None else df
                for lv in line_vals:
                    gdf = edf[edf[line_col] == lv] if lv is not None else edf
                    if gdf.empty:
                        continue
                    agg = (
                        gdf.groupby(x_col)[y_col]
                        .mean()
                        .reset_index()
                        .sort_values(x_col)
                    )
                    color = COLORS[color_idx % len(COLORS)]
                    color_idx += 1

                    parts = []
                    if lv is not None:
                        parts.append(f"{line_label}={int(lv) if line_col != 'environment' else lv}")
                    if env is not None:
                        parts.append(str(env))
                    label = ", ".join(parts) if parts else y_label

                    self.ax.plot(
                        agg[x_col], agg[y_col],
                        marker="o", label=label, color=color,
                        linewidth=2, markersize=5, zorder=3,
                    )

            self.ax.set_xlabel(x_label, fontsize=12)
            self.ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
            self.ax.legend(fontsize=9, framealpha=0.85, ncol=max(1, color_idx // 12))

        else:
            # Categorical X (environment) → grouped bars by packet_size
            cats      = sorted(df[x_col].unique())
            line_col  = "packet_size"
            line_vals = sorted(df[line_col].unique())
            n_groups  = len(line_vals)
            width     = 0.7 / max(n_groups, 1)
            x_pos     = np.arange(len(cats))

            for i, lv in enumerate(line_vals):
                gdf   = df[df[line_col] == lv]
                means = [gdf[gdf[x_col] == c][y_col].mean() for c in cats]
                offset = (i - n_groups / 2 + 0.5) * width
                self.ax.bar(
                    x_pos + offset, means, width=width * 0.9,
                    label=f"{int(lv)} bytes",
                    color=COLORS[i % len(COLORS)], alpha=0.85, zorder=3,
                )

            self.ax.set_xticks(x_pos)
            self.ax.set_xticklabels([str(c) for c in cats], fontsize=11)
            self.ax.set_xlabel(x_label, fontsize=12)
            self.ax.legend(fontsize=9, framealpha=0.85)

        self.ax.set_ylabel(y_label, fontsize=12)
        self.ax.set_title(f"{y_label}  vs  {x_label}", fontsize=13, pad=12)
        self.ax.text(
            0.99, 0.02, f"n = {len(df)} rows",
            transform=self.ax.transAxes, ha="right", va="bottom",
            fontsize=9, color="#aaaaaa",
        )

        self.fig.tight_layout()
        self._canvas_widget.draw()
        self._status_var.set(f"{len(df)} rows match current filters")


# ── entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Network test GUI explorer")
    parser.add_argument("--db", default=None, help="Path to SQLite database")
    args = parser.parse_args()

    db_path = args.db
    if db_path is None:
        root = tk.Tk()
        root.withdraw()
        db_path = filedialog.askopenfilename(
            title="Select your SQLite database",
            filetypes=[("SQLite databases", "*.db *.sqlite *.sqlite3"), ("All files", "*.*")],
        )
        root.destroy()
        if not db_path:
            print("No database selected.")
            sys.exit(0)

    try:
        df = load_data(db_path)
    except Exception as e:
        messagebox.showerror("Load error", str(e))
        sys.exit(1)

    if df.empty:
        messagebox.showwarning("Empty database", "No data found in averages/tests tables.")
        sys.exit(0)

    app = App(df)
    app.mainloop()


if __name__ == "__main__":
    main()