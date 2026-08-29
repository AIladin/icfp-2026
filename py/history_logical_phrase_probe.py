"""Price multiword logical phrases for ``history-lesson`` before machine work.

Unlike ``history_long_phrase_probe.py``, a phrase consumes one reference slot regardless of how
many base-128 ring words hold its characters.  The optimistic stream cost is still exact: one
length symbol and every raw character in the header, then an optimal one-symbol parse.  Physical
ring words and the extra continuation decoder are reported but deliberately not charged; missing
the side-80 stream gate under that favorable model rejects the representation.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import random
from typing import cast

from history_gen4 import split_stream
from history_long_phrase_probe import unpack
from history_phrase import YEAR, fold_years
from history_sweep import cost, tokenize

MAX_LOGICAL_PHRASES = 40
MAX_LENGTH = 32
POOL_LIMIT = 3_000
SWAP_CANDIDATES = 128
TARGET = 1_885


def candidate_pool(text: str) -> list[str]:
    """Return a bounded pool ordered by an optimistic non-overlap saving."""
    counts: Counter[str] = Counter()
    for length in range(9, MAX_LENGTH + 1):
        for start in range(len(text) - length + 1):
            phrase = text[start : start + length]
            if YEAR not in phrase:
                counts[phrase] += 1
    useful = [
        phrase
        for phrase, hits in counts.items()
        if hits >= 2 and (len(phrase) - 1) * (hits - 1) > len(phrase) + 1
    ]
    useful.sort(key=lambda phrase: -((len(phrase) - 1) * counts[phrase]))
    return useful[:POOL_LIMIT]


def physical_words(phrases: list[str]) -> int:
    return sum((len(phrase) + 7) // 8 for phrase in phrases)


def header_cost(phrases: list[str]) -> int:
    return sum(len(phrase) + 1 for phrase in phrases) + 1


def refine(text: str, seed: list[str], pool: list[str]) -> list[str]:
    """Best-improvement search with exact costs and bounded swap screening.

    Adding a candidate temporarily is a cheap exact measure of its utility.  Only the best 128 by
    that measure need the more expensive all-evictions scan; an accepted move triggers a fresh
    ranking, so interactions are re-priced rather than assumed additive.
    """
    phrases = list(seed)
    while True:
        baseline = cost(text, phrases)
        additions = sorted(
            (
                (cost(text, phrases + [candidate]), candidate)
                for candidate in pool
                if candidate not in phrases
            ),
            key=lambda item: item[0],
        )[:SWAP_CANDIDATES]

        best_cost = baseline
        best: list[str] | None = None
        if len(phrases) < MAX_LOGICAL_PHRASES:
            for trial_cost, candidate in additions:
                if trial_cost < best_cost:
                    best_cost = trial_cost
                    best = phrases + [candidate]
        else:
            for _, candidate in additions:
                for removed in range(len(phrases)):
                    trial = [
                        phrase for index, phrase in enumerate(phrases) if index != removed
                    ] + [candidate]
                    trial_cost = cost(text, trial)
                    if trial_cost < best_cost:
                        best_cost = trial_cost
                        best = trial
        if best is None:
            return phrases
        phrases = best
        print(f"move -> {best_cost}", flush=True)


def main() -> None:
    cases = json.loads(Path("../programs/history-lesson-cases.json").read_text())
    output = cast(list[str], cases[0]["rounds"][0]["out"])
    text = fold_years("".join(chr(int(value)) for value in output))
    digits = [int(value) for value in Path("history_digits_1977.txt").read_text().split()]
    words, payload = split_stream(digits)
    phrases = [unpack(word) for word in words]
    assert len(phrases) == MAX_LOGICAL_PHRASES
    assert cost(text, phrases) == len(digits) == 1_977
    assert len(tokenize(text, phrases)) == len(payload) == 1_818

    pool = candidate_pool(text)
    print(
        f"baseline total 1977 = header {header_cost(phrases)} + payload {len(payload)}; "
        f"logical {len(phrases)}, physical {physical_words(phrases)}; pool {len(pool)}"
    )

    best = refine(text, phrases, pool)
    best_cost = cost(text, best)

    # Four fixed-size kicks are enough to falsify the obvious local-basin objection while keeping
    # both runtime and candidate storage bounded.
    rng = random.Random(19)
    for kick in range(4):
        trial = list(best)
        for _ in range(4):
            trial.pop(rng.randrange(len(trial)))
        trial = refine(text, trial, pool)
        trial_cost = cost(text, trial)
        if trial_cost < best_cost:
            best, best_cost = trial, trial_cost
            print(f"kick {kick}: {best_cost}", flush=True)

    payload_cost = len(tokenize(text, best))
    print(
        f"final total {best_cost} = header {header_cost(best)} + payload {payload_cost}; "
        f"logical {len(best)}, physical {physical_words(best)}; "
        f"long {sum(len(phrase) > 8 for phrase in best)}; target {TARGET}; "
        f"margin {TARGET - best_cost}"
    )
    for phrase in sorted((phrase for phrase in best if len(phrase) > 8), key=lambda p: (-len(p), p)):
        print(f"  {len(phrase):2d} chars/{(len(phrase) + 7) // 8} words {phrase!r}")


if __name__ == "__main__":
    main()
