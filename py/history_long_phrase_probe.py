"""Bounded encoder-only probe for 9..16-character flat history phrases."""

from __future__ import annotations

from collections import Counter
import json
from itertools import combinations
from pathlib import Path
from typing import cast

from history_gen4 import split_stream
from history_phrase import YEAR, fold_years
from history_sweep import cost, tokenize

SLOT_BUDGET = 40


def unpack(word: int) -> str:
    chars: list[str] = []
    while word:
        word, char = divmod(word, 128)
        chars.append(chr(char))
    return "".join(chars)


def slots(phrase: str) -> int:
    return (len(phrase) + 7) // 8


def long_candidates(text: str) -> list[str]:
    counts: Counter[str] = Counter()
    for length in range(9, 17):
        for start in range(len(text) - length + 1):
            phrase = text[start : start + length]
            if YEAR not in phrase:
                counts[phrase] += 1
    useful = [phrase for phrase, hits in counts.items() if hits >= 3]
    return sorted(
        useful,
        key=lambda phrase: -((len(phrase) - 1) * text.count(phrase) - len(phrase) - 1),
    )[:1200]


def improve(text: str, phrases: list[str], pool: list[str]) -> list[str]:
    best = cost(text, phrases)
    while True:
        tokens = tokenize(text, phrases)
        used = Counter(token for token in tokens if isinstance(token, int))
        weak = sorted(range(len(phrases)), key=lambda index: used[index])[:12]
        best_move: tuple[int, list[str], str] | None = None
        have = set(phrases)
        for candidate in pool:
            if candidate in have:
                continue
            need = slots(candidate) - (SLOT_BUDGET - sum(map(slots, phrases)))
            remove_counts = range(0, 3) if need <= 0 else range(need, min(need + 2, 3))
            for remove_count in remove_counts:
                for removed in combinations(weak, remove_count):
                    trial = [p for index, p in enumerate(phrases) if index not in removed]
                    trial.append(candidate)
                    if sum(map(slots, trial)) > SLOT_BUDGET:
                        continue
                    trial_cost = cost(text, trial)
                    if trial_cost >= best:
                        continue
                    if best_move is None or trial_cost < best_move[0]:
                        best_move = trial_cost, trial, candidate
        if best_move is None:
            return phrases
        best, phrases, candidate = best_move
        print(f"add {candidate!r}: {best} digits, {sum(map(slots, phrases))} slots")


def main() -> None:
    cases = json.loads(Path("../programs/history-lesson-cases.json").read_text())
    output = cast(list[str], cases[0]["rounds"][0]["out"])
    text = fold_years("".join(chr(int(value)) for value in output))
    digits = [int(value) for value in Path("history_digits_1977.txt").read_text().split()]
    words, _ = split_stream(digits)
    phrases = [unpack(word) for word in words]
    assert cost(text, phrases) == 1977
    pool = long_candidates(text)
    print(f"baseline 1977 digits, {len(pool)} bounded candidates")
    result = improve(text, phrases, pool)
    final = cost(text, result)
    print(f"final {final} digits, {len(result)} phrases, {sum(map(slots, result))} slots")
    print(f"target 1885, margin {1885 - final}")


if __name__ == "__main__":
    main()
