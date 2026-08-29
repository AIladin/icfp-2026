"""Generate and audit the fast zero-verdict base-3 sentinel stack room."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build() -> list[str]:
    g = [[" "] * 9 for _ in range(9)]

    def put(r: int, c: int, ch: str) -> None:
        assert g[r][c] == " ", (r, c, g[r][c], ch)
        g[r][c] = ch

    # Shared receive and signed-token dispatch. The decoder first injects +1,
    # so the ordinary push initializes sentinel S=1 and emits the counter seed.
    put(3, 0, ">")
    put(3, 1, "@")
    put(3, 3, "r")
    put(3, 4, "X")

    # Push t: S <- 3S+t, emit zero success, return up the west edge.
    put(4, 4, "+")
    put(5, 4, "+")
    put(6, 4, "+")
    put(7, 4, "<")
    put(7, 3, "M")
    put(7, 2, "0")
    put(7, 1, "s")
    for r in range(4, 8):
        put(r, 0, "^")

    # Pop -t: reject S-t <= 0 at the sentinel, otherwise divide by three.
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
    for r in range(5, 8):
        put(r, 8, "v")

    # End: S-1 > 0 is n+1; S-1 == 0 derives balanced marker -1.
    put(3, 5, "1")
    put(3, 6, "-")
    put(3, 7, "v")
    put(4, 7, "N")
    put(5, 7, "X")
    put(5, 6, "s")
    put(5, 5, "H")
    put(6, 7, "-")
    put(7, 7, "s")

    # Positive-pop and balanced returns share the floor.
    put(8, 0, "^")
    for c in range(1, 9):
        put(8, c, "<")

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
    out = ROOT / "rooms" / "brackets-stack3-sentinel-zero" / "base.room"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_room())
    print(f"wrote {out} (11x11 including walls)")
    audit()
