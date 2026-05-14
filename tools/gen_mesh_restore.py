#!/usr/bin/env python3
"""Generate gcode to restore all 100 UBL mesh points from known-good mesh data."""

MESH_MIN_X = 18.0
MESH_MAX_X = 222.0
MESH_MIN_Y = 18.0
MESH_MAX_Y = 222.0
GRID = 10

xs = [MESH_MIN_X + i * (MESH_MAX_X - MESH_MIN_X) / (GRID - 1) for i in range(GRID)]
ys = [MESH_MIN_Y + i * (MESH_MAX_Y - MESH_MIN_Y) / (GRID - 1) for i in range(GRID)]

# Clean mesh — row index matches Y (row 0 = front Y=18, row 9 = back Y=222)
mesh = {
    9: [-0.130, -0.149, -0.168, -0.187, -0.202, -0.196, -0.167, -0.211, -0.205, -0.223],
    8: [-0.100, -0.125, -0.150, -0.168, -0.189, -0.188, -0.213, -0.203, -0.205, -0.204],
    7: [-0.077, -0.096, -0.114, -0.135, -0.097, -0.100, -0.109, -0.123, -0.148, -0.149],
    6: [-0.041, -0.045, -0.048, -0.064, -0.034, -0.032, -0.039, -0.059, -0.077, -0.063],
    5: [-0.034, -0.043, -0.052, -0.063, -0.030, -0.041, -0.050, -0.050, -0.068, -0.036],
    4: [-0.000, -0.015, -0.029, -0.036, -0.009, -0.004, -0.030, -0.037, -0.041, -0.043],
    3: [-0.014, -0.022, -0.029, -0.034, -0.030, -0.037, -0.058, -0.074, -0.060, -0.062],
    2: [-0.044, -0.061, -0.078, -0.083, -0.088, -0.103, -0.117, -0.132, -0.145, -0.175],
    1: [-0.083, -0.112, -0.140, -0.134, -0.133, -0.140, -0.166, -0.187, -0.188, -0.197],
    0: [-0.086, -0.115, -0.143, -0.137, -0.136, -0.143, -0.169, -0.190, -0.191, -0.200],
}

lines = [
    "; Restore UBL mesh — all 100 points via M421 (no UI confirmation)",
    "; I=col (X index 0-9), J=row (Y index 0-9)",
    "",
]

for row in range(GRID):
    for col in range(GRID):
        z = mesh[row][col]
        lines.append(f"M421 I{col} J{row} Z{z:.3f}")

lines += [
    "",
    "G29 A  ; re-enable UBL",
    "G29 S0 ; save to slot 0",
    "M500   ; save EEPROM",
    "M117 Mesh restored",
]

path = "/Users/I749659/repo/a2neo/tools/mesh_restore.gcode"
with open(path, "w") as f:
    f.write("\n".join(lines))

print(f"Written {len([l for l in lines if l.startswith('M421')])} mesh points to {path}")
