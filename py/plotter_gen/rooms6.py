"""Room interiors for the 46x46 split-EMIT plotter candidate.

Only EMIT differs from rooms5: its startup begins one cell left, while each DATA
worker sends one cell earlier and halts directly. This removes the eleventh
interior column without sharing an executable control cell.
"""

from rooms5 import *  # noqa: F403

# box (bx,by)-(bx+11,by+6); interior x bx+1..bx+10, y by+1..by+5
# Startup: @ -> `1023` -> M -> 0 -> ^, then west into the receive loop.
# DATA child: south from Y, east through `15`, send, then halt.
EMIT_ROWS = [
    "> sv      ",
    "Y&r<     <",
    ">  `15`sH ",
    "          ",
    "@`1023`M0^",
]
EMIT_W: int = 12
EMIT_H: int = 7
EMIT_OUT_ADDR: tuple[int, int] = (3, -1)
EMIT_OUT_DATA: tuple[int, int] = (8, 7)
EMIT_IN_P: tuple[int, int] = (2, 7)
