"""Eighteen-column ECHO experiment for the 44x44 plotter floorplan.

The counted ring moves one column left and the router/return move inward. Pipe pins
stay fixed so this can be audited independently on the server-baseline floorplan.
"""

from rooms8 import *  # noqa: F403

ECHO_ROWS = [
    "  v<            ",
    "   ^sRsR<       ",
    "        ^sRsRsR<",
    "               ^",
    "  >@4bRsv      ^",
    "v     sR<      ^",
    "v  sRsRsRsR   <^",
    ">RsRsRsRsRsRsma^",
]
ECHO_W: int = 18
ECHO_H: int = 10
