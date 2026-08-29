"""Generate and audit the compact, depth-32-safe brackets stack room."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build() -> list[str]:
    g = [[" "] * 10 for _ in range(10)]

    def put(r: int, c: int, ch: str) -> None:
        assert g[r][c] == " ", (r, c, g[r][c], ch)
        g[r][c] = ch

    # Positive-pop return: east edge, floor, west climb into the head.
    for r in range(7, 9):
        put(r, 9, "v")
    put(9, 9, "<")
    for c in range(2, 9):
        put(9, c, "<")
    put(9, 1, "^")
    for r in (5, 6, 8):
        put(r, 1, "^")

    # Common receive and sign dispatch, entered heading east.
    put(4, 5, "r")
    put(4, 6, "X")

    # Push (+t): B <- 3B+t, send verdict zero, return on the west.
    put(5, 6, "+")
    put(6, 6, "+")
    put(7, 6, "<")
    put(7, 5, "+")
    put(7, 4, "M")
    put(7, 3, "0")
    put(7, 2, "s")
    put(7, 1, "^")

    # Pop (-t): A <- S-t, then split underflow, exact-empty, and division.
    put(3, 6, "+")
    put(2, 6, "X")
    put(2, 5, "N")
    put(2, 4, "s")
    put(2, 3, "H")

    # S-t == 0: clear B, send zero, then return west through the same M.
    put(1, 6, "M")
    put(0, 6, ">")
    put(0, 7, "0")
    put(0, 8, "s")
    put(0, 9, "v")
    put(1, 9, "<")
    for c in range(2, 9):
        if g[1][c] == " ":
            put(1, c, "<")
    put(1, 1, "v")
    put(2, 1, "v")
    put(3, 1, "v")
    put(4, 1, ">")

    # S-t > 0: fold M3W/Ws around the north-east corner.
    put(2, 7, "M")
    put(2, 8, "3")
    put(2, 9, "v")
    put(3, 9, "W")
    put(4, 9, "/")
    put(5, 9, "W")
    put(6, 9, "s")

    # End sentinel. Turn south before testing S to share the east fold.
    put(4, 7, "W")
    put(4, 8, "v")
    put(5, 8, "X")
    put(5, 7, "s")  # S>0: n+1 offence; post-send travel is irrelevant.
    put(6, 8, "1")
    put(7, 8, "N")
    put(8, 8, "s")  # S==0: negative balanced verdict.

    # Seed counter with verdict zero, then join the floor return.
    put(8, 4, "@")
    put(8, 5, "0")
    put(8, 6, "s")
    put(8, 7, "v")
    return ["".join(row[1:]) for row in g]


def render_room() -> str:
    body = build()
    lines = [" " + "+" + "-" * 9 + "+"]
    for r, row in enumerate(body):
        west = "C" if r == 4 else " "
        east = "e" if r == 3 else ""
        lines.append(west + "|" + row + "|" + east)
    lines.append(" " + "+" + "-" * 9 + "+")
    return "\n".join(lines) + "\n"


def audit() -> None:
    for r, row in enumerate(build()):
        for c, ch in enumerate(row):
            if ch in "qrs":
                net = "stack.feed" if ch in "qr" else "stack.verdict"
                direction = "input" if ch in "qr" else "output"
                print(f"{ch} ({r},{c}) -> {net}; sole {direction} net")


if __name__ == "__main__":
    out = ROOT / "rooms" / "brackets-stack3" / "base.room"
    # Remove stale generated variants: their names encode pins, not dimensions.
    for variant in out.parent.glob("*.room"):
        if variant != out:
            variant.unlink()
    out.write_text(render_room())
    print(f"wrote {out} (11x12 including walls)")
    audit()
