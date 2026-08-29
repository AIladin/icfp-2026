"""Stacked-band floorplan: EMIT / P / Q down a narrow left band, ECHO + IN + SETUP below
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

import prog4 as prog2
import rooms4 as R
from canvas import Canvas, hline, vline
from snake import Snake

EMIT = (0, 2)
P = (0, 10)
Q = (0, 19)
ECHO = (0, 31)
INROOM = (0, 43)
SETUP_X = 21
SETUP_Y = 27
LANE_P = 10   # ECHO -> P climbs this column past Q
LANE_S = 11   # P -> display SWAP drops down this one


def place(c, box, w, h, body):
    x0, y0 = box
    c.room(x0, y0, x0 + w - 1, y0 + h - 1)
    for i, row in enumerate(body):
        c.text(x0 + 1, y0 + 1 + i, row.replace(" ", "\0"))


def build(w: int = 48, setup_h: int = 21, swap_right: int = 21) -> str:
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
    # One redundant full lap of five FIFO rotations is gone. Execute ten cells on the
    # final eastbound row, turn around the bottom-right corner, then execute the remaining
    # eleven northward in the return column. This is what removes SETUP's twentieth row.
    tail = prog2.PROG[-21:]
    if any(op in {"L", "X"} for op, _ in tail):
        raise ValueError("SETUP folded tail must contain only one-cell operations")
    sn.run(prog2.PROG[:-21])
    if (sn.x, sn.y, sn.d) != (bx1 - 12, by1 - 2, 1):
        raise ValueError(f"SETUP prefix moved: {(sn.x, sn.y, sn.d)}")
    for i, (op, _) in enumerate(tail[:10]):
        c.put(sn.x + i, sn.y, op)
    c.put(bx1 - 2, sn.y, "v")
    c.put(bx1 - 2, sn.y + 1, ">")
    c.put(bx1 - 1, sn.y + 1, "^")
    for i, (op, _) in enumerate(tail[10:]):
        c.put(bx1 - 1, sn.y - i, op)
    c.put(bx1 - 1, SETUP_Y + 1, "<")
    # Spawn joins the return column after the final tail operation, before the next round.
    c.put(bx1 - 2, SETUP_Y + 2, "@")
    c.put(bx1 - 1, SETUP_Y + 2, "^")

    wire(c, dx, swap_right)
    return c.render()


def wire(c: Canvas, dx: int, swap_right: int = 21) -> None:
    # EMIT -> display ADDR (up one, then east along row 0), EMIT -> display DATA
    c.pipe([(6, 1), (6, 0)] + hline(0, 7, dx + 4), (0, 1))
    c.pipe([(9, 8)] + hline(9, 9, dx - 1), (1, 0))
    # P -> EMIT
    c.pipe(vline(2, 9, 8), (0, -1))
    # P -> display SWAP: east, down the lane at x=14, east under the display
    # P's ring is faster than EMIT's, so SWAP needs a delay. The fallback uses 50 cells
    # (`swap_right=21`); exhaustive setup checks plus 2,000 assembled stress segments measured
    # 38 (`swap_right=18`) safe, while 34 overtakes the last DATA on five public cases.
    if not 15 < swap_right <= 21:
        raise ValueError("swap_right must be in 16..21")
    c.pipe([(10, 13), (LANE_S, 13)] + vline(LANE_S, 14, 30)
           + hline(30, LANE_S + 1, swap_right) + [(swap_right, 29)]
           + hline(29, swap_right - 1, LANE_S + 1) + [(LANE_S + 1, 28)]
           + hline(28, LANE_S + 2, swap_right) + [(swap_right, 27)]
           + hline(27, swap_right - 1, dx + 1), (0, -1))
    # P <-> Q, interleaved on adjacent columns of the shared wall
    c.pipe(vline(5, 17, 18), (0, 1))
    c.pipe(vline(6, 18, 17), (0, -1))
    # ECHO -> Q straight up a west column; ECHO -> P climbs the east lane past Q
    c.pipe(vline(7, 30, 27) + [(6, 27), (5, 27), (4, 27), (4, 26)], (0, -1))
    c.pipe(vline(LANE_P, 30, 14), (-1, 0))
    # ECHO <-> SETUP
    c.pipe([(8, 41), (8, 42)] + hline(42, 9, SETUP_X - 1), (1, 0))
    c.pipe(hline(36, SETUP_X - 1, 19), (-1, 0))
    # input room -> ECHO
    c.pipe(vline(1, 42, 41), (0, -1))


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/plot2.man")
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    sh = int(sys.argv[3]) if len(sys.argv) > 3 else 21
    swap_right = int(sys.argv[4]) if len(sys.argv) > 4 else 21
    out.write_text(build(w, sh, swap_right))
    print("wrote", out)
