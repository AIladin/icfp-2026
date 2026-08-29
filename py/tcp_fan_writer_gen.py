"""Generate the tcp H2 writer with a Y-spawned absolute-slot address worker."""

from pathlib import Path

SLOTS = 16
W = 14
H = 22
PORTS = "abcdefghijklmnop"


def put(g: list[list[str]], y: int, x: int, ch: str) -> None:
    old = g[y][x]
    if old != " " and old != ch:
        raise ValueError(f"collision {(y, x)}: {old!r} vs {ch!r}")
    g[y][x] = ch


def build() -> str:
    g = [[" " for _ in range(W + 2)] for _ in range(H)]
    for x in range(2, W):
        g[0][x] = g[H - 1][x] = "-"
    for y in range(1, H - 1):
        g[y][1] = g[y][W] = "|"
    for y, x in ((0, 1), (0, W), (H - 1, 1), (H - 1, W)):
        g[y][x] = "+"

    # Initial lineage consumes n and enters MAIN. Every later carrier returns through the same drop.
    put(g, 1, 2, "@")
    put(g, 1, 3, "R")
    put(g, 1, 4, "v")
    put(g, 2, 4, ">")

    # MAIN: send -seq to GUARD while retaining seq, then read val and split. The north copy carries
    # the input loop; the south copy carries (val, BP=seq) into the address ladder.
    for x, ch in zip(range(5, 12), "rMNsWbr", strict=True):
        put(g, 2, x, ch)
    put(g, 2, 12, "Y")
    put(g, 1, 12, "<")
    for x in range(5, 12):
        if g[1][x] == " ":
            g[1][x] = "."
    put(g, 3, 12, "<")
    put(g, 3, 4, "v")

    # BP=seq. A positive test descends; zero sends val into the pipe for the current absolute slot.
    for i in range(SLOTS):
        y = 4 + i
        g[y][W + 1] = PORTS[i]
        if i % 2 == 0:
            put(g, y, 4, ">")
            if i:
                put(g, y, 5, "m")
            put(g, y, 7, "d")
            put(g, y, 8, "s")
            put(g, y, 9, "H")
        else:
            put(g, y, 7, "<")
            put(g, y, 6, "m")
            put(g, y, 4, "a")
            put(g, y, 3, "s")
            put(g, y, 2, "H")

    # seq may be 16..47. Decrement once at the wrap, then re-enter slot zero.
    put(g, 20, 4, ">")
    put(g, 20, 5, "m")
    for x in range(6, 13):
        put(g, 20, x, ".")
    put(g, 20, 13, "^")
    for y in range(3, 20):
        if g[y][13] == " ":
            g[y][13] = "."
    g[3][13] = "<"

    # One packet input, one guard event output, and the 16 fan outputs.
    g[2][0] = "Z"
    marker = " " * 4 + "q"
    return marker + "\n" + "\n".join("".join(row).rstrip() for row in g) + "\n"


def audit() -> None:
    print("tcp-fan-writer binding audit")
    print("R(n), r(seq), r(val) -> sole input Z")
    print("s guard at (2,8) -> north output q at column 4; nearest fan output is 3 cells farther")
    for i in range(SLOTS):
        y = 4 + i
        x = 8 if i % 2 == 0 else 3
        print(f"s slot{i:02}: room ({y},{x}) -> outgoing {PORTS[i]} (same east-wall fan row)")
    print("slot pipes need min=2; guard timing is encoded in the complete netlist")


if __name__ == "__main__":
    out = Path(__file__).parents[1] / "rooms" / "tcp-fan-writer" / "base.room"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build())
    audit()
    print(f"wrote {out}")
