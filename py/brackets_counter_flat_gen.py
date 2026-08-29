"""Generate and audit the three-row zero-success brackets counter."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build() -> list[str]:
    return [
        "vM+1<    ",
        " Hs0Xv   ",
        "> @r^>WsH",
    ]


def render_room() -> str:
    lines = [" +---------+"]
    for r, row in enumerate(build()):
        west = "E" if r == 2 else " "
        east = "f" if r == 2 else ""
        lines.append(f"{west}|{row}|{east}")
    lines.append(" +---------+")
    return "\n".join(lines) + "\n"


def audit() -> None:
    for r, row in enumerate(build()):
        for c, ch in enumerate(row):
            if ch in "qrs":
                net = "counter.feed" if ch in "qr" else "counter.out"
                direction = "input" if ch in "qr" else "output"
                print(f"{ch} ({r},{c}) -> {net}; sole {direction} net")


if __name__ == "__main__":
    out = ROOT / "rooms" / "brackets-counter-flat" / "base.room"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_room())
    print(f"wrote {out} (11x5 including walls)")
    audit()
