"""Derived-shift SETUP experiment on the compact 44x44 plotter.

EMIT / P / Q remain down a narrow left band, ECHO + IN + SETUP below
the display.  Score is max(w,h)^2 * ticks, so the only thing that matters is the *larger*
side -- this layout drives the band down to 16 columns (display 34 + band) and puts every
tall room in the strip under the display.

Band, rows 0..26 (the display owns rows 1..26 from x=DX):
    row 0        ADDR run east into the display's top wall
    EMIT   2..7      P 10..19      Q 22..28
Below, rows 27..:
    ECHO 31..40      IN 43..45     SETUP 27..27+SH-1, x 22..W-1
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import prog5 as prog2
import rooms12 as R
from canvas import Canvas, hline, vline
from snake import Snake

EMIT = (0, 2)
P = (0, 11)
Q = (0, 20)
ECHO = (0, 31)
INROOM = (0, 41)
SETUP_X = 18
SETUP_Y = 27
LANE_P = 10   # ECHO -> P climbs this column past Q
LANE_S = 11   # P -> display SWAP drops down this one


def place(c, box, w, h, body):
    x0, y0 = box
    c.room(x0, y0, x0 + w - 1, y0 + h - 1)
    for i, row in enumerate(body):
        c.text(x0 + 1, y0 + 1 + i, row.replace(" ", "\0"))


def merge_last_branch_on_lower_row(sn: Snake, arms) -> None:
    """Merge plotter's final westbound X into its lower arm and keep heading west."""
    arm_len = max(len(sn._flat(arms[key])) for key in "+-0")
    span = arm_len + 3
    if sn.d != 1 or (sn.x - 1) - sn.x0 < span:
        raise ValueError(f"unexpected final-branch entry: {(sn.x, sn.y, sn.d)}")

    sn._drop(2)
    if sn.d != -1 or sn.room_left() < span:
        raise ValueError(f"unexpected final-branch placement: {(sn.x, sn.y, sn.d)}")

    bx, by, direction = sn.x, sn.y, sn.d
    sn.c.put(bx, by, "X")
    for row, key in ((by + direction, "+"), (by - direction, "-")):
        sn.c.put(bx, row, "<")
        for i, ch in enumerate(sn._flat(arms[key]), 1):
            sn.c.put(bx - i, row, ch)
    for i, ch in enumerate(sn._flat(arms["0"]), 1):
        sn.c.put(bx - i, by, ch)

    merge_x = bx - arm_len - 1
    sn.c.put(merge_x, by - 1, "v")
    sn.c.put(merge_x, by, "v")
    sn.c.put(merge_x, by + 1, "<")
    sn.x, sn.y, sn.d = merge_x - 1, by + 1, -1


