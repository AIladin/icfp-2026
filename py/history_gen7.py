"""Pack the preserved 1,977-symbol history stream into a variable-width 80-column drum.

The fixed planner guarantees capacity for every base-133 value and therefore stops at eight stream
symbols per literal.  This generator prices each actual value instead: a nine-symbol block is legal
when both its decimal spelling and the reversed spelling fit signed 64-bit.  A bounded dynamic
program chooses four literals per row, 27..32 symbols per row, and fills 66 data rows.

The surrounding decoder is copied geometrically from the server-verified 81x81 fallback.  This
first candidate deliberately remains 81x81: it isolates literal density and vertical-backtick
legality before attempting the separate one-row EXP shrink needed for side 80.
"""

from __future__ import annotations

import argparse
from functools import lru_cache
from itertools import product
from pathlib import Path

from history_gen2 import RELAY_MAP, dec_map, room_map, year_room
from history_gen3 import COMPACT_EXP
from memory_gen import Canvas

BASE = 133
LIMIT = 2**63 - 1
DATA_ROWS = 66
ROW_CELLS = 75
COMPOSITIONS = tuple(
    chunks
    for chunks in product(range(1, 10), repeat=4)
    if 27 <= sum(chunks) <= 32
)


type Block = tuple[int, str]
type RowPlan = tuple[Block, ...]
type RowChoice = tuple[int, int, int, RowPlan, int]
type Accumulator = tuple[int, int, int, int]
type SearchState = tuple[int, int, int, tuple[Accumulator, ...]]
type SearchPath = tuple[tuple[RowPlan, int], ...]


def packed_text(digits: tuple[int, ...]) -> str | None:
    """Return the shortest legal decimal spelling of one reversed base-133 block."""
    value = 0
    for digit in reversed(digits):
        value = value * BASE + digit
    text = str(value)
    if value > LIMIT or int(text[::-1]) > LIMIT:
        return None
    return text


