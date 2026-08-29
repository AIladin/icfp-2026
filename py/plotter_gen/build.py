"""Assemble the whole plotter machine onto one canvas.

Lanes are assigned first, rooms hang off them.  Everything is expressed as box origins so
the floorplan can be slid around without re-deriving pipe geometry.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import prog2
import rooms as R
from canvas import Canvas, hline, vline
from snake import Snake

W, H = 56, 54

# box origins ------------------------------------------------------------------
EMIT = (0, 3)
P = (0, 12)
Q = (11, 15)
ECHO = (0, 26)
INROOM = (0, 38)
DISP = (22, 1)
SETUP = (22, 30)


def off(box, d):
    return (box[0] + d[0], box[1] + d[1])


def place(c, box, w, h, body):
    x0, y0 = box
    c.room(x0, y0, x0 + w - 1, y0 + h - 1)
    for i, row in enumerate(body):
        c.text(x0 + 1, y0 + 1 + i, row.replace(" ", "\0"))


def build() -> str:
    c = Canvas(W, H)
    place(c, EMIT, R.EMIT_W, R.EMIT_H, R.EMIT_ROWS)
    place(c, P, R.P_W, R.P_H, R.P_ROWS)
    place(c, Q, R.Q_W, R.Q_H, R.Q_ROWS)
    place(c, ECHO, R.ECHO_W, R.ECHO_H, R.ECHO_ROWS)

    # input room
    c.room(INROOM[0], INROOM[1], INROOM[0] + 2, INROOM[1] + 2)
    c.put(INROOM[0] + 1, INROOM[1] + 1, "I")

    # display 32x24 interior
    c.display(DISP[0], DISP[1], DISP[0] + 33, DISP[1] + 25)

    # SETUP: snake x 23..44, y 31..51; loop-back on row 52 / column 45
    c.room(SETUP[0], SETUP[1], SETUP[0] + 24, SETUP[1] + 23)
    sn = Snake(c, 23, 44, 31, 51)
    sn.x, sn.d = 44, -1
    sn.run(prog2.PROG)
    sn.loop_back(52, 45, spawn_x=23)

    wire(c)
    return c.render()


def wire(c: Canvas) -> None:
    # P -> EMIT (5 cells, into EMIT's bottom wall)
    c.pipe(vline(1, 11, 7), (0, -1))
    # EMIT -> display ADDR (12), EMIT -> display DATA (12)
    c.pipe(vline(16, 2, 0) + hline(0, 17, 25), (0, 1))
    c.pipe(vline(13, 7, 10) + hline(10, 14, 21), (1, 0))
    # P <-> Q (2 cells each)
    c.pipe([(9, 17), (10, 17)], (1, 0))
    c.pipe([(10, 18), (9, 18)], (-1, 0))
    # P -> display SWAP (36 cells; must land after the last DATA)
    c.pipe(hline(13, 9, 21) + vline(21, 14, 27) + hline(27, 22, 30), (0, -1))
    # ECHO -> P, ECHO -> Q
    c.pipe([(8, 25), (8, 24), (8, 23), (7, 23), (6, 23), (6, 22)], (0, -1))
    c.pipe([(14, 25), (14, 24)] + hline(23, 14, 18) + [(18, 22)], (0, -1))
    # ECHO <-> SETUP
    c.pipe([(6, 36), (6, 37), (6, 38)] + hline(38, 7, 21), (1, 0))
    c.pipe(hline(31, 21, 20), (-1, 0))
    # input room -> ECHO (2 cells)
    c.pipe(vline(1, 37, 36), (0, -1))


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/plot.man")
    out.write_text(build())
    print("wrote", out)
