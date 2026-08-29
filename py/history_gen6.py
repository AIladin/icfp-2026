"""Combine history's direct dictionary producer and phrase expander into one room.

The dictionary man initializes the phrase ring itself, then falls into MAIN's existing bottom
return bus.  This removes the DICT -> EXP pipe and EXP's counted startup loop.  The initial room is
spacious on purpose: it isolates the semantic and binding experiment before a 13-row fold.
"""

from __future__ import annotations

from pathlib import Path
import random

import history_gen4
import history_gen5
from history_gen3 import COMPACT_EXP

SLOTS = 41


def reorder_ring_slots(
    words: list[int], payload: list[int], order: list[int]
) -> tuple[list[int], list[int]]:
    """Apply a permutation of current ring slots and preserve every relative phrase reference."""
    assert sorted(order) == list(range(40))
    new_position = {old: new for new, old in enumerate(order)}
    new_position[40] = 40
    old_head = new_head = 0
    remapped: list[int] = []
    for digit in payload:
        if digit <= 91:
            remapped.append(digit)
            continue
        old_target = (old_head + digit - 92) % SLOTS
        new_target = new_position[old_target]
        remapped.append(92 + (new_target - new_head) % SLOTS)
        old_head = (old_target + 1) % SLOTS
        new_head = (new_target + 1) % SLOTS
    return [words[index] for index in order], remapped


def six_row_order(words: list[int]) -> list[int]:
    """Put four short words in the final half-width pair and balance the three full pairs."""
    lengths = [len(str(word)) for word in words]
    final = sorted(range(40), key=lambda index: (lengths[index], index))[:4]
    remaining = [index for index in range(40) if index not in final]
    rng = random.Random(7)
    best: tuple[tuple[int, int], list[int]] | None = None
    for _ in range(100_000):
        order = rng.sample(remaining, len(remaining))
        widths = []
        for group in range(3):
            east = order[group * 12 : group * 12 + 6]
            west = list(reversed(order[group * 12 + 6 : group * 12 + 12]))
            widths.append(
                26
                + sum(
                    max(lengths[left], lengths[right])
                    for left, right in zip(east, west, strict=True)
                )
            )
        score = max(widths), sum(widths)
        if best is None or score < best[0]:
            best = score, order
    assert best is not None and best[0][0] <= 72
    return best[1] + final


def dict_rows_six(words: list[int]) -> list[str]:
    """Use three six-slot row pairs and one short three-slot tail pair."""
    assert len(words) == 40
    entries: list[tuple[int, str]] = [(word, "send") for word in words]
    entries += [(1996, "year"), (0, "stop")]
    rows: list[str] = []
    cursor = 0
    for pair, slots in enumerate((6, 6, 6, 3)):
        count = 2 * slots
        pair_entries = entries[cursor : cursor + count]
        cursor += count
        east = pair_entries[:slots]
        west = list(reversed(pair_entries[slots:]))
        specs: list[tuple[int, int]] = []
        width = 2
        for (east_value, _), (west_value, west_kind) in zip(east, west, strict=True):
            digits = max(len(str(east_value)), len(str(west_value)))
            lead = 3 if west_kind == "year" else 1
            specs.append((digits, lead))
            width += digits + lead + 3
        pair_rows = [[" "] * width for _ in range(2)]
        pair_rows[0][0] = "@" if pair == 0 else ">"
        pair_rows[0][-1] = "v"
        pair_rows[1][0] = "v"
        pair_rows[1][-1] = "<"
        x = 1
        for (digits, lead), (east_value, east_kind), (west_value, west_kind) in zip(
            specs, east, west, strict=True
        ):
            east_token = (
                " " * lead
                + f"`{east_value:0{digits}d}`"
                + ("s" if east_kind == "send" else "")
            )
            pair_rows[0][x : x + len(east_token)] = east_token
            prefix = "HsN" if west_kind == "year" else ("s" if west_kind == "send" else " ")
            west_digits = f"{west_value:0{digits}d}"[::-1]
            west_token = prefix + " " * (lead - len(prefix)) + f"`{west_digits}`"
            pair_rows[1][x : x + len(west_token)] = west_token
            x += digits + lead + 3
        rows.extend("".join(row) for row in pair_rows)
    assert cursor == len(entries)
    return rows


