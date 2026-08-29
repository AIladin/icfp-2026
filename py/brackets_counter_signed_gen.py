"""Generate and audit the seedless signed-verdict brackets counter."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build() -> list[str]:
    return [
        "  Hs< ",
        "Hs+1Xv",
        " @>r^+",
        "  ^<M<",
    ]


def render_room() -> str:
    lines = [" " + "+" + "-" * 6 + "+"]
    for r, row in enumerate(build()):
        west = "E" if r == 2 else " "
        east = "f" if r == 1 else ""
        lines.append(west + "|" + row + "|" + east)
    lines.append(" " + "+" + "-" * 6 + "+")
    return "\n".join(lines) + "\n"


def audit() -> None:
    for r, row in enumerate(build()):
        for c, ch in enumerate(row):
            if ch in "qrs":
                net = "counter.feed" if ch in "qr" else "counter.out"
                direction = "input" if ch in "qr" else "output"
                print(f"{ch} ({r},{c}) -> {net}; sole {direction} net")


if __name__ == "__main__":
    out = ROOT / "rooms" / "brackets-counter-signed" / "base.room"
    out.parent.mkdir(parents=True, exist_ok=True)
    for variant in out.parent.glob("*.room"):
        if variant != out:
            variant.unlink()
    out.write_text(render_room())
    print(f"wrote {out} (8x6 including walls)")
    audit()
