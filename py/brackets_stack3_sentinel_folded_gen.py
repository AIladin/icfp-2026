"""Generate the seeded-sentinel stack with an arithmetic-cancelled pop return."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build() -> list[str]:
    g = [[" "] * 9 for _ in range(9)]

    def put(r: int, c: int, ch: str) -> None:
        assert g[r][c] == " ", (r, c, g[r][c], ch)
        g[r][c] = ch

    # Shared receive and signed-token dispatch. Decoder's synthetic +1 pushes
    # the sentinel and emits the counter's initial zero verdict.
    put(3, 0, ">")
    put(3, 1, "@")
    put(3, 3, "r")
    put(3, 4, "X")
    for r in range(4, 8):
        put(r, 0, "^")

    # Push t: S <- 3S+t, emit zero success, return on the west.
    put(4, 4, "+")
    put(5, 4, "+")
    put(6, 4, "+")
    put(7, 4, "<")
    put(7, 3, "M")
    put(7, 2, "0")
    put(7, 1, "s")

    # Pop -t: reject S-t <= 0, otherwise divide and send the remainder.
    put(2, 4, "+")
    put(1, 4, "X")
    put(1, 3, "N")
    put(1, 2, "s")
    put(1, 1, "H")
    put(0, 4, ">")
    put(0, 5, "1")
    put(0, 6, "s")
    put(0, 7, "H")
    put(1, 5, "M")
    put(1, 6, "3")
    put(1, 7, "W")
    put(1, 8, "v")
    put(2, 8, "/")
    put(3, 8, "W")
    put(4, 8, "s")
    put(5, 8, "<")

    # End: compute S-1 down c5 and fan both verdicts into one floor send.
    put(3, 5, "v")
    put(4, 5, "1")
    put(5, 5, "-")
    put(6, 5, "N")
    put(7, 5, ">")
    put(7, 6, "X")
    put(6, 6, "H")
    put(7, 7, "-")
    put(7, 8, "v")
    put(8, 8, "<")
    put(8, 7, "<")
    put(8, 6, "<")
    put(8, 5, "s")
    put(8, 4, "H")

    # A matching pop returns west through `- +`, cancelling back to zero while
    # preserving quotient B. Offending remainders were already sent.
    return ["".join(row) for row in g]


def render_room() -> str:
    lines = [" +---------+"]
    for r, row in enumerate(build()):
        west = "C" if r == 3 else " "
        east = "e" if r == 4 else ""
        lines.append(f"{west}|{row}|{east}")
    lines.append(" +---------+")
    return "\n".join(lines) + "\n"


def audit() -> None:
    for r, row in enumerate(build()):
        for c, ch in enumerate(row):
            if ch in "qrs":
                net = "stack.feed" if ch in "qr" else "stack.verdict"
                direction = "input" if ch in "qr" else "output"
                print(f"{ch} ({r},{c}) -> {net}; sole {direction} net")


if __name__ == "__main__":
    out = ROOT / "rooms" / "brackets-stack3-sentinel-folded" / "base.room"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_room())
    print(f"wrote {out} (11x11 including walls)")
    audit()
