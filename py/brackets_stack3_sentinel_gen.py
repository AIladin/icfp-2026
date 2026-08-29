"""Generate and audit the compact sentinel-base-3 brackets stack room."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build() -> list[str]:
    g = [[" "] * 9 for _ in range(9)]

    def put(r: int, c: int, ch: str) -> None:
        assert g[r][c] == " ", (r, c, g[r][c], ch)
        g[r][c] = ch

    # Shared west climb and floor return.
    put(4, 0, ">")
    put(5, 0, "^")
    put(6, 0, "^")
    put(7, 0, "^")
    put(8, 0, "^")
    for c in range(1, 9):
        put(8, c, "s" if c == 7 else "<")

    # Receive signed type and dispatch: positive push, negative pop, zero end.
    put(4, 2, "r")
    put(4, 3, "X")

    # Push: S <- 3S+t; +1 verdict means one character completed.
    put(5, 3, "+")
    put(6, 3, "+")
    put(7, 3, ">")
    put(7, 4, "+")
    put(7, 5, "M")
    put(7, 6, "1")
    put(7, 8, "v")

    # Pop: S-t <= 0 is sentinel underflow; positive values divide by three.
    put(3, 3, "+")
    put(2, 3, "X")
    put(2, 2, "s")  # negative underflow is already an offence verdict
    put(2, 1, "H")
    put(1, 3, ">")
    put(1, 4, "1")
    put(1, 5, "N")
    put(1, 6, "s")  # exact sentinel underflow becomes -1
    put(1, 7, "H")
    put(2, 4, "M")
    put(2, 5, "3")
    put(2, 6, "W")
    put(2, 8, "v")
    put(3, 8, "/")
    put(4, 8, "W")
    put(5, 8, "X")
    put(5, 7, "N")
    put(5, 6, "s")
    put(5, 5, "H")
    put(6, 8, "1")

    # End: 1-S is zero iff balanced, negative iff openers remain.
    put(4, 4, "1")
    put(4, 5, "-")
    put(4, 6, "s")
    put(4, 7, "H")

    # Initialize the sentinel S=1, then join the west climb.
    put(6, 4, "@")
    put(6, 5, "1")
    put(6, 6, "M")
    put(6, 7, "<")
    return ["".join(row) for row in g]


def render_room() -> str:
    lines = [" " + "+" + "-" * 9 + "+"]
    for r, row in enumerate(build()):
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
    out = ROOT / "rooms" / "brackets-stack3-sentinel" / "base.room"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_room())
    print(f"wrote {out} (11x11 including walls)")
    audit()
