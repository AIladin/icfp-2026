"""Generate and audit the brackets decoder that injects a +1 stack sentinel."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build() -> list[str]:
    return [
        ">0sH",
        "d5Mv",
        "q@vr",
        "^<r~",
        "ss1*",
        "-^<}",
        "^~/<",
    ]


def render_room() -> str:
    lines = ["+----+"]
    for r, row in enumerate(build()):
        east = "A" if r == 1 else "c" if r == 4 else ""
        lines.append(f"|{row}|{east}")
    lines.append("+----+")
    return "\n".join(lines) + "\n"


def audit() -> None:
    for r, row in enumerate(build()):
        for c, ch in enumerate(row):
            if ch in "qrs":
                net = "decode.feed" if ch in "qr" else "decode.out"
                direction = "input" if ch in "qr" else "output"
                print(f"{ch} ({r},{c}) -> {net}; sole {direction} net")


if __name__ == "__main__":
    out = ROOT / "rooms" / "brackets-decoder-seed1" / "base.room"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_room())
    print(f"wrote {out} (6x9 including walls)")
    audit()
