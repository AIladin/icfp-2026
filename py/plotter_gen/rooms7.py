"""Room interiors for the narrow split-EMIT plotter candidate.

EMIT's startup omits the zero overwritten by its first receive. Its return column
and the DATA worker move left, removing another interior column.
"""

from rooms5 import *  # noqa: F403

# box (bx,by)-(bx+10,by+6); interior x bx+1..bx+9, y by+1..by+5
# Startup: @ -> `1023` -> M -> ^, then west into the receive loop. Its first `r`
# overwrites A, so the old explicit zero was unobservable.
# DATA child: south from Y, east through `15`, send, then halt.
EMIT_ROWS = [
    "> sv     ",
    "Y&r<    <",
    "> `15`sH ",
    "         ",
    "@`1023`M^",
]
EMIT_W: int = 11
EMIT_H: int = 7
EMIT_OUT_ADDR: tuple[int, int] = (3, -1)
EMIT_OUT_DATA: tuple[int, int] = (7, 7)
EMIT_IN_P: tuple[int, int] = (2, 7)