def combined_rows(words: list[int]) -> list[str]:
    """Return a 64x19 stacked DICT+MAIN logic probe with one little man."""
    dictionary = [list(row.ljust(50)) for row in history_gen5.dict_rows_four(words)]

    # The final pair is much shorter than the room's widest pair. Shift both rows together so its
    # paired vertical literals remain legal and its post-year stop sits east of MAIN. Replacing H
    # by a south turn lets the dictionary man descend through a clear column into MAIN's bottom bus.
    for y in (10, 11):
        turn = dictionary[y][49]
        occupied = [(x, ch) for x, ch in enumerate(dictionary[y][1:49], 1) if ch != " "]
        for x, _ in occupied:
            dictionary[y][x] = " "
        for x, ch in occupied:
            dictionary[y][x + 14] = ch
        dictionary[y][49] = turn

    width = 64
    rows = [[" "] * width for _ in range(19)]
    for y, row in enumerate(dictionary):
        rows[y][14 : 14 + len(row)] = row

    main = COMPACT_EXP[4:11]
    for y, row in enumerate(main, 12):
        rows[y][: len(row)] = row

    stop_x = next(x for x, ch in enumerate(rows[11]) if ch == "H")
    assert stop_x == 44
    rows[11][stop_x] = "v"
    for y in range(12, 18):
        assert rows[y][stop_x] == " "
        # MAIN's shared bottom return crosses an X that distinguishes a real year from startup.
        # Direct initialization leaves A=-1996, so neutralise it exactly as the old startup did.
        rows[y][stop_x] = "0" if y == 17 else "v"
    assert rows[18][stop_x] == " "
    rows[18][stop_x] = "<"
    return ["".join(row) for row in rows]


def folded_rows(words: list[int]) -> list[str]:
    """Fit an eight-row DICT and seven-row MAIN in a 78x13 L-shaped envelope."""
    dictionary = dict_rows_six(words)
    main = [list(row) for row in COMPACT_EXP[4:11]]
    # Tag the year-output path as positive; ROUTER negates the 128..4095 band before YEAR.
    main[5][24] = " "
    width, main_x, main_y = 78, 28, 6
    assert max(map(len, dictionary[:6])) <= 72
    assert max(map(len, dictionary[6:])) <= 28

    rows = [[" "] * width for _ in range(13)]
    for y, row in enumerate(dictionary):
        rows[y][: len(row)] = row
    for y, row in enumerate(main, main_y):
        for x, ch in enumerate(row, main_x):
            if ch == " ":
                continue
            assert rows[y][x] == " ", (x, y, rows[y][x], ch)
            rows[y][x] = ch

    # Neutralise A after year initialization, then use the row's existing west turn as the descent.
    stop_x = next(x for x, ch in enumerate(rows[7]) if ch == "H")
    assert rows[7][0] == "v"
    rows[7][stop_x] = "0"
    # The final walked zero literal is harmless; the row's existing west turn becomes the descent.
    for y in range(8, 12):
        assert rows[y][0] == " "
        rows[y][0] = "v"
    assert rows[12][0] == " "
    rows[12][0] = ">"
    return ["".join(row) for row in rows]


def router_rows() -> list[str]:
    """Send negatives and values >=2048 to ring; send smaller positives toward output."""
    rows = [[" "] * 24 for _ in range(12)]

    def put(y: int, x: int, text: str) -> None:
        rows[y][x : x + len(text)] = text

    # The first 41 values are DICT initialization and all go to ring.
    put(7, 0, "@`41`b>rdX")
    rows[8][8] = "m"
    rows[9][8] = "s"
    rows[10][8] = "<"
    rows[10][6] = "^"

    # Negative normal values are circulating year words and go to ring unchanged.
    rows[6][9] = "<"
    rows[6][0] = "v"
    rows[10][0] = ">"
    rows[10][5] = "s"

    # Current packed phrases are >=4140; characters and positive year markers are <=2026.
    put(8, 9, ">M`2048`W-X")
    rows[7][19] = "+"
    rows[6][19] = "s"  # output stream
    rows[5][19] = "<"
    rows[9][19] = "+"
    rows[10][19] = "s"  # phrase ring
    rows[11][19] = "<"

    rows[5][6] = "v"
    rows[11][6] = "^"
    return ["".join(row) for row in rows]


def year_classify_rows() -> list[str]:
    """Pass ASCII unchanged and negate positive year markers for the existing YEAR room."""
    rows = [[" "] * 16 for _ in range(9)]
    rows[4][:12] = list("@>rM`128`W-X")
    rows[3][11] = "+"
    rows[2][11] = "s"
    rows[1][11] = "<"
    rows[1][1] = "v"
    rows[4][1] = ">"
    rows[5][11] = "+"
    rows[6][11] = "N"
    rows[7][11] = "s"
    rows[8][11] = "<"
    rows[8][1] = "^"
    return ["".join(row) for row in rows]


