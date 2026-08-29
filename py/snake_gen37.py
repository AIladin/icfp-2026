"""Snake experiment: bypass input around the ring and remove HUB's input commands.

This is deliberately layered on snake_gen36: the BRAIN logic is unchanged except that input
values arrive on a second pipe directly from the input-forwarder man in HUB.  It tests the cheap
half of the one-lap plan before adding the delayed-tail Q field.
"""

from __future__ import annotations

import copy

import snake_gen36 as base
from plotter_gen.canvas import Canvas


# Rewrite only the input protocol.  The forwarder sends [sx, 16*sy] for INIT and thereafter
# [V] or [1, fx, 16*fy].  Those values therefore have exactly the shape HUB's old commands made.
blocks = copy.deepcopy(base.BLOCKS)
by_name = {b[0]: i for i, b in enumerate(blocks)}


def replace(name: str, block: tuple) -> None:
    blocks[by_name[name]] = block


replace(
    "INIT",
    (
        "INIT",
        "2 N s r N M s L17 N s r N + s M 2 - N M 1 N s W s",
        "j",
        ("INITB",),
    ),
)
replace(
    "INITB",
    (
        "INITB",
        "W 0 s 1 s W s W s 9 s 1 s 0 s",
        "j",
        ("MAIN",),
    ),
)
replace(
    "MAIN",
    (
        "MAIN",
        "1 M r -",
        "x",
        ("TCHK", ("r s r s", "FRUITA"), ("M 1 W", "DIRA")),
    ),
)

# Strip the old request command after frame commits.  MAIN now blocks directly on the forwarder.
i = by_name["FRUITA2"]
n, src, kind, tg = blocks[i]
assert src.endswith(" 2 s"), src
blocks[i] = (n, src[:-4], kind, tg)

i = by_name["TAP"]
n, src, kind, tg = blocks[i]
old = "1 s 0 s s 2 s r s"
assert old in src, src
blocks[i] = (n, src.replace(old, "1 s 0 s s r s", 1), kind, tg)

base.BLOCKS = blocks


def hub(c: Canvas, X: int, Y: int) -> None:
    """Two men in one 19x18 room.

    The upper man is the gen36 ring router, with command 1 (DRAW) as its only positive command.
    The lower man forwards contest input directly to BRAIN and scales every y coordinate by 16.
    Keeping both men in one room spends the empty band below HUB instead of adding a room or rows.
    """
    c.room(X, Y, X + 18, Y + 17)

    def p(x: int, y: int, ch: str) -> None:
        c.put(X + x, Y + y, ch)

    def t(x: int, y: int, text: str) -> None:
        for k, ch in enumerate(text):
            p(x + k, y, ch)

    # Ring router. Negative record data echoes; zero marker echoes; every positive token is the
    # DRAW prefix and forwards the next ring value.  The old 2/3 input arms are gone.
    p(1, 1, "v")
    p(1, 2, ">")
    for y in range(3, 8):
        p(1, y, "^")
    p(2, 7, "@")
    p(3, 7, "<")
    t(2, 1, "s<<")
    t(2, 2, "rX")
    p(4, 2, "^")
    # Positive arm: read one payload, walk east to the feed pin, then return west and up.
    p(3, 3, ">")
    p(4, 3, "r")
    p(15, 3, "v")
    p(15, 4, "s")
    p(15, 5, "<")

    # Input forwarder, kept in the east half so all its sends bind to the direct-output pin.
    # Initial input is sx,sy; later rounds are V followed by fx,fy iff V=1.  The fruit arm is
    # written backwards on row 14 because it is walked west: physically `s{W4Mrsr` executes
    # `r s r M 4 W { s`.
    p(8, 15, "@")
    t(9, 15, "rsrM4W{s")
    p(17, 15, "^")
    p(17, 11, "<")
    p(9, 12, ">")
    t(10, 12, "rMs1-X")
    p(15, 11, "<")
    p(9, 11, "v")
    # Fruit (zero) falls south and walks this mirrored code west.
    p(16, 12, "v")
    p(16, 13, "<")
    t(8, 13, "s{W4Mrsr")
    p(7, 13, "^")
    p(7, 10, ">")
    p(9, 10, "v")


base.hub = hub

# The combined HUB occupies the old HUB+IN band.  Its pins are routed explicitly below.
base.HUBX, base.HUBY = 1, 5
base.DRWX, base.DRWY = 3, 24
base.DSPX, base.DSPY = 2, 37
base.BAND = 23
base.ROWS = 56


def build(audit: bool = False) -> str:
    b = base.build_brain()
    B = b.width
    c = Canvas(B + base.BAND, max(b.height, base.ROWS))
    b.blit(c)
    hub(c, B + 2, 5)
    base.draw(c, B + 3, 24)
    c.display(B + 2, 37, B + 19, 54)

    # Raw contest input room, below DRAW and above the display.
    c.room(B + 19, 33, B + 21, 35)
    c.put(B + 20, 34, "I")

    def px(pts, final, want=None):
        cells = base.route([(B + x, y) for x, y in pts])
        if want is not None:
            assert len(cells) == want, (want, len(cells))
        c.pipe(cells, final=final)

    # Ring capacity is unchanged: 61 + 13 = the shipped 69 + 5.
    px([(0, 2), (14, 2), (14, 1), (1, 1), (1, 0), (15, 0), (15, 4), (7, 4)],
       final=(0, 1), want=56)
    px([(4, 4), (4, 3), (0, 3), (0, 12), (1, 12), (1, 13), (0, 13)],
       final=(-1, 0), want=18)

    # I -> the forwarder man's `r`s, on HUB's right wall below the router core.
    px([(20, 32), (21, 32), (21, 15)], final=(-1, 0))
    # Forwarder -> BRAIN at MAIN's row.  HUB starts at B+1, so x=B is not a safe vertical
    # corridor; leave from bottom column 15, step west to x=B, then approach BRAIN horizontally.
    px([(18, 23), (1, 23), (1, 9), (0, 9)], final=(-1, 0))

    # Router -> DRAW.  Its top pin is well east of both ring pins; it steps north into a free
    # channel, wraps east around HUB, and enters DRAW's right wall.
    px([(12, 4), (12, 3), (22, 3), (22, 26), (14, 26)], final=(-1, 0))
    px([(5, 23), (5, 22), (18, 22), (18, 36)], final=(0, 1), want=29)
    px([(14, 27), (15, 27), (15, 35), (1, 35), (1, 46)], final=(1, 0), want=35)
    px([(5, 32), (5, 34), (0, 34), (0, 55), (11, 55)], final=(0, -1), want=40)
    return c.render()


if __name__ == "__main__":
    print(build(), end="")
