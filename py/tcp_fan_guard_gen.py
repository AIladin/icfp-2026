"""Generate the tcp H2 ordered event guard.

Positive reader events are packet values: forward them and increment ``want`` in B.
Non-positive writer events are ``-seq``: reject when ``seq - want >= 16``.
The guard is the sole output producer, so the judge's round gate orders every previous
reader event before the next round's writer event without relying on a pipe race.
"""

from pathlib import Path

W = 15
H = 11


def build() -> str:
    g = [[" " for _ in range(W)] for _ in range(H)]
    for x in range(1, W - 1):
        g[1][x] = g[H - 1][x] = "-"
    for y in range(2, H - 1):
        g[y][0] = g[y][W - 1] = "|"
    for y, x in ((1, 0), (1, W - 1), (H - 1, 0), (H - 1, W - 1)):
        g[y][x] = "+"

    # MAIN. Positive values turn south, zero-seq walks into its return, and negative seq turns
    # north into the loss check. This uses all three X exits without conflating negative with zero.
    for x, ch in enumerate("@>RXv", start=1):
        g[4][x] = ch

    # Negative sequence arm: recover seq, compare seq-want, and test whether the gap is >= 16.
    g[3][4] = ">"
    for x, ch in enumerate("N-b]]]]av", start=5):
        g[3][x] = ch

    # Loss arm, reached northbound from a: emit -1 and retire the guard.
    for x, ch in zip(range(12, 7, -1), "<1NsH", strict=True):
        g[2][x] = ch

    # Positive value arm: output first, then B = want + 1.
    for y, ch in zip(range(5, 9), "s1+M", strict=True):
        g[y][4] = ch

    # All successful arms return to the R through the common bottom/west corridor.
    for x in range(3, 14):
        g[9][x] = "."
    for x in (4, 5, 13):
        g[9][x] = "<"
    g[9][2] = "^"
    for y in range(5, 9):
        g[y][2] = "."
    g[4][2] = ">"

    # Two incoming event ports (R intentionally merges them), one outgoing judge port.
    g[0][3] = "W"
    g.append(list(" " * 4 + "o" + " " * (W - 5)))
    lines = [("R" if y == 4 else " ") + "".join(row).rstrip() for y, row in enumerate(g)]
    return "\n".join(lines) + "\n"


def audit() -> None:
    print("tcp-fan-guard binding audit")
    print("R at room (4,3) -> ANY incoming reader/writer event port (intentional merge)")
    print("s value at room (5,4) -> sole output o")
    print("s loss at room (2,9) -> sole output o")
    print("ordering: guard is sole judge-output producer; next-round input is withheld until output lands")


if __name__ == "__main__":
    out = Path(__file__).parents[1] / "rooms" / "tcp-fan-guard" / "base.room"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build())
    audit()
    print(f"wrote {out}")
