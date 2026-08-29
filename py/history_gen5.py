"""Reorder the direct phrase ring and fold its producer four words per row.

This is a geometry probe for integrating DICT with EXP.  Phrase references are relative ring
rotations, so the dictionary order can be changed if every payload offset is remapped while
tracking both old and new ring heads.
"""

from __future__ import annotations

import random
from pathlib import Path

import history_gen4

SLOTS = 41


def remap(words: list[int], payload: list[int]) -> tuple[list[int], list[int]]:
    """Return a geometry-friendly word order and equivalent relative-offset payload."""
    rng = random.Random(5)
    best: tuple[tuple[int, int], list[int]] | None = None
    indices = list(range(len(words)))
    for _ in range(100_000):
        order = rng.sample(indices, len(indices))
        entries = [words[i] for i in order] + [1996, 0, 0, 0, 0, 0, 0, 0]
        costs = []
        for start in range(0, 48, 8):
            east = entries[start : start + 4]
            west = list(reversed(entries[start + 4 : start + 8]))
            costs.append(18 + sum(max(len(str(a)), len(str(b))) for a, b in zip(east, west, strict=True)))
        score = max(costs), sum(costs)
        if best is None or score < best[0]:
            best = score, order
    assert best is not None
    order = best[1]

    new_position = {old: new for new, old in enumerate(order)}
    new_position[40] = 40  # the year remains the final ring slot
    old_head = new_head = 0
    remapped: list[int] = []
    for digit in payload:
        if digit <= 91:
            remapped.append(digit)
            continue
        old_target = (old_head + digit - 92) % SLOTS
        new_target = new_position[old_target]
        step = (new_target - new_head) % SLOTS
        remapped.append(92 + step)
        old_head = (old_target + 1) % SLOTS
        new_head = (new_target + 1) % SLOTS
    return [words[i] for i in order], remapped


def dict_rows_four(words: list[int]) -> list[str]:
    """Fold 40 words into six independently padded four-slot row pairs."""
    assert len(words) == 40
    entries: list[tuple[int, str]] = [(word, "send") for word in words]
    # Keep the semantic year and stop in the westbound half of the final pair. Four harmless
    # empty slots are walked first; the westbound execution order then reaches year, stop.
    entries += [(0, "blank")] * 4
    entries += [(1996, "year"), (0, "stop")] + [(0, "blank")] * 2

    pair_specs: list[list[tuple[int, int]]] = []
    widths: list[int] = []
    for pair in range(6):
        east = entries[pair * 8 : pair * 8 + 4]
        west = list(reversed(entries[pair * 8 + 4 : pair * 8 + 8]))
        specs = []
        width = 2
        for (east_value, _), (west_value, west_kind) in zip(east, west, strict=True):
            digits = max(len(str(east_value)), len(str(west_value)))
            lead = 3 if west_kind == "year" else 1
            specs.append((digits, lead))
            width += digits + lead + 3
        pair_specs.append(specs)
        widths.append(width)

    width = max(widths)
    rows = [[" "] * width for _ in range(12)]
    for y in range(12):
        eastbound = y % 2 == 0
        rows[y][0 if eastbound else width - 1] = "@" if y == 0 else (">" if eastbound else "<")
        rows[y][width - 1 if eastbound else 0] = "v"

    for pair, specs in enumerate(pair_specs):
        east_entries = entries[pair * 8 : pair * 8 + 4]
        west_entries = list(reversed(entries[pair * 8 + 4 : pair * 8 + 8]))
        cursor = 1
        for (digits, lead), (east_value, east_kind), (west_value, west_kind) in zip(
            specs, east_entries, west_entries, strict=True
        ):
            east_digits = f"{east_value:0{digits}d}"
            west_digits = f"{west_value:0{digits}d}"[::-1]
            east_suffix = "s" if east_kind == "send" else ""
            east_token = " " * lead + f"`{east_digits}`" + east_suffix
            rows[2 * pair][cursor : cursor + len(east_token)] = east_token

            if west_kind == "year":
                prefix = "HsN"
            elif west_kind == "send":
                prefix = "s"
            else:
                prefix = " "
            west_token = prefix + " " * (lead - len(prefix)) + f"`{west_digits}`"
            rows[2 * pair + 1][cursor : cursor + len(west_token)] = west_token
            cursor += digits + lead + 3
    return ["".join(row) for row in rows]


def rebuild_stream(words: list[int], payload: list[int]) -> list[int]:
    header: list[int] = []
    for word in words:
        digits: list[int] = []
        while word:
            word, digit = divmod(word, 128)
            digits.append(digit)
        header.append(len(digits))
        header.extend(reversed(digits))
    return header + [history_gen4.END] + payload


def generate(digits_path: Path, rooms_root: Path, program_dir: Path) -> None:
    digits = [int(value) for value in digits_path.read_text().split()]
    words, payload = history_gen4.split_stream(digits)
    words, payload = remap(words, payload)
    remapped = rebuild_stream(words, payload)

    history_gen4.generate_from_digits(remapped, rooms_root, program_dir, dict_rows_four)


if __name__ == "__main__":
    generate(
        Path("history_digits_1977.txt"),
        Path("../programs/history-lesson/rooms-four"),
        Path("../programs/history-lesson/four"),
    )
