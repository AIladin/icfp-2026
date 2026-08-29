"""brackets: a three-stage pipeline, one room per stage.

    I --a--> D --c--> C --e--> N --f--> O

D  decoder   A/B/BP all free, so `M 5 W }` gives t = c >> 5 (exactly 1/2/3 for
             ()/[]/{}) in four cells.  Sends +t for an opener, -t for a closer,
             0 once for end of input.
C  stack     B = S, bijective base 3 (depth 32 -> 3^33/2, no overflow).
             push  `+ + + M`;  pop `W X + M 3 W / W X`.
             The floored remainder *is* the verdict: 0 on a match, 1 or 2 on a
             mismatch, so neither pop arm loads a constant.
N  counter   B = i, owns the output pipe.  0 = ok (i += 1), > 0 = emit i,
             < 0 = emit 0.  C seeds one ok before its loop, so an offence at
             character j is read while i == j and the emit is plain `W s H`.

Nothing is gated: D streams codes and never waits, so the per-character cost is
max(D, C, N) rather than their sum.

The one trick worth naming: **the opener/closer test is a second `x` on the
same backpack bit**, not a second subtree.  `b x` splits '(' off on bit0; the
other arm shifts once so that bit0 of the backpack is now bit1 of c, which is 1
for [ { and 0 for ) ] }.  The '(' arm shifts *three* times instead (40 >> 3 = 5,
bit0 = 1 = "opener"), so both arms rejoin one shared `M 5 W }` lane and one
final `x` sorts all six characters.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "programs" / "brackets9.man"
CASES = HERE.parent / "cases-brackets.json"

# ---------------------------------------------------------------------------
# Rooms are ASCII blocks, walls included.  Pipe markers sit on the cell just
# outside the wall: lowercase starts a pipe, its uppercase twin ends it.
# ---------------------------------------------------------------------------

# Room D -- decoder.
#
#   interior            what happens
#   (3,0) >             converge: every arm comes back here heading east
#   (3,1) q  (3,2) a    loop test; BP == 0 -> straight east to the end stub
#   (3,3..5) 0 s H      end of input: send code 0 and halt
#   (2,2) r (1,2) b     read the character, backpack it
#   (0,2) x             bit0: 1 -> east (main), 0 -> west ('(')
#   main  (0,3) ]       one shift, then down col 8 into the lane
#   '('   (0,1) ] ...   two more shifts, then into the same lane
#   lane  M 5 W } x     t in A, then bit0 of the backpack picks the arm
D_ROOM = [
    "+------------+",
    "|] ]x]     ] |",
    "|v  b      v |",
    "|>  r      < |",
    "|>qa0sH      |",
    "|            |",
    "+------------+",
]

C_ROOM = [
    "+---+",
    "|@  |",
    "+---+",
]

N_ROOM = [
    "+---+",
    "|@  |",
    "+---+",
]


def emit(blocks: list[tuple[int, int, list[str]]]) -> str:
    cells: dict[tuple[int, int], str] = {}
    for r0, c0, block in blocks:
        for dr, line in enumerate(block):
            for dc, ch in enumerate(line):
                key = (r0 + dr, c0 + dc)
                if ch == " ":
                    cells.setdefault(key, " ")
                    continue
                if key in cells and cells[key] not in (" ", ch):
                    raise ValueError(f"overwrite at {key}: {cells[key]!r} -> {ch!r}")
                cells[key] = ch
    rows = max(r for r, _ in cells) + 1
    cols = max(c for _, c in cells) + 1
    return (
        "\n".join(
            "".join(cells.get((r, c), " ") for c in range(cols)).rstrip()
            for r in range(rows)
        )
        + "\n"
    )


def main() -> None:
    text = emit([(0, 0, D_ROOM)])
    OUT.write_text(text)
    print(text, end="")
    subprocess.run(
        ["lmr", "check", str(OUT), "--ephemeral-pipes"],
        check=False,
    )


if __name__ == "__main__":
    main()
    sys.exit(0)
