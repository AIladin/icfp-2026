"""Direct-dictionary experiment for history-lesson.

The current stream spends 159 base-133 digits describing 40 flat phrases.  Their already-packed
64-bit words need only 392 instruction cells as decimal literals (including the negative year
slot), so a dedicated producer can initialize EXP's ring directly and remove those 159 digits.
This generator emits auditable rooms and a netlist; lmp owns concrete placement and routing.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from history_gen2 import RELAY_MAP, dec_map, drum, year_room
from history_gen3 import COMPACT_EXP
from memory_gen import Canvas

BASE = 133
END = 9


def split_stream(digits: list[int]) -> tuple[list[int], list[int]]:
    """Return packed phrase words and the post-header data digits."""
    words: list[int] = []
    pos = 0
    while digits[pos] != END:
        length = digits[pos]
        pos += 1
        word = 0
        for value in digits[pos : pos + length]:
            word = word * 128 + value
        words.append(word)
        pos += length
    return words, digits[pos + 1 :]


def bordered(rows: list[str], pins: dict[tuple[int, int], str]) -> str:
    width = max(map(len, rows))
    rows = [row.ljust(width) for row in rows]
    grid = [list(" " * (width + 4)) for _ in range(len(rows) + 4)]
    x0 = y0 = 1
    grid[y0][x0] = grid[y0][x0 + width + 1] = "+"
    grid[y0 + len(rows) + 1][x0] = grid[y0 + len(rows) + 1][x0 + width + 1] = "+"
    for x in range(x0 + 1, x0 + width + 1):
        grid[y0][x] = grid[y0 + len(rows) + 1][x] = "-"
    for y in range(y0 + 1, y0 + len(rows) + 1):
        grid[y][x0] = grid[y][x0 + width + 1] = "|"
    for y, row in enumerate(rows, y0 + 1):
        grid[y][x0 + 1 : x0 + width + 1] = row
    for (x, y), marker in pins.items():
        grid[y0 + 1 + y][x0 + 1 + x] = marker
    return "\n".join("".join(row).rstrip() for row in grid).rstrip() + "\n"


def dict_rows(words: list[int]) -> list[str]:
    """Fold 40 words into seven independently padded east/west row pairs."""
    assert len(words) == 40
    entries: list[tuple[int, str]] = [(word, "send") for word in words]
    entries += [(1996, "year"), (0, "stop")]

    pair_specs: list[list[tuple[int, int, str, str]]] = []
    widths: list[int] = []
    for pair in range(7):
        east = entries[pair * 6 : pair * 6 + 3]
        west_run = entries[pair * 6 + 3 : pair * 6 + 6]
        west = list(reversed(west_run))
        specs: list[tuple[int, int, str, str]] = []
        width = 2
        for (east_value, east_kind), (west_value, west_kind) in zip(east, west, strict=True):
            digits = max(len(str(east_value)), len(str(west_value)))
            # The final year slot has room for H,s,N before its shared opening backtick.
            lead = 3 if west_kind == "year" else 1
            specs.append((digits, lead, east_kind, west_kind))
            width += digits + lead + 3
        pair_specs.append(specs)
        widths.append(width)

    width = max(widths)
    rows = [[" "] * width for _ in range(14)]
    for y in range(14):
        eastbound = y % 2 == 0
        rows[y][0 if eastbound else width - 1] = "@" if y == 0 else (">" if eastbound else "<")
        rows[y][width - 1 if eastbound else 0] = "v"

    for pair, specs in enumerate(pair_specs):
        east_entries = entries[pair * 6 : pair * 6 + 3]
        west_entries = list(reversed(entries[pair * 6 + 3 : pair * 6 + 6]))
        cursor = 1
        for spec, east_entry, west_entry in zip(specs, east_entries, west_entries, strict=True):
            digits, lead, _, west_kind = spec
            east_value, east_kind = east_entry
            west_value, _ = west_entry
            east_digits = f"{east_value:0{digits}d}"
            west_digits = f"{west_value:0{digits}d}"[::-1]

            east_token = " " * lead + f"`{east_digits}`" + ("s" if east_kind == "send" else "")
            rows[2 * pair][cursor : cursor + len(east_token)] = east_token

            prefix = "HsN" if west_kind == "year" else ("s" if west_kind == "send" else " ")
            west_token = prefix + " " * (lead - len(prefix)) + f"`{west_digits}`"
            rows[2 * pair + 1][cursor : cursor + len(west_token)] = west_token
            cursor += digits + lead + 3

    return ["".join(row) for row in rows]


def exp_rows() -> list[str]:
    """Five-row MAIN plus a 41-word direct initialization loop in its eastern slack."""
    rows = [list(row.ljust(58)) for row in COMPACT_EXP[6:11]]

    # DICT sends 40 phrases followed by -1996.  Keep all 41 in the ring.  On the 41st pass BP
    # reaches zero, so `a` falls east, descends at x=47, and joins MAIN's bottom return bus.
    for x, ch in enumerate("@`41`b", 44):
        rows[1][x] = ch
    rows[1][50] = "v"
    rows[1][54] = "<"
    for x, ch in enumerate(">rsma", 50):
        rows[2][x] = ch
    rows[2][55] = "0"  # neutralise the last value before crossing MAIN's year-test X
    rows[2][56] = "v"
    rows[3][56] = "v"
    rows[4][56] = "<"

    # MAIN has no spawn now; after initialization the bottom bus rises to this entry. Preserve
    # old rows 4-5 above it: phrase rotation's `a` rises through them to its r/s loop.
    return [row.ljust(58) for row in COMPACT_EXP[4:6]] + ["".join(row) for row in rows]


def generate_from_digits(
    digits: list[int],
    rooms_root: Path,
    program_dir: Path,
    dict_builder: Callable[[list[int]], list[str]] = dict_rows,
) -> None:
    words, payload = split_stream(digits)
    assert len(words) == 40 and len(payload) == 1818

    # DICT: lower-case marker is its sole outgoing pin.
    drows = dict_builder(words)
    (rooms_root / "history-dict").mkdir(parents=True, exist_ok=True)
    (rooms_root / "history-dict" / "interface.toml").write_text('[ports]\nout = "a"\n')
    (rooms_root / "history-dict" / "base.room").write_text(
        bordered(drows, {(len(drows[0]) + 1, len(drows) - 1): "a"})
    )

    # DRUM: remove the 159-symbol dictionary header; one output only.
    c = Canvas()
    drum_h = drum(c, 78, payload, BASE)
    assert drum_h == 65
    grid = c.render().splitlines()
    grid[1] += "a"
    (rooms_root / "history-drum-direct").mkdir(parents=True, exist_ok=True)
    (rooms_root / "history-drum-direct" / "interface.toml").write_text('[ports]\nout = "a"\n')
    (rooms_root / "history-drum-direct" / "base.room").write_text("\n".join(grid) + "\n")

    # DEC pins follow its only receive/send operations.
    dec = dec_map(BASE)
    (rooms_root / "history-dec").mkdir(parents=True, exist_ok=True)
    (rooms_root / "history-dec" / "interface.toml").write_text('[ports]\nfeed = "A"\nout = "b"\n')
    (rooms_root / "history-dec" / "base.room").write_text(
        bordered(dec, {(-2, 0): "A", (len(dec[0]) + 1, 1): "b"})
    )

    exp = exp_rows()
    (rooms_root / "history-exp-direct").mkdir(parents=True, exist_ok=True)
    (rooms_root / "history-exp-direct" / "interface.toml").write_text(
        '[ports]\ndict = "A"\nstream = "B"\nring_in = "C"\nout = "d"\nring_out = "e"\n'
    )
    (rooms_root / "history-exp-direct" / "base.room").write_text(
        bordered(
            exp,
            {
                (55, 8): "A",        # init r chooses south; MAIN's ring r still chooses east
                (-2, 2): "B",        # MAIN stream r
                (58 + 1, 3): "C",    # MAIN ring r
                (-2, 5): "d",        # direct/year character sends
                (58 + 1, 4): "e",    # init and phrase recycle sends
            },
        )
    )

    yr = year_room(22)
    (rooms_root / "history-year").mkdir(parents=True, exist_ok=True)
    (rooms_root / "history-year" / "interface.toml").write_text('[ports]\nfeed = "A"\nout = "b"\n')
    (rooms_root / "history-year" / "base.room").write_text(
        bordered(yr, {(-2, 1): "A", (-2, 2): "b"})
    )

    (rooms_root / "history-relay").mkdir(parents=True, exist_ok=True)
    (rooms_root / "history-relay" / "interface.toml").write_text('[ports]\nfeed = "A"\nout = "b"\n')
    (rooms_root / "history-relay" / "base.room").write_text(
        bordered(RELAY_MAP, {(-2, 0): "A", (-2, 1): "b"})
    )

    program_dir.mkdir(parents=True, exist_ok=True)
    (program_dir / "direct.eman.toml").write_text(
        '''problem = "history-lesson"

[rooms]
drum = "history-drum-direct"
dict = "history-dict"
dec = "history-dec"
exp = "history-exp-direct"
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
from = "dict.out"
to = "exp.dict"
min = 2

[[pipes]]
from = "exp.ring_out"
to = "relay.feed"
# 41 initialized words occupy the two legs plus RELAY's hand; 40 cells is the safe floor.
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


def generate(digits_path: Path, rooms_root: Path, program_dir: Path) -> None:
    generate_from_digits(
        [int(value) for value in digits_path.read_text().split()], rooms_root, program_dir
    )


if __name__ == "__main__":
    generate(
        Path("history_digits_1977.txt"),
        Path("../rooms"),
        Path("../programs/history-lesson"),
    )
