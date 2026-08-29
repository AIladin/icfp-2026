"""Pack the 1,977-digit history stream into an 81x81 machine.

The 82x82 server program already had enough payload density for an 81-column drum: both widths
carry 30 base-133 digits per row.  The missing row was structural.  EXP's phrase-unpack loop used
separate return rows for "repeat" and "done".  Negating the quotient before its X sends repeat
north into the otherwise empty row above the loop, leaving one south return row for done, direct
characters, and years.  EXP becomes 43x11 internally instead of 44x12.

YEAR keeps its proven room logic but moves up one row.  The output room moves west of DEC so it no
longer occupies YEAR's new top row.  No shared tooling is involved.
"""

from __future__ import annotations

import json
from pathlib import Path

from history_gen2 import (
    EXP_MAP,
    RELAY_MAP,
    dec_map,
    drum,
    room_map,
    year_room,
)
from memory_gen import Canvas


def compact_exp_map() -> list[str]:
    """The existing EXP with its two phrase-unpack return rows folded into one."""
    rows = [list(row[:43]) for row in EXP_MAP[:11]]

    # The one-time ring seed and a real year both descend at x=42.  Distinguish them in the common
    # return without another row: seed leaves A=0; a real year negates back to positive.  An X on
    # the lower row sends only the positive value north through a three-cell `s` spur.
    rows[0][38] = "0"
    rows[6][41] = "N"
    rows[6][42] = "v"

    # Old loop tail on row 9 was `... W X v`: positive quotient turned south to a repeat
    # lane, while zero continued and dropped to a second return lane.  `b a` branches north on a
    # nonzero quotient without changing A; zero falls straight through.  Row 8 is empty from x=4
    # through x=23, so it is the repeat lane for free, and x=3 already drops onto the loop head.
    for x in range(13, 16):
        rows[9][x] = " "
    rows[9][13] = "b"
    rows[9][14] = "a"
    rows[9][15] = "v"
    rows[8][14] = "<"

    # The sole lower row is now the common return.  A finished phrase drops at x=15; a direct
    # character drops at x=20; a year walks west after its send at x=21.  All join MAIN's bus
    # at x=2.  The old x=3 riser belonged to the repeat lane and is gone.
    for x in (3, 13, 14, 21):
        rows[10][x] = " "
    # Keep the spur east of x=20: direct characters descend through that column after their own
    # send, and sharing it would emit each one twice.
    rows[9][21] = "v"
    rows[9][22] = "s"  # one column farther west breaks the tie with ring_out
    rows[9][23] = " "
    rows[9][24] = "N"  # YEAR expects the negative marker, after X tested its positive form
    rows[9][25] = "<"
    rows[10][15] = "<"
    rows[10][20] = "<"
    rows[10][21] = "<"
    rows[10][25] = "X"
    rows[10][42] = "<"  # year branch and one-time seed both descend at x=42

    return ["".join(row) for row in rows]


COMPACT_EXP = compact_exp_map()


def build(digits: list[int], base: int = 133, side: int = 81) -> str:
    c = Canvas()
    drum_h = drum(c, side - 2, digits, base)
    assert drum_h == 68, drum_h

    top = drum_h
    dec_x = 4
    exp_x = 27
    year_x = 3
    relay_x = 74

    # OUTPUT is west of DEC.  YEAR can then rise to y=73 without sharing its top wall with O.
    c.room(0, top + 1, 3, 3)
    c.put(1, top + 2, "O")
    room_map(c, dec_x, top, dec_map(base))
    room_map(c, exp_x, top, COMPACT_EXP)
    room_map(c, year_x, top + 5, year_room(22))
    room_map(c, relay_x, top + 9, RELAY_MAP)

    # DRUM and DEC touch vertically, so the two-cell pipe rounds DEC's north-east corner and
    # enters its east wall.  Both rooms have only one pipe in that direction.
    c.pipe([(dec_x + 16, drum_h - 1), (dec_x + 16, top + 1), (dec_x + 15, top + 1)])

    # DEC -> EXP across the clear horizontal gap.  EXP's stream and ring inputs remain on
    # opposite walls, preserving the submitted layout's binding algebra.
    c.pipe([(dec_x + 15, top + 2), (exp_x, top + 2)])

    # EXP -> YEAR: leave EXP west, turn once, and enter YEAR's north wall.
    c.pipe([(exp_x, top + 4), (year_x + 22, top + 4), (year_x + 22, top + 5)])

    # YEAR -> OUTPUT: leave west, turn north, and enter O through its bottom wall.
    c.pipe([(year_x, top + 7), (1, top + 7), (1, top + 3)])

    # RELAY -> EXP is the two-cell return at the common bottom row.
    exp_e = exp_x + len(COMPACT_EXP[0]) + 1
    c.pipe([(relay_x, top + 12), (exp_e, top + 12)])

    # EXP -> RELAY is also the ring's storage.  This is the submitted program's safe
    # boustrophedon shifted one column left: 70+ cells for 40 phrases plus the year slot.
    points = [(exp_e, top)]
    x_left, x_right = exp_e + 1, side - 1
    points.append((x_right, top))
    for y in range(top + 1, top + 8):
        points.append((x_right if y % 2 == 1 else x_left, y))
        points.append((x_left if y % 2 == 1 else x_right, y))
    # End left of RELAY, descend outside its wall, then enter through the west side.
    points.extend([(x_left, top + 10), (relay_x, top + 10)])
    c.pipe(points)

    return c.render()


def load_text(path: Path) -> str:
    data = json.loads(path.read_text())
    return "".join(chr(int(value)) for value in data[0]["rounds"][0]["out"])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--digits", type=Path, default=Path("history_digits_1977.txt"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    source = build([int(value) for value in args.digits.read_text().split()])
    if args.out:
        args.out.write_text(source)
    else:
        print(source, end="")
