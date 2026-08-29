"""Generate the narrow safe stack with separate push and pop climbs."""

from pathlib import Path

from brackets_stack3_local_sentinel_gen import build as build_local

ROOT = Path(__file__).resolve().parent.parent


def build() -> list[str]:
    grid = [list(row) for row in build_local()]
    assert grid[3][1] == " " and grid[4][1] == " "
    grid[3][1] = ">"
    grid[4][1] = "^"
    return ["".join(row) for row in grid]


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
    out = ROOT / "rooms" / "brackets-stack3-dual-climb" / "base.room"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_room())
    print(f"wrote {out} (10x11 including walls)")
    audit()
