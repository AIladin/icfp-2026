"""Ten-column split-EMIT experiment with a folded startup path."""

from rooms8 import *  # noqa: F403

# Startup turns north after the mask literal and sets B in the old blank row.
# DATA moves its send/halt left, keeping the return column disjoint.
EMIT_ROWS = [
    "> sv    ",
    "Y&r<   <",
    ">`15`sH ",
    "       M",
    "@`1023`^",
]
EMIT_W: int = 10
EMIT_H: int = 7
