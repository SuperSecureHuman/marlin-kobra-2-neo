#!/usr/bin/env python3
"""
UBL Mesh Visualizer
Paste G29 T output between the triple-quotes in MESH_DATA below, then run.
"""

import re
import sys

try:
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
except ImportError:
    print("Installing dependencies...")
    import subprocess

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "numpy", "matplotlib"]
    )
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors

# ── Paste your G29 T output here ─────────────────────────────────────────────
MESH_DATA = """
       0       1       2       3       4       5       6       7       8       9
9 | -0.130  -0.149  -0.168  -0.187  -0.202  -0.196  -0.167  -0.211  -0.205  -0.223
  |
8 | -0.100  -0.125  -0.150  -0.168  -0.189  -0.188  -0.213  -0.203  -0.205  -0.204
  |
7 | -0.077  -0.096  -0.114  -0.135  -0.097  -0.100  -0.109  -0.123  -0.148  -0.149
  |
6 | -0.041  -0.045  -0.048  -0.064  -0.034  -0.032  -0.039  -0.059  -0.077  -0.063
  |
5 | -0.034  -0.043  -0.052  -0.063  -0.030  -0.041  -0.050  -0.050  -0.068  -0.036
  |
4 | -0.000  -0.015  -0.029  -0.036  -0.009  -0.004  -0.030  -0.037  -0.041  -0.043
  |
3 | -0.014  -0.022  -0.029  -0.034  -0.030  -0.037  -0.058  -0.074  -0.060  -0.062
  |
2 | -0.044  -0.061  -0.078  -0.083  -0.088  -0.103  -0.117  -0.132  -0.145  -0.175
  |
1 | -0.083  -0.112  -0.140  -0.134  -0.133  -0.140  -0.166  -0.187  -0.188  -0.197
  |
0 | -0.086 [-0.115] -0.143  -0.137  -0.136  -0.143  -0.169  -0.190  -0.191  -0.200
       0       1       2       3       4       5       6       7       8       9
"""
# ─────────────────────────────────────────────────────────────────────────────


def parse_mesh(text):
    rows = {}
    for line in text.strip().splitlines():
        m = re.match(r"\s*(\d+)\s*\|(.+)", line)
        if not m:
            continue
        row_idx = int(m.group(1))
        # strip brackets around current probe position
        nums = re.sub(r"[\[\]]", "", m.group(2))
        vals = [float(x) for x in re.findall(r"[+-]?\d+\.\d+", nums)]
        if vals:
            rows[row_idx] = vals
    n_rows = max(rows) + 1
    n_cols = max(len(v) for v in rows.values())
    grid = np.zeros((n_rows, n_cols))
    for r, vals in rows.items():
        grid[r, : len(vals)] = vals
    return grid


grid = parse_mesh(MESH_DATA)
n_rows, n_cols = grid.shape

# flip so row 0 is at bottom (front of printer = bottom of plot)
plot_grid = grid  # row 0 = front = bottom in imshow with origin='lower'

vmin, vmax = grid.min(), grid.max()
vcenter = 0.0
total_range = vmax - vmin

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle(
    f"UBL Mesh  |  range: {vmin:+.3f} to {vmax:+.3f} mm  |  total: {total_range:.3f} mm",
    fontsize=13,
    fontweight="bold",
)

# ── Heatmap ───────────────────────────────────────────────────────────────────
ax = axes[0]
ax.set_title("Heatmap  (green=ideal, red=high, blue=low)", fontsize=11)

# diverging colormap centered at 0
norm = mcolors.TwoSlopeNorm(
    vmin=vmin, vcenter=vcenter, vmax=vmax if vmax > 0 else 0.001
)
cmap = plt.cm.RdYlGn_r  # red=high, green=zero, blue=low... use RdBu instead
cmap = plt.cm.RdBu  # blue=negative(low), red=positive(high)

im = ax.imshow(
    plot_grid,
    origin="lower",
    cmap=cmap,
    norm=norm,
    aspect="equal",
    interpolation="nearest",
)

# annotate each cell
for r in range(n_rows):
    for c in range(n_cols):
        val = plot_grid[r, c]
        color = "white" if abs(val) > total_range * 0.4 else "black"
        ax.text(
            c,
            r,
            f"{val:+.3f}",
            ha="center",
            va="center",
            fontsize=7,
            color=color,
            fontweight="bold",
        )

ax.set_xticks(range(n_cols))
ax.set_yticks(range(n_rows))
ax.set_xlabel("X column  (0=left, 9=right)", fontsize=10)
ax.set_ylabel("Y row  (0=front, 9=back)", fontsize=10)
ax.set_xticklabels([f"X{i}" for i in range(n_cols)], fontsize=8)
ax.set_yticklabels([f"Y{i}" for i in range(n_rows)], fontsize=8)

cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label("Z offset (mm)", fontsize=9)

# highlight worst point
worst_r, worst_c = np.unravel_index(np.argmin(plot_grid), plot_grid.shape)
best_r, best_c = np.unravel_index(np.argmax(plot_grid), plot_grid.shape)
ax.add_patch(
    plt.Rectangle(
        (worst_c - 0.5, worst_r - 0.5),
        1,
        1,
        fill=False,
        edgecolor="yellow",
        linewidth=2.5,
        label="lowest",
    )
)
ax.add_patch(
    plt.Rectangle(
        (best_c - 0.5, best_r - 0.5),
        1,
        1,
        fill=False,
        edgecolor="lime",
        linewidth=2.5,
        label="highest",
    )
)
ax.legend(loc="upper right", fontsize=8)

# ── 3D Surface ────────────────────────────────────────────────────────────────
ax3d = fig.add_subplot(1, 2, 2, projection="3d")
ax3d.set_title("3D Surface", fontsize=11)

X, Y = np.meshgrid(np.arange(n_cols), np.arange(n_rows))
surf = ax3d.plot_surface(
    X, Y, plot_grid, cmap="RdBu", norm=norm, edgecolor="grey", linewidth=0.3, alpha=0.9
)
ax3d.set_xlabel("X (col)", fontsize=9)
ax3d.set_ylabel("Y (row)", fontsize=9)
ax3d.set_zlabel("Z (mm)", fontsize=9)
ax3d.set_xticks(range(0, n_cols, 2))
ax3d.set_yticks(range(0, n_rows, 2))
ax3d.view_init(elev=30, azim=225)
fig.colorbar(surf, ax=ax3d, fraction=0.03, pad=0.1).set_label("mm", fontsize=8)

# ── Stats ─────────────────────────────────────────────────────────────────────
stats = (
    f"Min: {vmin:+.3f} mm at X{worst_c} Y{worst_r}\n"
    f"Max: {vmax:+.3f} mm at X{best_c}  Y{best_r}\n"
    f"Range: {total_range:.3f} mm\n"
    f"Mean: {grid.mean():+.3f} mm\n"
    f"Std dev: {grid.std():.3f} mm"
)
fig.text(
    0.01,
    0.01,
    stats,
    fontsize=9,
    family="monospace",
    verticalalignment="bottom",
    bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
)

plt.tight_layout(rect=[0, 0.06, 1, 0.95])
plt.savefig("/tmp/mesh_viz.png", dpi=150, bbox_inches="tight")
print("Saved to /tmp/mesh_viz.png")
plt.show()
