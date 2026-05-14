"""
Network test graph explorer — GUI version.

Usage:
    python plot_tests_gui.py
    python plot_tests_gui.py --db path/to/my.db

Requirements:  pip install matplotlib pandas
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

# Columns that get checkbox filters (in display order)
CHECKBOX_COLS = [
    ("packet_size",       "Packet size (bytes)"),
    ("number_of_packets", "Number of packets"),
    ("distance",          "Distance (m)"),
    ("environment",       "Environment"),
    ("test_name",         "Test name"),
]

COLORS = ["#378add", "#D85A30", "#1D9E75", "#7F77DD", "#BA7517", "#5DCAA5", "#F09995"]


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


class App(tk.Tk):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self.df = df
        self._chart_ready = False

        self.title("Network test explorer")
        self.configure(bg="#f5f5f5")
        self.minsize(1150, 680)

        self.check_vars: dict[tuple, tk.BooleanVar] = {}
        self.y_var         = tk.StringVar(value=METRICS[0][0])
        self.x_var         = tk.StringVar(value=X_AXES[0][0])
        self.split_env_var = tk.BooleanVar(value=False)

        self._build_left_panel()
        self._build_right_panel()

        self._chart_ready = True
        self._refresh_chart()

    # ── left panel ────────────────────────────────────────────────────────────
    def _build_left_panel(self):
        container = tk.Frame(self, bg="#f0f0f0", width=270)
        container.pack(side=tk.LEFT, fill=tk.Y)
        container.pack_propagate(False)

        self._lc = tk.Canvas(container, bg="#f0f0f0", highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=self._lc.yview)
        self._lc.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._lc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(self._lc, bg="#f0f0f0")
        self._lc.create_window((0, 0), window=inner, anchor="nw", tags="inner")
        inner.bind("<Configure>", lambda e: self._lc.configure(scrollregion=self._lc.bbox("all")))
        self._lc.bind("<Configure>", lambda e: self._lc.itemconfig("inner", width=e.width))

        def _wheel(e):
            if e.num == 4:   self._lc.yview_scroll(-1, "units")
            elif e.num == 5: self._lc.yview_scroll(1,  "units")
            else:            self._lc.yview_scroll(-1 * int(e.delta / 120), "units")

        self._lc.bind("<MouseWheel>", _wheel)
        self._lc.bind("<Button-4>",   _wheel)
        self._lc.bind("<Button-5>",   _wheel)

        self._populate_left(inner)

    def _sep(self, parent, title):
        tk.Frame(parent, bg="#d8d8d8", height=1).pack(fill=tk.X, pady=(10, 0))
        tk.Label(parent, text=title.upper(), bg="#f0f0f0", fg="#777777",
                 font=("Helvetica", 9, "bold"), anchor="w", padx=10, pady=5).pack(fill=tk.X)

    def _checkbox_section(self, parent, col, label):
        self._sep(parent, label)
        f = tk.Frame(parent, bg="#f0f0f0")
        f.pack(fill=tk.X, padx=10, pady=(0, 4))

        def make_toggle(c=col):
            def toggle():
                vals = [v for (cc, _), v in self.check_vars.items() if cc == c]
                s = not all(v.get() for v in vals)
                for v in vals: v.set(s)
                self._refresh_chart()
            return toggle

        tk.Button(f, text="all / none", font=("Helvetica", 8), bg="#f0f0f0",
                  relief="flat", cursor="hand2", fg="#555555",
                  command=make_toggle()).pack(anchor="w")

        numeric = col not in ("environment", "test_name")
        for v in sorted(self.df[col].unique()):
            var  = tk.BooleanVar(value=True)
            self.check_vars[(col, v)] = var
            text = str(int(v)) if numeric else str(v)
            tk.Checkbutton(f, text=text, variable=var, bg="#f0f0f0",
                           activebackground="#f0f0f0", anchor="w",
                           font=("Helvetica", 10),
                           command=self._refresh_chart).pack(fill=tk.X)

    def _populate_left(self, parent):
        tk.Label(parent, text="Network test explorer", bg="#f0f0f0",
                 font=("Helvetica", 12, "bold"), anchor="w", padx=10, pady=12).pack(fill=tk.X)

        for col, label in CHECKBOX_COLS:
            self._checkbox_section(parent, col, label)

        # Y axis
        self._sep(parent, "Y axis — metric")
        yf = tk.Frame(parent, bg="#f0f0f0")
        yf.pack(fill=tk.X, padx=10, pady=(0, 4))
        for col, label in METRICS:
            tk.Radiobutton(yf, text=label, variable=self.y_var, value=col,
                           bg="#f0f0f0", activebackground="#f0f0f0", anchor="w",
                           font=("Helvetica", 10), command=self._refresh_chart).pack(fill=tk.X)

        # X axis
        self._sep(parent, "X axis — group by")
        xf = tk.Frame(parent, bg="#f0f0f0")
        xf.pack(fill=tk.X, padx=10, pady=(0, 4))
        for col, label in X_AXES:
            tk.Radiobutton(xf, text=label, variable=self.x_var, value=col,
                           bg="#f0f0f0", activebackground="#f0f0f0", anchor="w",
                           font=("Helvetica", 10), command=self._refresh_chart).pack(fill=tk.X)

        # Options
        self._sep(parent, "Options")
        of = tk.Frame(parent, bg="#f0f0f0")
        of.pack(fill=tk.X, padx=10, pady=(0, 20))
        tk.Checkbutton(of, text="Split lines by environment",
                       variable=self.split_env_var, bg="#f0f0f0",
                       activebackground="#f0f0f0", anchor="w",
                       font=("Helvetica", 10), command=self._refresh_chart).pack(fill=tk.X)

    # ── right panel ───────────────────────────────────────────────────────────
    def _build_right_panel(self):
        right = tk.Frame(self, bg="#ffffff")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        self.fig.patch.set_facecolor("#ffffff")

        self._cw = FigureCanvasTkAgg(self.fig, master=right)
        self._cw.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self._status_var = tk.StringVar(value="")
        tk.Label(right, textvariable=self._status_var, bg="#ffffff", fg="#999999",
                 font=("Helvetica", 10), anchor="w", padx=16).pack(fill=tk.X, pady=(0, 6))

    # ── filtering ─────────────────────────────────────────────────────────────
    def _get_filtered(self) -> pd.DataFrame:
        df = self.df.copy()
        for col, _ in CHECKBOX_COLS:
            allowed = [v for (c, v), var in self.check_vars.items() if c == col and var.get()]
            if not allowed:
                return df.iloc[0:0]
            df = df[df[col].isin(allowed)]
        return df

    # ── chart ─────────────────────────────────────────────────────────────────
    def _refresh_chart(self, _=None):
        if not self._chart_ready:
            return

        df      = self._get_filtered()
        x_col   = self.x_var.get()
        y_col   = self.y_var.get()
        x_label = next(lbl for col, lbl in X_AXES  if col == x_col)
        y_label = next(lbl for col, lbl in METRICS if col == y_col)

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
            self.ax.text(0.5, 0.5, "No data matches current filters",
                         transform=self.ax.transAxes, ha="center", va="center",
                         fontsize=13, color="#bbbbbb")
            self._status_var.set("0 rows match current filters")
            self._cw.draw()
            return

        is_numeric_x = pd.api.types.is_numeric_dtype(df[x_col])

        if is_numeric_x:
            # Pick the "other" column to split into lines
            if x_col == "packet_size":
                line_col, line_fmt = "number_of_packets", lambda v: f"{int(v)} pkts"
            elif x_col == "number_of_packets":
                line_col, line_fmt = "packet_size",       lambda v: f"{int(v)} B"
            elif x_col == "distance":
                line_col, line_fmt = "packet_size",       lambda v: f"{int(v)} B"
            else:
                line_col, line_fmt = "packet_size",       lambda v: f"{int(v)} B"

            env_vals  = sorted(df["environment"].unique()) if split_env else [None]
            line_vals = sorted(df[line_col].unique())
            test_vals = sorted(df["test_name"].unique())

            color_idx = 0
            for env in env_vals:
                edf = df[df["environment"] == env] if env is not None else df
                for lv in line_vals:
                    gdf = edf[edf[line_col] == lv]
                    if gdf.empty:
                        continue
                    # One line per test_name within each group
                    for tn in test_vals:
                        tdf = gdf[gdf["test_name"] == tn]
                        if tdf.empty:
                            continue
                        agg = (tdf.groupby(x_col)[y_col].mean()
                               .reset_index().sort_values(x_col))
                        color = COLORS[color_idx % len(COLORS)]
                        color_idx += 1
                        parts = [line_fmt(lv), tn]
                        if env is not None:
                            parts.append(str(env))
                        self.ax.plot(agg[x_col], agg[y_col], marker="o",
                                     label=", ".join(parts), color=color,
                                     linewidth=2, markersize=5, zorder=3)

            self.ax.set_xlabel(x_label, fontsize=12)
            self.ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
            self.ax.legend(fontsize=9, framealpha=0.85, ncol=max(1, color_idx // 12))

        else:
            # Categorical X → grouped bars by packet_size × test_name
            cats      = sorted(df[x_col].unique())
            line_vals = sorted(df["packet_size"].unique())
            test_vals = sorted(df["test_name"].unique())
            combos    = [(lv, tn) for lv in line_vals for tn in test_vals]
            n_groups  = len(combos)
            width     = 0.8 / max(n_groups, 1)
            x_pos     = np.arange(len(cats))

            for i, (lv, tn) in enumerate(combos):
                gdf    = df[(df["packet_size"] == lv) & (df["test_name"] == tn)]
                means  = [gdf[gdf[x_col] == c][y_col].mean() for c in cats]
                offset = (i - n_groups / 2 + 0.5) * width
                self.ax.bar(x_pos + offset, means, width=width * 0.9,
                            label=f"{int(lv)}B {tn}",
                            color=COLORS[i % len(COLORS)], alpha=0.85, zorder=3)

            self.ax.set_xticks(x_pos)
            self.ax.set_xticklabels([str(c) for c in cats], fontsize=11)
            self.ax.set_xlabel(x_label, fontsize=12)
            self.ax.legend(fontsize=9, framealpha=0.85)

        self.ax.set_ylabel(y_label, fontsize=12)
        self.ax.set_title(f"{y_label}  vs  {x_label}", fontsize=13, pad=12)
        self.ax.text(0.99, 0.02, f"n = {len(df)} rows",
                     transform=self.ax.transAxes, ha="right", va="bottom",
                     fontsize=9, color="#aaaaaa")

        self.fig.tight_layout()
        self._cw.draw()
        self._status_var.set(f"{len(df)} rows match current filters")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None)
    args = parser.parse_args()

    db_path = args.db
    if db_path is None:
        root = tk.Tk(); root.withdraw()
        db_path = filedialog.askopenfilename(
            title="Select SQLite database",
            filetypes=[("SQLite", "*.db *.sqlite *.sqlite3"), ("All", "*.*")])
        root.destroy()
        if not db_path:
            sys.exit(0)

    try:
        df = load_data(db_path)
    except Exception as e:
        messagebox.showerror("Load error", str(e)); sys.exit(1)

    if df.empty:
        messagebox.showwarning("Empty", "No data found."); sys.exit(0)

    App(df).mainloop()


if __name__ == "__main__":
    main()