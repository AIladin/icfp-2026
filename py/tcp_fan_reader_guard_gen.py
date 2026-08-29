"""Generate the cyclic blocking reader room for the tcp 16-pipe fan experiment.

The active man blocks directly on the pipe for ``want mod 16``. A received value is sent to the
ordered guard, increments the reader's local position in B, and walks to the next slot. The
side/bottom corridor wraps slot 15 back to slot 0.
"""

from pathlib import Path

SLOTS = 16
W = 11
H = 22
PORTS = "ABCDEFGHIJKLMNOP"


def build() -> str:
    rows = [[" " for _ in range(W + 1)] for _ in range(H)]  # extra west marker column

    # Room border occupies x=1..10; x=0 is available for west-wall pin markers.
    for x in range(2, W):
        rows[0][x] = rows[H - 1][x] = "-"
    rows[0][1] = rows[0][W] = rows[H - 1][1] = rows[H - 1][W] = "+"
    for y in range(1, H - 1):
        rows[y][1] = rows[y][W] = "|"

    # Spawn joins the same wrap corridor used after slot 15.
    rows[1][2] = "v"
    rows[1][3] = "@"
    rows[1][10] = "<"
    for y in (2, 3):
        rows[y][2] = "v"
        rows[y][10] = "^"

    for i in range(SLOTS):
        y = i + 4
        rows[y][0] = PORTS[i]
        if i % 2 == 0:
            rows[y][2] = ">"
            for x, ch in zip(range(3, 8), "rs1+M", strict=True):
                rows[y][x] = ch
            rows[y][9] = "v"
        else:
            rows[y][9] = "<"
            for x, ch in zip(range(8, 3, -1), "rs1+M", strict=True):
                rows[y][x] = ch
            rows[y][2] = "v"

    # Slot 15 falls into this corridor, rises at the east, and re-enters slot 0 from above.
    rows[20][2] = ">"
    rows[20][10] = "^"
    for x in range(3, 10):
        rows[20][x] = "."
    for y in range(4, 20):
        rows[y][10] = "^"

    # The sole outgoing guard pin stays on the south wall, leaving the fan wall untouched.
    rows.append(list(" " * 7 + "r" + " " * 4))
    return "\n".join("".join(row).rstrip() for row in rows) + "\n"


def audit() -> None:
    print("tcp-fan-reader binding audit")
    for i in range(SLOTS):
        y = i + 4
        x = 3 if i % 2 == 0 else 8
        print(f"r slot{i:02}: room ({y},{x}) -> incoming port {PORTS[i]} (same fan row, margin 1)")
        sx = 4 if i % 2 == 0 else 7
        print(f"s slot{i:02}: room ({y},{sx}) -> sole guard output r")
    print("capacity: slot pipes declare min=2,max=40; uniqueness permits one live packet per slot")


if __name__ == "__main__":
    out = Path(__file__).parents[1] / "rooms" / "tcp-fan-reader-guard" / "base.room"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build())
    audit()
    print(f"wrote {out}")
