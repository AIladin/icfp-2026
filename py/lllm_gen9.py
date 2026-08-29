"""A 140-column CPU obtained by removing empty pipe-selection zones.

The opcode staircase already fits in columns 8..78.  The old 200-column room only kept rotate
and EMIT sends at columns 130/185.  Put all three outgoing pins on the south wall instead, where
column alone selects state/count/emit, at 65/90/130.  No instruction sequence changes.
"""

from __future__ import annotations

import lllm_gen5 as G

CPU2_W = 140


def room_cpu2(g: G.Grid, x0: int, y0: int) -> G.Room:
    names = (
        "CPU_W", "CPU_N_COL", "CPU_K_COL", "CPU_Q_COL", "CPU_O_COL", "CPU_E_COL",
        "SK", "SQ", "TJX", "CPU_FLAG_R_COL", "CPU_FLAG_S_COL", "CPU_LAP_M_COL",
        "CPU_AFTER_TURN_COL",
        "CPU_O_SIDE", "CPU_E_SIDE", "CPU_N_SIDE", "CPU_K_SIDE", "CPU_Q_SIDE",
    )
    old = {name: getattr(G, name) for name in names}
    try:
        G.CPU_W = CPU2_W
        G.CPU_N_COL, G.CPU_K_COL, G.CPU_Q_COL = 57, 100, 138
        G.CPU_O_COL, G.CPU_E_COL = 5, 42
        G.SK, G.SQ, G.TJX = 100, 138, 139
        G.CPU_FLAG_R_COL, G.CPU_FLAG_S_COL, G.CPU_LAP_M_COL = 138, 133, 70
        G.CPU_AFTER_TURN_COL = 139
        G.CPU_O_SIDE, G.CPU_E_SIDE = "S", "E"
        G.CPU_N_SIDE, G.CPU_K_SIDE, G.CPU_Q_SIDE = "S", "N", "S"
        return G.room_cpu(g, x0, y0)
    finally:
        for name, value in old.items():
            setattr(G, name, value)


def audit() -> int:
    G.ROOMS.clear()
    grid = G.Grid(300, 100)
    room_cpu2(grid, 4, 4)
    return G.audit(grid)


if __name__ == "__main__":
    raise SystemExit(audit())
