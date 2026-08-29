"""Stage 2 — the flood core on its own, driven by a throwaway sequencer.

Input: 257 ring tokens (the 256 cells then the marker, whose value is `w+1` for the
first flood lap).  Output: the ring dumped token by token, so the distance field can
be diffed against the Python model.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "plotter_gen")
from canvas import Canvas  # noqa: E402

from .place import solve  # noqa: E402
from .rooms import FLG, FLG_INIT, TST, TST_INIT, UPD, UPD_INIT, WIN, Room, c, L  # noqa: E402

# the flood lap: forward every token, and bump the marker so FLG sees the next
# frontier constant.  `N` up front makes the marker the only NEGATIVE value, which is
# what XLOOP's exit arm tests.
LAP_FLOOD = (
    [c(".")] * 16 + [c("r"), c("N")],
    {"+": [c("N"), c("s")], "0": [c("s")], "-": [c("N"), c("M"), L(1), c("+"), c("s")]},
)

NOP = [c(".")]


TSEQ_INIT = [
    L(257),
    c("b"),
    ("DO", [c("r"), c("s")]),
    L(16),
    c("b"),
    ("DO", NOP * 8 + [c("r")]),
    L(64),
    c("b"),
    ("DO", [("XLOOP", LAP_FLOOD)]),
]
TSEQ_BODY = [c(".")] * 26 + [c("r"), c("s")]

PIPES = {
    "seq": ["i", "p", "n", "n", "p", "p", "p", "n", "o"],
    "flg": ["q", "p", "q", "u", "f"],
    "upd": ["q", "n", "t", "u", "n", "t", "t", "n"],
    "win": ["f", "g"],
    "tst": ["g", "t"],
}
ENDS = {
    "seq": {"i": "in", "n": "in", "p": "out", "o": "out"},
    "flg": {"p": "in", "q": "out", "u": "out", "f": "out"},
    "upd": {"q": "in", "t": "in", "u": "in", "n": "out"},
    "win": {"f": "in", "g": "out"},
    "tst": {"g": "in", "t": "out"},
}
LETTER = {k: k for k in "pqnufgtio"}
SIDES = {
    "seq": {"i": "n", "o": "s", "p": "n", "n": "w"},
    "flg": {"p": "n", "q": "w", "u": "s", "f": "s"},
    "win": {"f": "n", "g": "e"},
    "tst": {"g": "w", "t": "n"},
    "upd": {"q": "w", "u": "n", "t": "s", "n": "s"},
}


def place(cv, name, room):
    names = PIPES[name]
    if len(names) != len(room.ports):
        raise ValueError(f"{name}: {len(names)} labels vs {len(room.ports)} ports {room.ports}")
    groups = {"in": [], "out": []}
    for pipe, (ch, x, y) in zip(names, room.ports):
        groups["in" if ch in "rRUq" else "out"].append((pipe, x, y))
    out = {}
    for kind, ports in groups.items():
        if not ports:
            continue
        assign = solve(
            room.x0, room.y0, room.x1, room.y1, ports,
            banned=set(out.values()), sides=SIDES[name],
        )
        for pipe, pos in assign.items():
            out[pipe] = pos
            letter = LETTER[pipe]
            cv.put(*pos, letter.upper() if ENDS[name][pipe] == "in" else letter)
    return out


def build() -> str:
    cv = Canvas(420, 240)
    rooms = {}
    for name, (init, body, width, depth, px, py) in {
        "seq": (TSEQ_INIT, TSEQ_BODY, 60, 2, 10, 20),
        "flg": (FLG_INIT, FLG, 34, 1, 160, 20),
        "win": (None, WIN, 14, 1, 160, 120),
        "tst": (TST_INIT, TST, 20, 1, 280, 120),
        "upd": (UPD_INIT, UPD, 26, 1, 300, 20),
    }.items():
        rooms[name] = Room(cv, px, py, width, init=init, body=body, depth=depth)
    # input room
    cv.room(120, 4, 122, 6)
    cv.put(121, 5, "I")
    cv.put(121, 7, "i")
    # output room
    cv.room(60, 200, 62, 202)
    cv.put(61, 201, "O")
    cv.put(61, 199, "O")
    for name, r in rooms.items():
        place(cv, name, r)
    return cv.render()


if __name__ == "__main__":
    open(sys.argv[1], "w").write(build())