def plan_rows(digits: list[int], w_int: int = 78) -> tuple[list[RowPlan], list[int]]:
    """Find an exact parse whose vertical backtick spans contain no instructions.

    For each column, ``pending`` tracks an earlier unmatched vertical tick and ``bad`` tracks a
    non-digit instruction seen after it. A later tick may close ``pending`` only when that column is
    not bad. An odd final tick is legal because every generated tick is already paired horizontally.
    Four states per stream position form a bounded beam; an exact backward density pass first
    removes every position that cannot still end at symbol 1,977 on row 66.
    """
    stream = tuple(digits)
    target = len(stream)

    @lru_cache(maxsize=None)
    def choices(start: int, east: bool) -> tuple[RowChoice, ...]:
        found: dict[tuple[int, int, int], tuple[RowPlan, int]] = {}
        for chunks in COMPOSITIONS:
            end = start + sum(chunks)
            if end > target:
                continue
            cursor = start
            blocks: list[Block] = []
            cost = 0
            for take in chunks:
                text = packed_text(stream[cursor : cursor + take])
                if text is None:
                    break
                blocks.append((take, text))
                cost += len(text) + 3
                cursor += take
            if len(blocks) != 4 or cost > ROW_CELLS:
                continue

            row_plan = tuple(blocks)
            for offset in range(ROW_CELLS - cost + 1):
                ticks = controls = 0
                if east:
                    x = 2 + offset
                    for _, text in row_plan:
                        ticks |= 1 << x | 1 << (x + len(text) + 1)
                        controls |= 1 << (x + len(text) + 2)
                        x += len(text) + 3
                else:
                    x = w_int - 1 - offset
                    for _, text in row_plan:
                        ticks |= 1 << (x - len(text) - 1) | 1 << x
                        controls |= 1 << (x - len(text) - 2)
                        x -= len(text) + 3
                found.setdefault((end, ticks, controls), (row_plan, offset))
        return tuple(
            (end, ticks, controls, row_plan, offset)
            for (end, ticks, controls), (row_plan, offset) in found.items()
        )

    @lru_cache(maxsize=None)
    def ends(start: int, east: bool) -> frozenset[int]:
        return frozenset(choice[0] for choice in choices(start, east))

    forward = [{0}]
    for row in range(DATA_ROWS):
        east = row % 2 == 0
        forward.append({end for start in forward[-1] for end in ends(start, east)})
    if target not in forward[-1]:
        raise ValueError(f"66 independent rows reach at most {max(forward[-1])}, not {target}")

    finish: list[set[int]] = [set() for _ in range(DATA_ROWS + 1)]
    finish[-1] = {target}
    for row in range(DATA_ROWS - 1, -1, -1):
        east = row % 2 == 0
        finish[row] = {
            start for start in forward[row] if ends(start, east) & finish[row + 1]
        }

    states: dict[SearchState, SearchPath] = {(0, 0, 0, ()): ()}
    beam_per_position = 16
    for row in range(DATA_ROWS):
        east = row % 2 == 0
        buckets: dict[int, dict[SearchState, SearchPath]] = {}
        for (start, pending, bad, saved), path in states.items():
            for end, ticks, controls, row_plan, offset in choices(start, east):
                if end not in finish[row + 1] or ticks & bad:
                    continue

                accumulators = {column: (forward, reverse, power) for column, forward, reverse, power in saved}
                closing = pending & ticks
                opening = ticks & ~pending
                for column in range(w_int):
                    bit = 1 << column
                    if closing & bit:
                        accumulators.pop(column, None)
                    elif opening & bit:
                        accumulators[column] = (0, 0, 1)

                next_pending = pending ^ ticks
                next_bad = bad & ~ticks
                poisoned = controls & next_pending
                next_bad |= poisoned
                for column in range(w_int):
                    if poisoned & 1 << column:
                        accumulators.pop(column, None)

                x = 2 + offset if east else w_int - 1 - offset
                for _, text in row_plan:
                    if east:
                        digit_cells = enumerate(text, x + 1)
                        x += len(text) + 3
                    else:
                        digit_cells = enumerate(text[::-1], x - len(text))
                        x -= len(text) + 3
                    for column, char in digit_cells:
                        bit = 1 << column
                        if not next_pending & bit or next_bad & bit:
                            continue
                        forward, reverse, power = accumulators[column]
                        digit = int(char)
                        forward = forward * 10 + digit
                        reverse += digit * power
                        power *= 10
                        if forward > LIMIT or reverse > LIMIT:
                            next_bad |= bit
                            del accumulators[column]
                        else:
                            accumulators[column] = (forward, reverse, power)

                next_saved = tuple(
                    (column, *values) for column, values in sorted(accumulators.items())
                )
                state = (end, next_pending, next_bad, next_saved)
                bucket = buckets.setdefault(end, {})
                bucket.setdefault(state, path + ((row_plan, offset),))
                if len(bucket) > 4 * beam_per_position:
                    ranked = sorted(
                        bucket.items(),
                        key=lambda item: (item[0][2].bit_count(), item[0][1].bit_count()),
                    )
                    buckets[end] = dict(ranked[:beam_per_position])
        states = {}
        for bucket in buckets.values():
            ranked = sorted(
                bucket.items(),
                key=lambda item: (item[0][2].bit_count(), item[0][1].bit_count()),
            )
            states.update(ranked[:beam_per_position])
        if not states:
            raise ValueError(f"vertical backtick beam exhausted after row {row + 1}")

    path = next((path for (end, _, _, _), path in states.items() if end == target), None)
    if path is None:
        raise ValueError("vertical backtick beam did not reach the exact stream length")
    return [row_plan for row_plan, _ in path], [offset for _, offset in path]


def backtick_columns(row: RowPlan, w_int: int, east: bool, offset: int) -> list[int]:
    columns: list[int] = []
    if east:
        x = 2 + offset
        for _, text in row:
            columns.extend((x, x + len(text) + 1))
            x += len(text) + 3
        return columns

    x = w_int - 1 - offset
    for _, text in row:
        columns.extend((x - len(text) - 1, x))
        x -= len(text) + 3
    return sorted(columns)