def generate(digits_path: Path, rooms_root: Path, program_dir: Path) -> None:
    digits = [int(value) for value in digits_path.read_text().split()]
    words, payload = history_gen4.split_stream(digits)
    words, payload = history_gen5.remap(words, payload)
    words, payload = reorder_ring_slots(words, payload, six_row_order(words))
    remapped = history_gen5.rebuild_stream(words, payload)

    # Reuse the already-audited DRUM, DEC, YEAR and RELAY emitters. The generated separate DICT and
    # EXP types are intentionally unreferenced by the combined netlist.
    history_gen4.generate_from_digits(
        remapped, rooms_root, program_dir, history_gen5.dict_rows_four
    )

    rows = combined_rows(words)
    room_dir = rooms_root / "history-exp-dict"
    room_dir.mkdir(parents=True, exist_ok=True)
    (room_dir / "interface.toml").write_text(
        '[ports]\nstream = "A"\nring_in = "B"\nring_out = "c"\nout = "d"\n'
    )
    (room_dir / "base.room").write_text(
        history_gen4.bordered(
            rows,
            {
                (-2, 14): "A",  # MAIN payload receive, west
                (31, len(rows) + 1): "B",  # both MAIN ring reads, south
                (22, -2): "c",  # all DICT and MAIN ring sends, north
                (7, len(rows) + 1): "d",  # all character/year sends, south
            },
        )
    )

    (program_dir / "combined.eman.toml").write_text(
        '''problem = "history-lesson"

[rooms]
drum = "history-drum-direct"
dec = "history-dec"
exp = "history-exp-dict"
year = "history-year"
relay = "history-relay"
output = "output"

[[pipes]]
from = "drum.out"
to = "dec.feed"
min = 2

[[pipes]]
from = "dec.out"
to = "exp.stream"
min = 2

[[pipes]]
from = "exp.ring_out"
to = "relay.feed"
# 40 phrases plus the year occupy the two legs plus RELAY's held word.
min = 40

[[pipes]]
from = "relay.out"
to = "exp.ring_in"
min = 2

[[pipes]]
from = "exp.out"
to = "year.feed"
min = 2

[[pipes]]
from = "year.out"
to = "output.feed"
min = 2
'''
    )

    folded = folded_rows(words)
    folded_dir = rooms_root / "history-exp-dict-folded"
    folded_dir.mkdir(parents=True, exist_ok=True)
    (folded_dir / "interface.toml").write_text(
        '[ports]\nstream = "A"\nring_in = "B"\nmux = "c"\n'
    )
    (folded_dir / "base.room").write_text(
        history_gen4.bordered(
            folded,
            {
                (-2, 8): "A",
                (len(folded[0]) + 1, 8): "B",
                (len(folded[0]) + 1, 6): "c",
            },
        )
    )

    router = router_rows()
    router_dir = rooms_root / "history-router"
    router_dir.mkdir(parents=True, exist_ok=True)
    (router_dir / "interface.toml").write_text(
        '[ports]\nfeed = "A"\nring = "b"\nout = "c"\n'
    )
    (router_dir / "base.room").write_text(
        history_gen4.bordered(
            router,
            {
                (-2, 7): "A",
                (20, len(router) + 1): "b",
                (len(router[0]) + 1, 6): "c",
            },
        )
    )

    classify = year_classify_rows()
    classify_dir = rooms_root / "history-year-classify"
    classify_dir.mkdir(parents=True, exist_ok=True)
    (classify_dir / "interface.toml").write_text('[ports]\nfeed = "A"\nout = "b"\n')
    (classify_dir / "base.room").write_text(
        history_gen4.bordered(
            classify,
            {
                (-2, 4): "A",
                (len(classify[0]) + 1, 4): "b",
            },
        )
    )

    (program_dir / "folded.eman.toml").write_text(
        '''problem = "history-lesson"

[rooms]
drum = "history-drum-direct"
dec = "history-dec"
exp = "history-exp-dict-folded"
router = "history-router"
classify = "history-year-classify"
year = "history-year"
relay = "history-relay"
output = "output"

[[pipes]]
from = "drum.out"
to = "dec.feed"
min = 2

[[pipes]]
from = "dec.out"
to = "exp.stream"
min = 2

[[pipes]]
from = "exp.mux"
to = "router.feed"
min = 2

[[pipes]]
from = "router.ring"
to = "relay.feed"
# All 41 initialized values must fit before EXP begins receiving from the ring.
min = 40

[[pipes]]
from = "relay.out"
to = "exp.ring_in"
min = 2

[[pipes]]
from = "router.out"
to = "classify.feed"
min = 2

[[pipes]]
from = "classify.out"
to = "year.feed"
min = 2

[[pipes]]
from = "year.out"
to = "output.feed"
min = 2
'''
    )


if __name__ == "__main__":
    generate(
        Path("history_digits_1977.txt"),
        Path("../programs/history-lesson/rooms-combined"),
        Path("../programs/history-lesson"),
    )