def build(w: int = 44, setup_h: int = 17, swap_right: int = 11) -> str:
    h = max(SETUP_Y + setup_h, INROOM[1] + 3)
    dx = w - 34
    c = Canvas(w, h)
    place(c, EMIT, R.EMIT_W, R.EMIT_H, R.EMIT_ROWS)
    place(c, P, R.P_W, R.P_H, R.P_ROWS)
    place(c, Q, R.Q_W, R.Q_H, R.Q_ROWS)
    place(c, ECHO, R.ECHO_W, R.ECHO_H, R.ECHO_ROWS)

    c.room(INROOM[0], INROOM[1], INROOM[0] + 2, INROOM[1] + 2)
    c.put(INROOM[0] + 1, INROOM[1] + 1, "I")
    c.display(dx, 1, dx + 33, 26)

    bx1, by1 = w - 1, SETUP_Y + setup_h - 1
    c.room(SETUP_X, SETUP_Y, bx1, by1)
    sn = Snake(c, SETUP_X + 1, bx1 - 2, SETUP_Y + 1, by1 - 2)
    sn.x, sn.d = bx1 - 2, -1
    # The left-wall queue pipe now departs above ECHO, allowing a 26-column SETUP room.
    # Its extra snake column is intended to recover the row required by the 45-cell height.
    # The final branch's lower arm has a free west suffix. Merge into that suffix instead
    # of spending a fresh continuation row, then put Phase H into the branch's empty east cavity.
    sn.run(prog2.PROG[:44])
    branch_op, branch_arms = prog2.PROG[44]
    if branch_op != "X":
        raise ValueError("SETUP final branch index changed")
    merge_last_branch_on_lower_row(sn, branch_arms)
    sn.run(prog2.PROG[45:46])
    if (sn.x, sn.y, sn.d) != (SETUP_X + 4, by1 - 3, -1):
        raise ValueError(f"SETUP Phase H entry moved: {(sn.x, sn.y, sn.d)}")
    # Wrap before M, then execute it on the new row. This leaves `12` on the same
    # vertically safe columns without paying the old pair of blank cells.
    sn._drop(1)
    phase_h_prefix = prog2.PROG[46:-44]
    if phase_h_prefix[-1] != ("M", None):
        raise ValueError("SETUP derived-shift prefix changed")
    sn.run(phase_h_prefix[:-1])
    c.put(sn.x, sn.y, "M")
    sn.x += sn.d
    if (sn.x, sn.y, sn.d) != (bx1 - 1, by1 - 2, 1):
        raise ValueError(f"SETUP prefix moved: {(sn.x, sn.y, sn.d)}")

    tail = prog2.PROG[-44:]
    if any(op in {"L", "X"} for op, _ in tail):
        raise ValueError("SETUP cavity tail must contain only one-cell operations")
    tail_cells = [(bx1 - 1, y) for y in range(by1 - 3, by1 - 7, -1)]
    tail_cells += [(x, by1 - 7) for x in range(bx1 - 2, bx1 - 11, -1)]
    tail_cells += [(x, by1 - 8) for x in range(bx1 - 10, bx1 - 1)]
    tail_cells += [(x, by1 - 9) for x in range(bx1 - 2, bx1 - 12, -1)]
    tail_cells += [(x, by1 - 10) for x in range(bx1 - 11, bx1 - 1)]
    tail_cells += [(bx1 - 1, y) for y in range(by1 - 11, by1 - 13, -1)]
    if len(tail_cells) != len(tail):
        raise ValueError(f"SETUP tail path has {len(tail_cells)} cells for {len(tail)} ops")
    for (op, _), (x, y) in zip(tail, tail_cells, strict=True):
        c.put(x, y, op)

    for x, y, ch in (
        (bx1 - 1, by1 - 2, "^"),
        (bx1 - 1, by1 - 7, "<"),
        (bx1 - 11, by1 - 7, "^"),
        (bx1 - 11, by1 - 8, ">"),
        (bx1 - 1, by1 - 8, "^"),
        (bx1 - 1, by1 - 9, "<"),
        (bx1 - 12, by1 - 9, "^"),
        (bx1 - 12, by1 - 10, ">"),
        (bx1 - 1, by1 - 10, "^"),
        (bx1 - 1, SETUP_Y + 2, "^"),
        (bx1 - 1, SETUP_Y + 1, "<"),
    ):
        c.put(x, y, ch)
    # Spawn joins the northbound return without occupying the steady-state tail path.
    c.put(bx1 - 2, SETUP_Y + 2, "@")

    wire(c, dx, swap_right)
    return c.render()


def wire(c: Canvas, dx: int, swap_right: int = 21) -> None:
    # EMIT -> display ADDR. DATA doglegs around P; the two values reach the
    # display together, where the specified ADDR-before-DATA order is decisive.
    c.pipe([(3, 1), (3, 0)] + hline(0, 4, dx + 1), (0, 1))
    c.pipe(
        [(6, 9), (6, 10), (7, 10), (7, 9), (8, 9), (8, 10), (9, 10), (9, 9)],
        (1, 0),
    )
    # P -> EMIT
    c.pipe(vline(2, 10, 9), (0, -1))
    # P -> display SWAP: descend directly on the outer lane and turn under the display.
    # ECHO -> P is reordered onto x=9 so it no longer separates this route from display.
    if not 10 < swap_right <= 21:
        raise ValueError("swap_right must be in 11..21")
    c.pipe(vline(9, 18, 27) + hline(27, 10, swap_right), (0, -1))
    # P <-> Q, interleaved on adjacent columns of the shared wall
    c.pipe(vline(5, 18, 19), (0, 1))
    c.pipe(vline(6, 19, 18), (0, -1))
    # ECHO -> Q straight up a west column; ECHO -> P climbs the east lane past Q
    c.pipe(vline(6, 30, 28) + [(5, 28), (4, 28), (4, 27)], (0, -1))
    c.pipe([(10, 30), (10, 29), (9, 29)] + vline(8, 29, 18), (0, -1))
    # ECHO <-> SETUP
    c.pipe([(9, 41), (9, 42)] + hline(42, 10, SETUP_X - 1), (1, 0))
    c.pipe([(SETUP_X - 1, 29), (SETUP_X - 2, 29), (SETUP_X - 2, 30)], (0, 1))
    # input room -> ECHO, doglegged to preserve the two-cell minimum in 44 rows
    c.pipe([(3, 42), (4, 42), (4, 41)], (0, -1))


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/plot2.man")
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 44
    sh = int(sys.argv[3]) if len(sys.argv) > 3 else 17
    swap_right = int(sys.argv[4]) if len(sys.argv) > 4 else 11
    out.write_text(build(w, sh, swap_right))
    print("wrote", out)
