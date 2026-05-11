"""
Iteration convergence explorer.

Shows how the mean and confidence band of a metric stabilises as you
include more iterations. Use the slider to set how many iterations
(1 → max) are used. The band is mean ± std across the included iterations,
plotted over each unique test configuration (packet_size × number_of_packets).

Usage:
    python iteration_explorer.py
    python iteration_explorer.py --db path/to/my.db

Requirements: pip install matplotlib pandas
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

# ── metrics ───────────────────────────────────────────────────────────────────
METRICS = [
    ("throughput",        "Throughput (Kbps)",        True),   # (col, label, convert_to_kbps)
    ("rtt_ms",            "RTT (ms)",                 False),
    ("jitter_ms",         "Jitter (ms)",              False),
    ("packet_loss_iperf", "Packet loss — iperf (%)",  False),
    ("packet_loss_ping",  "Packet loss — ping (%)",   False),
]

X_AXES = [
    ("packet_size",       "Packet size (bytes)"),
    ("number_of_packets", "Number of packets"),
    ("distance",          "Distance (m)"),
]

COLORS = ["#378add", "#D85A30", "#1D9E75", "#7F77DD", "#BA7517", "#5DCAA5", "#F09995"]


# ── data loading ──────────────────────────────────────────────────────────────
def load_iterations(db_path: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        """
        SELECT
            t.test_name, t.environment, t.distance,
            t.packet_size, t.number_of_packets,
            i.iteration,
            i.throughput, i.jitter_ms,
            i.packet_loss_iperf, i.packet_loss_ping,
            i.rtt_ms
        FROM iterations i
        JOIN tests t ON i.test_id = t.id
        ORDER BY t.id, i.iteration
        """,
        conn,
    )
    conn.close()
    return df


# ── application ───────────────────────────────────────────────────────────────
class IterApp(tk.Tk):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self.df = df
        self._ready = False

        self.title("Iteration convergence explorer")
        self.configure(bg="#f0f0f0")
        self.minsize(1150, 680)

        # Max iterations across all tests
        self._max_iter = int(df["iteration"].max())

        # ── tk vars ───────────────────────────────────────────────────────────
        self.n_iter_var    = tk.IntVar(value=self._max_iter)
        self.y_var         = tk.StringVar(value=METRICS[0][0])
        self.x_var         = tk.StringVar(value=X_AXES[0][0])
        self.split_env_var = tk.BooleanVar(value=False)
        self.check_vars: dict[tuple, tk.BooleanVar] = {}

        self._build_left()
        self._build_right()

        self._ready = True
        self._refresh()

    # ── left panel ────────────────────────────────────────────────────────────
    def _build_left(self):
        container = tk.Frame(self, bg="#f0f0f0", width=270)
        container.pack(side=tk.LEFT, fill=tk.Y)
        container.pack_propagate(False)

        lc = tk.Canvas(container, bg="#f0f0f0", highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=lc.yview)
        lc.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        lc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._lc = lc

        inner = tk.Frame(lc, bg="#f0f0f0")
        lc.create_window((0, 0), window=inner, anchor="nw", tags="inner")
        inner.bind("<Configure>", lambda e: lc.configure(scrollregion=lc.bbox("all")))
        lc.bind("<Configure>",    lambda e: lc.itemconfig("inner", width=e.width))

        def _wheel(e):
            if e.num == 4:   lc.yview_scroll(-1, "units")
            elif e.num == 5: lc.yview_scroll(1,  "units")
            else:            lc.yview_scroll(-1 * int(e.delta / 120), "units")

        lc.bind("<MouseWheel>", _wheel)
        lc.bind("<Button-4>",   _wheel)
        lc.bind("<Button-5>",   _wheel)

        self._fill_left(inner)

    def _sep(self, parent, title):
        tk.Frame(parent, bg="#d0d0d0", height=1).pack(fill=tk.X, pady=(10, 0))
        tk.Label(parent, text=title.upper(), bg="#f0f0f0", fg="#777",
                 font=("Helvetica", 9, "bold"), anchor="w", padx=10, pady=5).pack(fill=tk.X)

    def _fill_left(self, parent):
        tk.Label(parent, text="Iteration convergence explorer",
                 bg="#f0f0f0", font=("Helvetica", 11, "bold"),
                 anchor="w", padx=10, pady=12).pack(fill=tk.X)

        # ── Iteration slider ──────────────────────────────────────────────────
        self._sep(parent, f"Iterations to include  (max {self._max_iter})")
        sf = tk.Frame(parent, bg="#f0f0f0")
        sf.pack(fill=tk.X, padx=10, pady=(0, 6))

        row = tk.Frame(sf, bg="#f0f0f0")
        row.pack(fill=tk.X)
        tk.Label(row, text="N =", bg="#f0f0f0", font=("Helvetica", 10)).pack(side=tk.LEFT)
        self._iter_lbl = tk.Label(row, text=str(self._max_iter), width=5,
                                  bg="#f0f0f0", font=("Helvetica", 12, "bold"), fg="#378add")
        self._iter_lbl.pack(side=tk.LEFT, padx=4)

        self._iter_sl = ttk.Scale(
            sf, from_=1, to=self._max_iter,
            variable=self.n_iter_var, orient="horizontal",
            command=self._on_iter,
        )
        self._iter_sl.pack(fill=tk.X, pady=(4, 0))

        # tick marks hint
        tick_row = tk.Frame(sf, bg="#f0f0f0")
        tick_row.pack(fill=tk.X)
        tk.Label(tick_row, text="1", bg="#f0f0f0", fg="#aaa",
                 font=("Helvetica", 8)).pack(side=tk.LEFT)
        tk.Label(tick_row, text=str(self._max_iter), bg="#f0f0f0", fg="#aaa",
                 font=("Helvetica", 8)).pack(side=tk.RIGHT)

        # ── Checkboxes: packet_size, number_of_packets, environment ──────────
        for col, label in [
            ("packet_size",       "Packet size (bytes)"),
            ("number_of_packets", "Number of packets"),
            ("environment",       "Environment"),
        ]:
            self._sep(parent, label)
            f = tk.Frame(parent, bg="#f0f0f0")
            f.pack(fill=tk.X, padx=10, pady=(0, 4))

            def make_toggle(c=col):
                def toggle():
                    vals = [v for (cc, _), v in self.check_vars.items() if cc == c]
                    s = not all(v.get() for v in vals)
                    for v in vals: v.set(s)
                    self._refresh()
                return toggle

            tk.Button(f, text="all / none", font=("Helvetica", 8),
                      bg="#f0f0f0", relief="flat", cursor="hand2",
                      fg="#555", command=make_toggle()).pack(anchor="w")

            for v in sorted(self.df[col].unique()):
                var  = tk.BooleanVar(value=True)
                self.check_vars[(col, v)] = var
                text = str(int(v)) if col != "environment" else str(v)
                tk.Checkbutton(f, text=text, variable=var, bg="#f0f0f0",
                               activebackground="#f0f0f0", anchor="w",
                               font=("Helvetica", 10),
                               command=self._refresh).pack(fill=tk.X)

        # ── Y metric ─────────────────────────────────────────────────────────
        self._sep(parent, "Y axis — metric")
        yf = tk.Frame(parent, bg="#f0f0f0")
        yf.pack(fill=tk.X, padx=10, pady=(0, 4))
        for col, label, _ in METRICS:
            tk.Radiobutton(yf, text=label, variable=self.y_var, value=col,
                           bg="#f0f0f0", activebackground="#f0f0f0", anchor="w",
                           font=("Helvetica", 10), command=self._refresh).pack(fill=tk.X)

        # ── X axis ───────────────────────────────────────────────────────────
        self._sep(parent, "X axis — group by")
        xf = tk.Frame(parent, bg="#f0f0f0")
        xf.pack(fill=tk.X, padx=10, pady=(0, 4))
        for col, label in X_AXES:
            tk.Radiobutton(xf, text=label, variable=self.x_var, value=col,
                           bg="#f0f0f0", activebackground="#f0f0f0", anchor="w",
                           font=("Helvetica", 10), command=self._refresh).pack(fill=tk.X)

        # ── Options ───────────────────────────────────────────────────────────
        self._sep(parent, "Options")
        of = tk.Frame(parent, bg="#f0f0f0")
        of.pack(fill=tk.X, padx=10, pady=(0, 20))
        tk.Checkbutton(of, text="Split lines by environment",
                       variable=self.split_env_var, bg="#f0f0f0",
                       activebackground="#f0f0f0", anchor="w",
                       font=("Helvetica", 10), command=self._refresh).pack(fill=tk.X)

    # ── right panel ───────────────────────────────────────────────────────────
    def _build_right(self):
        right = tk.Frame(self, bg="#ffffff")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        self.fig.patch.set_facecolor("#ffffff")

        self._cw = FigureCanvasTkAgg(self.fig, master=right)
        self._cw.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self._status = tk.StringVar(value="")
        tk.Label(right, textvariable=self._status, bg="#ffffff", fg="#999",
                 font=("Helvetica", 10), anchor="w", padx=16).pack(fill=tk.X, pady=(0, 6))

    # ── handlers ─────────────────────────────────────────────────────────────
    def _on_iter(self, _=None):
        n = int(round(self.n_iter_var.get()))
        self.n_iter_var.set(n)
        self._iter_lbl.config(text=str(n))
        self._refresh()

    # ── filter ────────────────────────────────────────────────────────────────
    def _get_filtered(self) -> pd.DataFrame:
        n   = int(round(self.n_iter_var.get()))
        df  = self.df[self.df["iteration"] <= n].copy()
        for col in ("packet_size", "number_of_packets", "environment"):
            allowed = [v for (c, v), var in self.check_vars.items() if c == col and var.get()]
            if not allowed:
                return df.iloc[0:0]
            df = df[df[col].isin(allowed)]
        return df

    # ── chart ─────────────────────────────────────────────────────────────────
    def _refresh(self, _=None):
        if not self._ready:
            return

        df    = self._get_filtered()
        y_col = self.y_var.get()
        x_col = self.x_var.get()
        _, y_label, to_kbps = next(m for m in METRICS if m[0] == y_col)
        x_label = next(lbl for col, lbl in X_AXES if col == x_col)
        n_iter  = int(round(self.n_iter_var.get()))
        split   = self.split_env_var.get()

        if to_kbps and not df.empty:
            df = df.copy()
            df[y_col] = df[y_col] / 1000

        self.ax.clear()
        self.ax.set_facecolor("#ffffff")
        self.ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.5, zorder=0)
        self.ax.spines[["top", "right"]].set_visible(False)

        if df.empty or df[y_col].isna().all():
            self.ax.text(0.5, 0.5, "No data matches current filters",
                         transform=self.ax.transAxes, ha="center", va="center",
                         fontsize=13, color="#bbb")
            self._status.set("0 rows")
            self._cw.draw()
            return

        # Determine line grouping column (the "other" dimension vs x_col)
        if x_col == "packet_size":
            line_col, line_fmt = "number_of_packets", lambda v: f"{int(v)} pkts"
        elif x_col == "number_of_packets":
            line_col, line_fmt = "packet_size",       lambda v: f"{int(v)} B"
        else:  # distance
            line_col, line_fmt = "packet_size",       lambda v: f"{int(v)} B"

        env_vals  = sorted(df["environment"].unique()) if split else [None]
        line_vals = sorted(df[line_col].unique())

        color_idx = 0
        for env in env_vals:
            edf = df[df["environment"] == env] if env is not None else df
            for lv in line_vals:
                gdf = edf[edf[line_col] == lv]
                if gdf.empty:
                    continue

                # For each unique x value: mean and std across the N included iterations
                agg = (
                    gdf.groupby(x_col)[y_col]
                    .agg(mean="mean", std="std")
                    .reset_index()
                    .sort_values(x_col)
                )
                agg["std"] = agg["std"].fillna(0)

                color = COLORS[color_idx % len(COLORS)]
                color_idx += 1

                parts = [line_fmt(lv)]
                if env is not None:
                    parts.append(str(env))
                label = ", ".join(parts)

                # Shaded band: mean ± std
                self.ax.fill_between(
                    agg[x_col],
                    (agg["mean"] - agg["std"]).clip(lower=0),
                    agg["mean"] + agg["std"],
                    alpha=0.15, color=color, zorder=2,
                )
                # Mean line
                self.ax.plot(
                    agg[x_col], agg["mean"],
                    marker="o", color=color, label=label,
                    linewidth=2, markersize=5, zorder=3,
                )

        self.ax.set_xlabel(x_label, fontsize=12)
        self.ax.set_ylabel(y_label, fontsize=12)
        self.ax.set_title(
            f"{y_label}  vs  {x_label}   [first {n_iter} iteration{'s' if n_iter != 1 else ''}]",
            fontsize=13, pad=12,
        )
        self.ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        self.ax.legend(fontsize=9, framealpha=0.85,
                       ncol=max(1, color_idx // 10))
        self.ax.text(0.99, 0.02, f"n = {len(df)} data points",
                     transform=self.ax.transAxes, ha="right", va="bottom",
                     fontsize=9, color="#aaa")

        self.fig.tight_layout()
        self._cw.draw()
        self._status.set(
            f"{len(df)} data points from {n_iter} iteration{'s' if n_iter != 1 else ''} "
            f"— band = mean ± std"
        )


# ── entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Iteration convergence explorer")
    parser.add_argument("--db", default=None)
    args = parser.parse_args()

    db_path = args.db
    if db_path is None:
        root = tk.Tk()
        root.withdraw()
        db_path = filedialog.askopenfilename(
            title="Select SQLite database",
            filetypes=[("SQLite", "*.db *.sqlite *.sqlite3"), ("All", "*.*")],
        )
        root.destroy()
        if not db_path:
            print("No file selected.")
            sys.exit(0)

    try:
        df = load_iterations(db_path)
    except Exception as e:
        messagebox.showerror("Load error", str(e))
        sys.exit(1)

    if df.empty:
        messagebox.showwarning("Empty", "No iteration data found.")
        sys.exit(0)

    IterApp(df).mainloop()


if __name__ == "__main__":
    main()