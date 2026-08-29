"""West-pass ECHO decrement experiment for the compact 44x44 plotter."""

from rooms11 import *  # noqa: F403

# BP starts at three. Each positive east-end `a` turns north; `m` then decrements
# on the west pass. After three west passes BP is zero, so the fourth east pass exits.
ECHO_ROWS = [
    "  v<            ",
    "   ^sRsR<       ",
    "        ^sRsRsR<",
    "               ^",
    "  >@3bRsv      ^",
    " v    sR<      ^",
    " v sRsRsRsR  m<^",
    " >RsRsRsRsRsRsa^",
]
ECHO_W: int = 18
ECHO_H: int = 10
