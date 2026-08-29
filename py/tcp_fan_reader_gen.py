"""Generate the cyclic blocking reader room for the tcp 16-pipe fan experiment.

The active man blocks directly on the pipe for ``want mod 16``.  A received value is broadcast
with ``S`` to both the judge output and the writer's feedback pipe, increments ``want`` in B, and
walks to the next slot.  The side/bottom corridor wraps slot 15 back to slot 0.

This is deliberately the smallest H2 experiment: it settles whether the reader needs a q/branch
per slot.  It does not implement the writer or a complete tcp candidate.
"""

from pathlib import Path

SLOTS = 16
W = 11
H = 20
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

    for i in range(SLOTS):
        y = i + 2
        rows[y][0] = PORTS[i]
        if i % 2 == 0:
            rows[y][2] = ">"
            for x, ch in zip(range(3, 8), "rS1+M", strict=True):
                rows[y][x] = ch
            rows[y][9] = "v"
        else:
            rows[y][9] = "<"
            for x, ch in zip(range(8, 3, -1), "rS1+M", strict=True):
                rows[y][x] = ch
            rows[y][2] = "v"

    # Slot 15 falls into this corridor, rises at the east, and re-enters slot 0 from above.
    rows[18][2] = ">"
    rows[18][10] = "^"
    for x in range(3, 10):
        rows[18][x] = "."
    for y in range(2, 18):
        rows[y][10] = "^"

    # Two outgoing pins. Every S intentionally broadcasts to both, so their placement does not
    # affect instruction binding; keeping them on the south wall leaves the fan wall untouched.
    rows.append(list(" " * 5 + "q" + " " + "r" + " " * 4))
    return "\n".join("".join(row).rstrip() for row in rows) + "\n"


def audit() -> None:
    print("tcp-fan-reader binding audit")
    for i in range(SLOTS):
        y = i + 2
        x = 3 if i % 2 == 0 else 8
        print(f"r slot{i:02}: room ({y},{x}) -> incoming port {PORTS[i]} (same fan row, margin 1)")
        sx = 4 if i % 2 == 0 else 7
        print(f"S slot{i:02}: room ({y},{sx}) -> BROADCAST outputs q=output and r=feedback")
    print("capacity: every slot pipe must have min=2,max=2; one packet per absolute slot")


if __name__ == "__main__":
    out = Path(__file__).parents[1] / "rooms" / "tcp-fan-reader" / "base.room"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build())
    audit()
    print(f"wrote {out}")
