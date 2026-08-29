"""Optimistic encoder-only bound for zero-header, one-symbol structural macros.

The existing 40 flat phrases and their 159-symbol header stay unchanged.  A macro may contain any
repeated 9..64-character substring (except the generated year marker), costs one payload symbol,
and is charged no stream header or ring slot.  This is intentionally more generous than a real
Littleman decoder; if eight such macros cannot reach the side-80 gate, machine work is unjustified.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import cast

from history_gen4 import split_stream
from history_long_phrase_probe import unpack
from history_phrase import YEAR, fold_years
from history_sweep import tokenize

HEADER_SYMBOLS = 159
TARGET = 1885
MAX_MACROS = 8


def candidates(text: str) -> list[str]:
    counts: Counter[str] = Counter()
    for length in range(9, 65):
        for start in range(len(text) - length + 1):
            phrase = text[start : start + length]
            if YEAR not in phrase:
                counts[phrase] += 1
    useful = [phrase for phrase, hits in counts.items() if hits >= 2]
    return sorted(
        useful,
        key=lambda phrase: -((len(phrase) - 1) * counts[phrase]),
    )[:3000]


def payload_cost(text: str, phrases: list[str], macros: list[str]) -> int:
    return len(tokenize(text, phrases + macros))


def select(text: str, phrases: list[str], pool: list[str], label: str) -> tuple[int, list[str]]:
    baseline = payload_cost(text, phrases, [])
    macros: list[str] = []
    current = baseline
    print(f"{label}: pool {len(pool)}")
    for step in range(1, MAX_MACROS + 1):
        best_cost = current
        best_macro: str | None = None
        for macro in pool:
            if macro in macros:
                continue
            trial = payload_cost(text, phrases, macros + [macro])
            if trial < best_cost:
                best_cost = trial
                best_macro = macro
        if best_macro is None:
            break
        macros.append(best_macro)
        current = best_cost
        print(f"{step}: total {HEADER_SYMBOLS + current}, saved {baseline - current}, {best_macro!r}")
    return current, macros


def main() -> None:
    cases = json.loads(Path("../programs/history-lesson-cases.json").read_text())
    output = cast(list[str], cases[0]["rounds"][0]["out"])
    text = fold_years("".join(chr(int(value)) for value in output))
    digits = [int(value) for value in Path("history_digits_1977.txt").read_text().split()]
    words, payload = split_stream(digits)
    phrases = [unpack(word) for word in words]
    baseline = payload_cost(text, phrases, [])
    assert HEADER_SYMBOLS + baseline == len(digits) == 1977
    assert baseline == len(payload)

    pool = candidates(text)
    print(f"baseline {HEADER_SYMBOLS + baseline}, payload {baseline}")
    current, macros = select(text, phrases, pool, "unbounded control strings")
    total = HEADER_SYMBOLS + current
    print(f"unbounded final {total}; target {TARGET}; margin {TARGET - total}; macros {len(macros)}")

    # A realistic table entry is one 64-bit base-128 word.  Restrict each macro to at most eight
    # existing character/primary-phrase tokens, so its expansion recipe fits one ring cell.
    packed_pool = [phrase for phrase in pool if len(tokenize(phrase, phrases)) <= 8]
    current, macros = select(text, phrases, packed_pool, "one-word child recipes")
    total = HEADER_SYMBOLS + current
    print(f"packed final {total}; target {TARGET}; margin {TARGET - total}; macros {len(macros)}")


if __name__ == "__main__":
    main()
