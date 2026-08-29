"""DISP: one pipe in from RAM, the three LM-75 pipes out.

RAM cannot own the display pipes itself.  Three pipes leaving one wall have to reach the display's
*top*, *left* and *bottom*, so they nest only one way, and RAM's side of them is confined to rows
196..408 -- a window set by the easternmost rotator column against the deepest bit-walk block.  Inside
that window they end up at most ~200 rows apart and `lmp` finds no corridor for all three.

So they leave a small room instead, and on **three different walls** -- `p` north, `t` east, `u` south
-- which is what lets the router reach three sides of the display without two pipes contesting one
corridor.  A later redesign put all three on the east wall ninety rows apart; it routes no better and
cannot even be laid, because each lane's dive column crosses the previous lane's return corridor.

Protocol: a selector (0 ADDR, 1 DATA, 2 SWAP) then the value.  RAM forwards both.

The interior is a transcription rather than a routed construction.  At thirty by fourteen it is the one
room in this design small enough to read whole, and every attempt to *derive* the three lanes ran a
dive through an earlier lane's return.  `ROWS` below is the grid exactly as it is packed.
"""

from __future__ import annotations

from gen.canvas import Room
from gen.lay import SGrid

W, H = 30, 14  # interior; the walls and the four markers sit outside it

# one incoming pipe means every `r` binds unconditionally; each `s` sits beside its own marker
PORTS = {
    "cmd": ("C", "W", 6, False),
    "addr": ("p", "N", 14, True),
    "data": ("t", "E", 6, True),
    "swap": ("u", "S", 14, True),
}

ROWS = (
    '',
    '     >        s             v',
    '',
    ' v                          <',
    '',
    '',
    '@>rXr^',
    '   >M1W-Xr                  sv',
    '        >M1W-Xr v',
    ' ^                           <',
    '',
    '',
    ' ^            s <',
    '',
)


def build(g: SGrid, x0: int, y0: int) -> Room:
    room = Room(g, x0, y0, W, H, "DISP")
    for _name, (ch, wall, off, out) in PORTS.items():
        room.mark(ch, wall, off, out)
    for dy, row in enumerate(ROWS):
        for dx, ch in enumerate(row):
            if ch != " ":
                room.put(dx, dy, ch)
    return room


def render(x0: int = 1, y0: int = 1) -> tuple[SGrid, Room]:
    g = SGrid()
    return g, build(g, x0, y0)
