"""Price a depth-two, at-most-40-rule grammar for history-lesson.

This is an encoder-only falsifier.  A rule stores two earlier symbols (raw character or rule), so
its proposed stream header costs three base-133 digits: a rule marker and two child ids.  The start
sequence costs one digit per symbol.  No Littleman semantics are modeled here.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
from typing import cast

from history_gen4 import split_stream
from history_phrase import YEAR, fold_years
from history_sweep import tokenize

MAX_RULES = 40
MAX_DEPTH = 2


@dataclass(frozen=True)
class Symbol:
    text: str
    depth: int
    rule: int | None = None


def replace_pair(seq: list[Symbol], pair: tuple[Symbol, Symbol], replacement: Symbol) -> list[Symbol]:
    out: list[Symbol] = []
    i = 0
    while i < len(seq):
        if i + 1 < len(seq) and (seq[i], seq[i + 1]) == pair:
            out.append(replacement)
            i += 2
        else:
            out.append(seq[i])
            i += 1
    return out


def build(text: str) -> tuple[list[Symbol], list[tuple[Symbol, Symbol]]]:
    chars = {ch: Symbol(ch, 0) for ch in set(text)}
    seq = [chars[ch] for ch in text]
    rules: list[tuple[Symbol, Symbol]] = []
    for _ in range(MAX_RULES):
        counts = Counter(zip(seq, seq[1:], strict=False))
        legal = [
            (hits, pair)
            for pair, hits in counts.items()
            if hits >= 3
            and max(pair[0].depth, pair[1].depth) + 1 <= MAX_DEPTH
            and YEAR not in pair[0].text + pair[1].text
        ]
        if not legal:
            break
        # Header cost is three digits. Replacing h non-overlapping occurrences saves about h-3;
        # exact replacement below handles overlapping equal-symbol pairs.
        _, pair = max(legal, key=lambda item: (item[0], len(item[1][0].text + item[1][1].text)))
        replacement = Symbol(
            pair[0].text + pair[1].text,
            max(pair[0].depth, pair[1].depth) + 1,
            len(rules),
        )
        new_seq = replace_pair(seq, pair, replacement)
        if len(seq) - len(new_seq) <= 3:
            break
        rules.append(pair)
        seq = new_seq
    return seq, rules


def hybrid_cost(text: str, phrases: list[str], macro_count: int) -> tuple[int, int]:
    """Greedily evict flat phrases, then spend those slots on depth-two pair macros."""
    kept = list(phrases)
    while len(kept) > MAX_RULES - macro_count:
        base_tokens = len(tokenize(text, kept))
        # Evict the phrase whose loss adds the fewest start symbols after refunding its header.
        victim = min(
            range(len(kept)),
            key=lambda i: (
                len(tokenize(text, kept[:i] + kept[i + 1 :]))
                - base_tokens
                - len(kept[i])
                - 1
            ),
        )
        kept.pop(victim)

    seq: list[tuple[str, int]] = []
    for token in tokenize(text, kept):
        seq.append((str(token), 0))
    made = 0
    for rule in range(macro_count):
        counts = Counter(zip(seq, seq[1:], strict=False))
        legal = [
            (hits, pair)
            for pair, hits in counts.items()
            if hits >= 4 and max(pair[0][1], pair[1][1]) + 1 <= MAX_DEPTH
        ]
        if not legal:
            break
        _, pair = max(legal, key=lambda item: item[0])
        replacement = (f"macro{rule}", max(pair[0][1], pair[1][1]) + 1)
        out: list[tuple[str, int]] = []
        i = 0
        while i < len(seq):
            if i + 1 < len(seq) and (seq[i], seq[i + 1]) == pair:
                out.append(replacement)
                i += 2
            else:
                out.append(seq[i])
                i += 1
        seq = out
        made += 1
    header = sum(len(phrase) + 1 for phrase in kept) + 3 * made + 1
    return header + len(seq), made


def main() -> None:
    # Read the normalized case rather than treating its JSON syntax as payload.
    case = json.loads(Path("../programs/history-lesson-cases.json").read_text())[0]
    output = cast(list[str], case["rounds"][0]["out"])
    raw = "".join(chr(int(value)) for value in output)
    text = fold_years(raw)
    seq, rules = build(text)
    stream_cost = len(seq) + 3 * len(rules) + 1
    used = Counter(symbol.rule for symbol in seq if symbol.rule is not None)
    print(f"text chars: {len(raw)}")
    print(f"rules: {len(rules)}, max depth: {max((s.depth for s in seq), default=0)}")
    print(f"start symbols: {len(seq)}, estimated total digits: {stream_cost}")
    print(f"target: 1885, margin: {1885 - stream_cost}")
    print(f"live top-level rules: {len(used)}")
    for index, pair in enumerate(rules):
        print(f"{index:2}: d{max(pair[0].depth, pair[1].depth) + 1} {pair[0].text + pair[1].text!r}")

    digits = [int(value) for value in Path("history_digits_1977.txt").read_text().split()]
    words, _ = split_stream(digits)
    phrases = [
        "".join(chr((word // (128**i)) % 128) for i in range(8) if (word // (128**i)) % 128)
        for word in words
    ]
    print("hybrid flat phrases + pair macros:")
    for macro_count in range(1, 21):
        total, made = hybrid_cost(text, phrases, macro_count)
        print(f"  slots {40 - macro_count}+{made}: {total} digits")


if __name__ == "__main__":
    main()