def variable_drum(
    canvas: Canvas,
    w_int: int,
    digits: list[int],
    offsets: list[int] | None = None,
    audit: bool = False,
) -> int:
    """Draw the actual-value drum and return its wall-box height."""
    rows, planned_offsets = plan_rows(digits, w_int)
    if offsets is None:
        offsets = planned_offsets
    if len(offsets) != len(rows):
        raise ValueError("one horizontal offset is required per data row")

    canvas.room(0, 0, w_int + 2, len(rows) + 2)
    position = 0
    for index, (row, offset) in enumerate(zip(rows, offsets, strict=True)):
        cost = sum(len(text) + 3 for _, text in row)
        if not 0 <= offset <= ROW_CELLS - cost:
            raise ValueError(f"row {index} offset {offset} exceeds its {ROW_CELLS - cost} slack")
        y = index + 1
        east = index % 2 == 0
        if east:
            x = 2 + offset
            for _, text in row:
                canvas.text(x, y, f"`{text}`s")
                x += len(text) + 3
        else:
            x = w_int - 1 - offset
            for _, text in row:
                canvas.text(x - len(text) - 2, y, f"s`{text[::-1]}`")
                x -= len(text) + 3
        canvas.put(1 if east else w_int, y, "@" if index == 0 else (">" if east else "<"))
        canvas.put(w_int if east else 1, y, "H" if index == len(rows) - 1 else "v")

        if audit:
            takes = [take for take, _ in row]
            widths = [len(text) for _, text in row]
            values = [text for _, text in row]
            columns = backtick_columns(row, w_int, east, offset)
            print(
                f"row {index:02d} {'E' if east else 'W'} stream[{position}:{position + sum(takes)}] "
                f"take={takes} width={widths} cost={cost} off={offset} ticks={columns} "
                f"values={values}"
            )
        position += sum(take for take, _ in row)
    assert position == len(digits)
    return len(rows) + 2


def build(digits: list[int], offsets: list[int] | None = None, audit: bool = False) -> str:
    """Use the verified fallback machinery around an 80-column variable drum."""
    side = 81
    canvas = Canvas()
    drum_h = variable_drum(canvas, 78, digits, offsets, audit)
    assert drum_h == 68

    top = drum_h
    dec_x = 4
    exp_x = 27
    year_x = 3
    relay_x = 74

    canvas.room(0, top + 1, 3, 3)
    canvas.put(1, top + 2, "O")
    room_map(canvas, dec_x, top, dec_map(BASE))
    room_map(canvas, exp_x, top, COMPACT_EXP)
    room_map(canvas, year_x, top + 5, year_room(22))
    room_map(canvas, relay_x, top + 9, RELAY_MAP)

    canvas.pipe([(dec_x + 16, drum_h - 1), (dec_x + 16, top + 1), (dec_x + 15, top + 1)])
    canvas.pipe([(dec_x + 15, top + 2), (exp_x, top + 2)])
    canvas.pipe([(exp_x, top + 4), (year_x + 22, top + 4), (year_x + 22, top + 5)])
    canvas.pipe([(year_x, top + 7), (1, top + 7), (1, top + 3)])

    exp_e = exp_x + len(COMPACT_EXP[0]) + 1
    canvas.pipe([(relay_x, top + 12), (exp_e, top + 12)])
    points = [(exp_e, top), (side - 1, top)]
    x_left, x_right = exp_e + 1, side - 1
    for y in range(top + 1, top + 8):
        points.append((x_right if y % 2 == 1 else x_left, y))
        points.append((x_left if y % 2 == 1 else x_right, y))
    points.extend([(x_left, top + 10), (relay_x, top + 10)])
    canvas.pipe(points)
    return canvas.render()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--digits", type=Path, default=Path("history_digits_1977.txt"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    digits = [int(value) for value in args.digits.read_text().split()]
    args.out.write_text(build(digits, audit=args.audit))


if __name__ == "__main__":
    main()
