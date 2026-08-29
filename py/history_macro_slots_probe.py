"""Optimistic fixed-slot bound for structural macros replacing flat history phrases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from history_gen4 import split_stream
from history_long_phrase_probe import unpack
from history_macro_probe import candidates, payload_cost
from history_phrase import fold_years
from history_sweep import tokenize

TARGET = 1885


def header_cost(phrases: list[str]) -> int:
    return sum(len(phrase) + 1 for phrase in phrases) + 1


def evict_one(text: str, phrases: list[str]) -> list[str]:
    return min(
        ([phrase for index, phrase in enumerate(phrases) if index != removed]
         for removed in range(len(phrases))),
        key=lambda trial: header_cost(trial) + payload_cost(text, trial, []),
    )


def choose_macros(
    text: str, phrases: list[str], pool: list[str], count: int,
) -> tuple[int, list[str]]:
    macros: list[str] = []
    current = payload_cost(text, phrases, macros)
    for _ in range(count):
        choices = (macro for macro in pool if macro not in macros)
        best = min(choices, key=lambda macro: payload_cost(text, phrases, macros + [macro]))
        trial = payload_cost(text, phrases, macros + [best])
        if trial >= current:
            break
        macros.append(best)
        current = trial
    return header_cost(phrases) + current, macros


def main() -> None:
    cases = json.loads(Path("../programs/history-lesson-cases.json").read_text())
    output = cast(list[str], cases[0]["rounds"][0]["out"])
    text = fold_years("".join(chr(int(value)) for value in output))
    digits = [int(value) for value in Path("history_digits_1977.txt").read_text().split()]
    words, _ = split_stream(digits)
    original = [unpack(word) for word in words]
    assert header_cost(original) + payload_cost(text, original, []) == 1977
    pool = candidates(text)

    phrases = list(original)
    print("macros total margin surviving-phrases recipe-tokens strings")
    for count in range(1, 21):
        phrases = evict_one(text, phrases)
        packed_pool = [macro for macro in pool if len(tokenize(macro, phrases)) <= 8]
        total, macros = choose_macros(text, phrases, packed_pool, count)
        recipes = sum(len(tokenize(macro, phrases)) for macro in macros)
        print(count, total, TARGET - total, len(phrases), recipes, repr(macros))


if __name__ == "__main__":
    main()
