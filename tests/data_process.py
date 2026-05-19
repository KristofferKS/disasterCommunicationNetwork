"""
Network test graph explorer — GUI version with overlay support.

Configure a plot (X varies, fixed values for other dims, Y metric),
then click "Add to chart" to pin it. Add more configs on top.
Each pinned config shows in the chart list — click ✕ to remove one.

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

DIMS = [
    ("packet_size",       "Packet size (bytes)"),
    ("number_of_packets", "Number of packets"),
    ("distance",          "Distance (m)"),
    ("environment",       "Environment"),
]

METRICS = [
    ("throughput",        "Throughput (Kbps)", True),
    ("rtt_ms",            "RTT (ms)",          False),
    ("jitter_ms",         "Jitter (ms)",       False),
    ("packet_loss_iperf", "Packet loss — iperf (%)", False),
    ("packet_loss_ping",  "Packet loss — ping (%)",  False),
    ("duration",          "Duration (s)",      False),
]

COLORS = [
    "#378add", "#D85A30", "#1D9E75", "#7F77DD", "#BA7517",
    "#5DCAA5", "#F09995", "#6A9FB5", "#E8A838", "#A066AA",
    "#4CAF50", "#FF5722", "#00BCD4", "#9C27B0", "#FF9800",
]


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


def short_label(x_col: str, fix: dict[str, str], y_col: str, test_name: str) -> str:
    """One-line legend label for a single series."""
    x_short = {"packet_size": "PS", "number_of_packets": "NP",
                "distance": "Dist", "environment": "Env"}.get(x_col, x_col)
    parts = [f"{x_short} varies"]
    for col, lbl in DIMS:
        if col == x_col:
            continue
        parts.append(f"{lbl.split('(')[0].strip().split(' ')[0]}={fix[col]}")
    parts.append(test_name)
    return " | ".join(parts)


class App(tk.Tk):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self.df = df
        self._ready = False

        self.title("Network test explorer")
        self.configure(bg="#f0f0f0")
        self.minsize(1200, 700)

        self.x_var = tk.StringVar(value=DIMS[0][0])
        self.fix_vars: dict[str, tk.StringVar] = {col: tk.StringVar() for col, _ in DIMS}
        self.y_var  = tk.StringVar(value=METRICS[0][0])
        self.xmin_var = tk.StringVar(value="")
        self.xmax_var = tk.StringVar(value="")

        # List of pinned configs: each is a dict with keys:
        #   x_col, fix (dict col→str), y_col, color_idx, label
        self._pinned: list[dict] = []
        self._color_counter = 0

        self._build_left()
        self._build_right()

        self._update_fix_dropdowns()
        self.x_var.trace_add("write", lambda *_: self._on_x_change())

        self._ready = True
        self._redraw()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        plt.close(self.fig)
        self.quit()
        self.destroy()

    # ── scrollable left panel ─────────────────────────────────────────────────
    def _build_left(self):
        container = tk.Frame(self, bg="#f0f0f0", width=290)
        container.pack(side=tk.LEFT, fill=tk.Y)
        container.pack_propagate(False)

        sb = ttk.Scrollbar(container, orient="vertical")
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._txt = tk.Text(container, yscrollcommand=sb.set,
                            bg="#f0f0f0", relief="flat",
                            highlightthickness=0, cursor="arrow", wrap="none")
        self._txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self._txt.yview)
        self._txt.bind("<Key>", lambda e: "break")

        self._inner = tk.Frame(self._txt, bg="#f0f0f0")
        self._txt.window_create("1.0", window=self._inner)
        self._txt.config(state="disabled")

        self._txt.bind("<Configure>", lambda e: self._inner.config(width=max(1, e.width - 4)))

        def _wheel(e):
            if e.num == 4:   self._txt.yview_scroll(-1, "units")
            elif e.num == 5: self._txt.yview_scroll(1,  "units")
            else:            self._txt.yview_scroll(-1 * int(e.delta / 120), "units")

        for w in (self._txt, self._inner):
            w.bind("<MouseWheel>", _wheel)
            w.bind("<Button-4>",   _wheel)
            w.bind("<Button-5>",   _wheel)

        self._fill_left(self._inner)

    def _sep(self, parent, title):
        tk.Frame(parent, bg="#d0d0d0", height=1).pack(fill=tk.X, pady=(10, 0))
        tk.Label(parent, text=title.upper(), bg="#f0f0f0", fg="#777",
                 font=("Helvetica", 9, "bold"), anchor="w", padx=10, pady=5).pack(fill=tk.X)

    def _fill_left(self, parent):
        tk.Label(parent, text="Network test explorer", bg="#f0f0f0",
                 font=("Helvetica", 12, "bold"), anchor="w", padx=10, pady=12).pack(fill=tk.X)

        # X varies
        self._sep(parent, "X axis — what varies")
        xf = tk.Frame(parent, bg="#f0f0f0")
        xf.pack(fill=tk.X, padx=10, pady=(0, 4))
        for col, label in DIMS:
            tk.Radiobutton(xf, text=label, variable=self.x_var, value=col,
                           bg="#f0f0f0", activebackground="#f0f0f0", anchor="w",
                           font=("Helvetica", 10),
                           command=self._on_x_change).pack(fill=tk.X)

        # Fixed values
        self._sep(parent, "Fixed values for other dimensions")
        self._fix_frame = tk.Frame(parent, bg="#f0f0f0")
        self._fix_frame.pack(fill=tk.X, padx=10, pady=(0, 4))

        # Y metric
        self._sep(parent, "Y axis — metric")
        yf = tk.Frame(parent, bg="#f0f0f0")
        yf.pack(fill=tk.X, padx=10, pady=(0, 8))
        for col, label, _ in METRICS:
            tk.Radiobutton(yf, text=label, variable=self.y_var, value=col,
                           bg="#f0f0f0", activebackground="#f0f0f0", anchor="w",
                           font=("Helvetica", 10),
                           command=self._redraw).pack(fill=tk.X)

        # Add / Clear buttons
        self._sep(parent, "Chart overlay")
        bf = tk.Frame(parent, bg="#f0f0f0")
        bf.pack(fill=tk.X, padx=10, pady=(6, 4))
        tk.Button(bf, text="＋ Add to chart", font=("Helvetica", 10, "bold"),
                  bg="#378add", fg="white", relief="flat", cursor="hand2",
                  activebackground="#2a6db0", activeforeground="white",
                  padx=8, pady=4,
                  command=self._add_to_chart).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(bf, text="Clear all", font=("Helvetica", 10),
                  bg="#f0f0f0", relief="flat", cursor="hand2",
                  fg="#c0392b", activeforeground="#922b21",
                  padx=8, pady=4,
                  command=self._clear_all).pack(side=tk.LEFT)

    # ── rebuild fix dropdowns ─────────────────────────────────────────────────
    def _update_fix_dropdowns(self):
        for w in self._fix_frame.winfo_children():
            w.destroy()

        x_col = self.x_var.get()
        for col, label in DIMS:
            if col == x_col:
                continue
            vals     = sorted(self.df[col].unique())
            str_vals = [str(int(v)) if col not in ("environment", "test_name")
                        else str(v) for v in vals]
            cur = self.fix_vars[col].get()
            if cur not in str_vals:
                self.fix_vars[col].set(str_vals[0] if str_vals else "")

            row = tk.Frame(self._fix_frame, bg="#f0f0f0")
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=label, bg="#f0f0f0", anchor="w",
                     font=("Helvetica", 10), width=20).pack(side=tk.LEFT)
            cb = ttk.Combobox(row, textvariable=self.fix_vars[col],
                              values=str_vals, state="readonly", width=10)
            cb.pack(side=tk.LEFT, padx=(4, 0))
            cb.bind("<<ComboboxSelected>>", lambda e: self._redraw())

        tk.Label(self._fix_frame, text="Each test name = one line",
                 bg="#f0f0f0", fg="#888", font=("Helvetica", 9, "italic"),
                 anchor="w").pack(fill=tk.X, pady=(6, 0))

    # ── right panel ───────────────────────────────────────────────────────────
    def _build_right(self):
        right = tk.Frame(self, bg="#ffffff")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Chart list at top of right panel
        list_frame = tk.Frame(right, bg="#f8f8f8", bd=0)
        list_frame.pack(fill=tk.X, padx=12, pady=(10, 0))
        tk.Label(list_frame, text="Pinned series:", bg="#f8f8f8",
                 font=("Helvetica", 9, "bold"), fg="#555").pack(anchor="w")
        self._list_frame = tk.Frame(list_frame, bg="#f8f8f8")
        self._list_frame.pack(fill=tk.X)

        # Chart
        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        self.fig.patch.set_facecolor("#ffffff")
        self._cw = FigureCanvasTkAgg(self.fig, master=right)
        self._cw.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        # X range controls
        xrange = tk.Frame(right, bg="#ffffff")
        xrange.pack(fill=tk.X, padx=12, pady=(0, 2))
        tk.Label(xrange, text="X range:", bg="#ffffff", fg="#555",
                 font=("Helvetica", 10)).pack(side=tk.LEFT)
        tk.Label(xrange, text="min", bg="#ffffff", fg="#777",
                 font=("Helvetica", 9)).pack(side=tk.LEFT, padx=(6, 2))
        self.xmin_entry = tk.Entry(xrange, textvariable=self.xmin_var, width=8,
                                   font=("Helvetica", 10), relief="solid", bd=1)
        self.xmin_entry.pack(side=tk.LEFT)
        tk.Label(xrange, text="max", bg="#ffffff", fg="#777",
                 font=("Helvetica", 9)).pack(side=tk.LEFT, padx=(8, 2))
        self.xmax_entry = tk.Entry(xrange, textvariable=self.xmax_var, width=8,
                                   font=("Helvetica", 10), relief="solid", bd=1)
        self.xmax_entry.pack(side=tk.LEFT)
        tk.Button(xrange, text="Apply", font=("Helvetica", 9),
                  bg="#f0f0f0", relief="flat", cursor="hand2", padx=6,
                  command=self._redraw).pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(xrange, text="Reset", font=("Helvetica", 9),
                  bg="#f0f0f0", relief="flat", cursor="hand2", padx=6,
                  command=self._reset_xrange).pack(side=tk.LEFT, padx=(2, 0))

        self._status = tk.StringVar(value="")
        bottom = tk.Frame(right, bg="#ffffff")
        bottom.pack(fill=tk.X, pady=(0, 6))
        tk.Label(bottom, textvariable=self._status, bg="#ffffff", fg="#999",
                 font=("Helvetica", 10), anchor="w", padx=16).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(bottom, text="💾 Save graph", font=("Helvetica", 10),
                  bg="#f0f0f0", relief="flat", cursor="hand2",
                  fg="#333", activeforeground="#000",
                  padx=10, pady=3,
                  command=self._save_figure).pack(side=tk.RIGHT, padx=12)

    # ── pinned series list UI ─────────────────────────────────────────────────
    def _rebuild_list_ui(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

        if not self._pinned:
            tk.Label(self._list_frame, text="(none — click 'Add to chart')",
                     bg="#f8f8f8", fg="#aaa", font=("Helvetica", 9, "italic")).pack(anchor="w")
            return

        for i, cfg in enumerate(self._pinned):
            row = tk.Frame(self._list_frame, bg="#f8f8f8")
            row.pack(fill=tk.X, pady=2)

            # Colour swatch
            tk.Frame(row, bg=COLORS[cfg["color_idx"] % len(COLORS)],
                     width=12, height=12).pack(side=tk.LEFT, padx=(0, 5))

            # Inline editable name entry
            name_var = tk.StringVar(value=cfg["label"])
            cfg["_name_var"] = name_var   # keep reference so it survives GC

            entry = tk.Entry(row, textvariable=name_var, font=("Helvetica", 9),
                             bg="#f8f8f8", relief="flat", fg="#333",
                             highlightthickness=1, highlightbackground="#d0d0d0",
                             highlightcolor="#378add")
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

            def make_rename(idx=i, var=name_var):
                def _rename(*_):
                    self._pinned[idx]["label"] = var.get()
                    self._redraw()
                return _rename

            name_var.trace_add("write", make_rename())

            def make_remove(idx=i):
                return lambda: self._remove(idx)

            tk.Button(row, text="✕", font=("Helvetica", 8), fg="#c0392b",
                      bg="#f8f8f8", relief="flat", cursor="hand2",
                      activeforeground="#922b21",
                      command=make_remove()).pack(side=tk.RIGHT)

    # ── overlay management ────────────────────────────────────────────────────
    def _current_fix(self) -> dict[str, str]:
        return {col: self.fix_vars[col].get() for col, _ in DIMS}

    def _add_to_chart(self):
        x_col = self.x_var.get()
        y_col = self.y_var.get()
        fix   = self._current_fix()
        df    = self._filter(x_col, fix)

        if df.empty:
            messagebox.showwarning("No data", "Current selection returned no data.")
            return

        test_names = sorted(df["test_name"].unique())
        _, y_label, to_kbps = next(m for m in METRICS if m[0] == y_col)

        for tn in test_names:
            label = short_label(x_col, fix, y_col, tn)
            # Avoid exact duplicates
            if any(p["label"] == label for p in self._pinned):
                continue
            self._pinned.append({
                "x_col":     x_col,
                "fix":       dict(fix),
                "y_col":     y_col,
                "to_kbps":   to_kbps,
                "test_name": tn,
                "label":     label,
                "color_idx": self._color_counter,
            })
            self._color_counter += 1

        self._rebuild_list_ui()
        self._redraw()

    def _remove(self, idx: int):
        self._pinned.pop(idx)
        self._rebuild_list_ui()
        self._redraw()

    def _clear_all(self):
        self._pinned.clear()
        self._color_counter = 0
        self._rebuild_list_ui()
        self._redraw()

    # ── filtering ─────────────────────────────────────────────────────────────
    def _filter(self, x_col: str, fix: dict[str, str]) -> pd.DataFrame:
        df = self.df.copy()
        for col, _ in DIMS:
            if col == x_col:
                continue
            val_str = fix.get(col, "")
            if not val_str:
                return df.iloc[0:0]
            if col not in ("environment", "test_name"):
                try:
                    val = type(df[col].iloc[0])(val_str)
                except Exception:
                    val = val_str
            else:
                val = val_str
            df = df[df[col] == val]
        return df

    def _reset_xrange(self):
        self.xmin_var.set("")
        self.xmax_var.set("")
        self._redraw()

    def _on_x_change(self):
        # Reset X range whenever the X axis dimension changes
        self.xmin_var.set("")
        self.xmax_var.set("")
        self._update_fix_dropdowns()
        self._redraw()

    # ── chart ─────────────────────────────────────────────────────────────────
    def _redraw(self, _=None, preview=True):
        if not self._ready:
            return

        self.ax.clear()
        self.ax.set_facecolor("#ffffff")
        self.ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.55, zorder=0)
        self.ax.spines[["top", "right"]].set_visible(False)

        x_col   = self.x_var.get()
        y_col   = self.y_var.get()
        fix     = self._current_fix()
        x_label = next(lbl for col, lbl in DIMS if col == x_col)
        _, y_label_pre, to_kbps_pre = next(m for m in METRICS if m[0] == y_col)

        # ── preview (grey dashed) — skipped when saving ──────────────────────
        if preview:
            df_pre = self._filter(x_col, fix)
            if not df_pre.empty and not df_pre[y_col].isna().all():
                if to_kbps_pre:
                    df_pre = df_pre.copy()
                    df_pre[y_col] = df_pre[y_col] / 1000
                for tn in sorted(df_pre["test_name"].unique()):
                    tdf = df_pre[df_pre["test_name"] == tn]
                    agg = tdf.groupby(x_col)[y_col].mean().reset_index().sort_values(x_col)
                    self.ax.plot(agg[x_col], agg[y_col], marker="o",
                                 label=f"[preview] {tn}", color="#bbbbbb",
                                 linewidth=1.5, markersize=4, linestyle="--", zorder=2)

        # ── pinned series ─────────────────────────────────────────────────────
        total_rows   = 0
        y_labels_used = set()
        all_y_vals   = []   # all pinned Y values (for Y scaling)
        all_xy_vals  = []   # (x, y) pairs (for Y scaling after X range applied)

        for cfg in self._pinned:
            df2 = self._filter(cfg["x_col"], cfg["fix"])
            if df2.empty:
                continue
            df2 = df2[df2["test_name"] == cfg["test_name"]]
            if df2.empty:
                continue

            yc = cfg["y_col"]
            if cfg["to_kbps"]:
                df2 = df2.copy()
                df2[yc] = df2[yc] / 1000
            _, yl, _ = next(m for m in METRICS if m[0] == yc)
            y_labels_used.add(yl)

            agg = df2.groupby(cfg["x_col"])[yc].mean().reset_index().sort_values(cfg["x_col"])
            color = COLORS[cfg["color_idx"] % len(COLORS)]
            is_num = pd.api.types.is_numeric_dtype(df2[cfg["x_col"]])

            # Collect for Y-limit calculation
            all_y_vals.extend(agg[yc].dropna().tolist())
            if is_num:
                all_xy_vals.extend(zip(agg[cfg["x_col"]].tolist(), agg[yc].tolist()))

            if is_num:
                self.ax.plot(agg[cfg["x_col"]], agg[yc], marker="o",
                             label=cfg["label"], color=color,
                             linewidth=2, markersize=6, zorder=3)
            else:
                x_pos  = np.arange(len(agg))
                n_pins = len(self._pinned)
                w      = 0.7 / max(n_pins, 1)
                offset = (self._pinned.index(cfg) - n_pins / 2 + 0.5) * w
                self.ax.bar(x_pos + offset, agg[yc], width=w * 0.9,
                            label=cfg["label"], color=color, alpha=0.85, zorder=3)
                self.ax.set_xticks(x_pos)
                self.ax.set_xticklabels([str(v) for v in agg[cfg["x_col"]]], fontsize=11)

            total_rows += len(df2)

        # ── Y limits: computed from pinned data only (ignores preview line) ───
        if self._pinned and all_y_vals:
            ylo = min(v for v in all_y_vals if pd.notna(v))
            yhi = max(v for v in all_y_vals if pd.notna(v))
            pad = (yhi - ylo) * 0.08 if yhi != ylo else max(abs(yhi) * 0.1, 1)
            self.ax.set_ylim(max(0, ylo - pad), yhi + pad)

        # ── X range override ──────────────────────────────────────────────────
        try:
            xmin = float(self.xmin_var.get()) if self.xmin_var.get().strip() else None
            xmax = float(self.xmax_var.get()) if self.xmax_var.get().strip() else None
            if xmin is not None or xmax is not None:
                cur_xmin, cur_xmax = self.ax.get_xlim()
                new_xmin = xmin if xmin is not None else cur_xmin
                new_xmax = xmax if xmax is not None else cur_xmax
                self.ax.set_xlim(new_xmin, new_xmax)
                # Re-compute Y limits for only the data visible in the X window
                if self._pinned and all_xy_vals:
                    vis_y = [y for x, y in all_xy_vals if new_xmin <= x <= new_xmax]
                    if vis_y:
                        ylo2 = min(vis_y)
                        yhi2 = max(vis_y)
                        pad2 = (yhi2 - ylo2) * 0.08 if yhi2 != ylo2 else max(abs(yhi2) * 0.1, 1)
                        self.ax.set_ylim(max(0, ylo2 - pad2), yhi2 + pad2)
        except ValueError:
            pass

        # ── labels / legend ───────────────────────────────────────────────────
        if y_labels_used:
            y_label_final = y_labels_used.pop() if len(y_labels_used) == 1 else "Value"
        else:
            y_label_final = y_label_pre

        if pd.api.types.is_numeric_dtype(self.df[x_col]):
            self.ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        self.ax.set_xlabel(x_label, fontsize=12)
        self.ax.set_ylabel(y_label_final, fontsize=12)
        self.ax.set_title(
            f"{y_label_final}  vs  {x_label}"
            + (f"  ({len(self._pinned)} pinned)" if self._pinned else "  [preview]"),
            fontsize=12, pad=10,
        )

        handles, labels = self.ax.get_legend_handles_labels()
        if handles:
            ncol = max(1, min(len(handles), 4))
            self.ax.legend(handles, labels, fontsize=9, framealpha=0.85, ncol=ncol,
                           loc="upper center", bbox_to_anchor=(0.5, -0.16),
                           borderaxespad=0)

        self.fig.subplots_adjust(bottom=0.26, top=0.90, left=0.11, right=0.97)
        self._cw.draw()
        self._status.set(
            f"{len(self._pinned)} pinned series — {total_rows} rows plotted"
            if self._pinned else "Preview mode — click '＋ Add to chart' to pin"
        )


    def _save_figure(self):
        path = filedialog.asksaveasfilename(
            title="Save graph",
            defaultextension=".png",
            filetypes=[
                ("PNG image",        "*.png"),
                ("PDF document",     "*.pdf"),
                ("SVG vector image", "*.svg"),
            ],
        )
        if not path:
            return
        try:
            # Redraw without preview, save, then restore preview
            self._redraw(preview=False)
            self.fig.savefig(path, dpi=200, bbox_inches="tight")
            self._status.set(f"Saved → {path}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
        finally:
            # Always restore the preview version on screen
            self._redraw(preview=True)


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