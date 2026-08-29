"""Generate the narrow seeded-sentinel stack with a shared pop/end division."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build() -> list[str]:
    g = [[" "] * 8 for _ in range(9)]

    def put(r: int, c: int, ch: str) -> None:
        assert g[r][c] == " ", (r, c, g[r][c], ch)
        g[r][c] = ch

    # Receive and dispatch. Decoder's synthetic +1 initializes the sentinel and
    # sends the counter seed through the ordinary push arm.
    put(3, 0, ">")
    put(3, 1, "@")
    put(3, 2, "r")
    put(3, 3, "X")
    for r in range(4, 9):
        put(r, 0, "^")

    # Push t: S <- 3S+t. The extra height replaces the old westward M tail.
    put(4, 3, "+")
    put(5, 3, "+")
    put(6, 3, "+")
    put(7, 3, "M")
    put(8, 3, "<")
    put(8, 2, "0")
    put(8, 1, "s")

    # Pop -t: reject sentinel underflow, otherwise divide and send remainder.
    put(2, 3, "+")
    put(1, 3, "X")
    put(1, 2, "N")
    put(1, 1, "s")
    put(1, 0, "H")
    put(0, 3, ">")
    put(0, 4, "1")
    put(0, 5, "s")
    put(0, 6, "H")
    put(1, 4, "M")
    put(1, 5, "3")
    put(1, 6, "v")
    put(2, 6, "W")
    put(3, 6, "/")
    put(4, 6, "<")
    put(4, 5, "W")
    put(4, 4, "s")

    # End enters the same `/` horizontally. 1-S divided by S is 0 exactly at
    # the sentinel and -1 for every unclosed stack; the remainder is 0/1.
    put(3, 4, "1")
    put(3, 5, "-")
    put(3, 7, "v")
    put(4, 7, "N")
    put(5, 7, "<")
    put(5, 6, "X")
    put(6, 6, "H")

    # Balanced goes west. Its B=0 makes the crossed push `+` harmless.
    put(5, 5, "1")
    put(5, 4, "N")
    put(5, 2, "s")
    put(5, 1, "H")
    return ["".join(row) for row in g]


def render_room() -> str:
    lines = [" +--------+"]
    for r, row in enumerate(build()):
        west = "C" if r == 3 else " "
        east = "e" if r == 4 else ""
        lines.append(f"{west}|{row}|{east}")
    lines.append(" +--------+")
    return "\n".join(lines) + "\n"


def audit() -> None:
    for r, row in enumerate(build()):
        for c, ch in enumerate(row):
            if ch in "qrs":
                net = "stack.feed" if ch in "qr" else "stack.verdict"
                direction = "input" if ch in "qr" else "output"
                print(f"{ch} ({r},{c}) -> {net}; sole {direction} net")


if __name__ == "__main__":
    out = ROOT / "rooms" / "brackets-stack3-sentinel-narrow" / "base.room"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_room())
    print(f"wrote {out} (10x11 including walls)")
    audit()
