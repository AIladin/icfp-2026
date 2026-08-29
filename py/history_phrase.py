"""The `history-lesson` payload: a phrase dictionary, packed into one base-131 digit stream.

[[Literal drum]] fixes the cost of a cell at ~2.85 bits, so the only lever left is sending fewer
bits. Byte-pair encoding gets 2810 characters down to 1958 symbols, and — this is the part that
makes it cheap to *decode* — the phrases are stored **flat**, not as a grammar. A ring cell holds a
whole 64-bit value, so one packed base-128 word is one phrase of up to eight characters, and
expanding it is the same `/` loop that unpacks the drum. No stack, no recursion, no Huffman ladder.

One stream, one alphabet, digits 1..130 (0 terminates a literal block):

    1..91     a character, ASCII 31 + digit
    92..       a phrase: rotate the ring forward by `digit - 92` and unpack the word that lands

The phrase digit is an offset from wherever the ring head already is, not an index. EXP reads the
word and leaves the ring where it stopped, so there is no sentinel and no realign loop; the encoder
carries the head instead, which costs nothing because a digit is a digit either way.

and it opens with the dictionary itself: per phrase a length, then that phrase's characters as raw
ASCII **in reverse**, so the decoder builds the packed word with `V = V*128 + c` and reads it back
in order. A length of `END` closes the section.
"""

from __future__ import annotations

import collections
import re

YEAR = "\x01"  # stands in for a four-digit year; the machine counts them out instead
FIRST_YEAR = 1996
CHAR_OFF = 31  # digit 1..91 -> ASCII 32..122
PACK = 128  # ring words are base-128 ASCII, 0 terminates
MAX_PHRASE = 8  # 128**8 < 2**63
END = MAX_PHRASE + 1  # a length that cannot occur, so it closes the dictionary


def fold_years(text: str) -> str:
    """Every year 1996.. is one placeholder: they are a counter, not data."""
    return re.sub(r"\b(19|20)\d\d\b", YEAR, text)


def merge_pairs(text: str, rounds: int) -> tuple[list[int], list[str]]:
    """Byte-pair encoding, then flattened: every surviving phrase is a plain string.

    Merged symbols that later got swallowed by a longer merge are dropped — flat expansions do not
    need them, which is most of why the dictionary stays at 141 digits.
    """
    alphabet = sorted(set(text))
    seq = [alphabet.index(c) for c in text]
    expand = {i: c for i, c in enumerate(alphabet)}
    nxt = len(alphabet)

    for _ in range(rounds):
        mark = alphabet.index(YEAR) if YEAR in alphabet else None
        counts = collections.Counter(
            pair for pair in zip(seq, seq[1:])
            if mark is None or (YEAR not in expand[pair[0]] and YEAR not in expand[pair[1]])
        )
        if not counts:
            break
        (a, b), hits = counts.most_common(1)[0]
        if hits < 3:
            break
        expand[nxt] = expand[a] + expand[b]
        folded, i = [], 0
        while i < len(seq):
            if i + 1 < len(seq) and seq[i] == a and seq[i + 1] == b:
                folded.append(nxt)
                i += 2
            else:
                folded.append(seq[i])
                i += 1
        seq, nxt = folded, nxt + 1

    live = sorted({x for x in seq if x >= len(alphabet)})
    phrases = [expand[x] for x in live]
    if any(len(p) > MAX_PHRASE for p in phrases):
        raise ValueError("a phrase outgrew one packed word")
    place = {x: i for i, x in enumerate(live)}
    char = {i: ord(c) - CHAR_OFF for i, c in enumerate(alphabet)}
    mark = alphabet.index(YEAR) if YEAR in alphabet else None
    slots = len(live) + (1 if mark is not None else 0)  # the year rides in the ring too

    out, head = [], 0
    for x in seq:
        if x in char and x != mark:
            out.append(char[x])
            continue
        target = len(live) if x == mark else place[x]
        step = (target - head) % slots  # forward-only: the ring never rewinds
        out.append(92 + step)
        head = (head + step + 1) % slots  # reading it advances the head one more place
    return out, phrases


def encode(text: str, rounds: int = 40, years: bool = False) -> tuple[list[int], int, list[str]]:
    """The whole digit stream, and the base it is written in."""
    data, phrases = merge_pairs(fold_years(text) if years else text, rounds)
    head: list[int] = []
    for phrase in phrases:
        head.append(len(phrase))
        head += [ord(c) for c in reversed(phrase)]
    head.append(END)
    # When years are folded the ring gains one more slot, holding the year as a NEGATIVE word --
    # which is how the machine tells it from a phrase, one `X` on the sign and no code space spent.
    # INIT seeds it from a literal rather than from the stream.
    return head + data, 92 + len(phrases) + (1 if years else 0), phrases


def decode(digits: list[int], years: bool = False) -> str:
    """Reference decoder — exactly what the two rooms do, so the grid can be diffed against it."""
    stream = iter(digits)
    ring: list[int] = []
    while (length := next(stream)) != END:
        word = 0
        for _ in range(length):
            word = word * PACK + next(stream)
        ring.append(word)

    if years:
        ring.append(-FIRST_YEAR)  # the year slot, seeded by INIT rather than sent

    out: list[str] = []
    head = 0
    for digit in stream:
        if digit <= 91:
            out.append(chr(digit + CHAR_OFF))
            continue
        head = (head + digit - 92) % len(ring)
        word = ring[head]
        if word < 0:  # the year: count it out in decimal, put the next one back
            year = -word
            ring[head] = -(year + 1)
            out.append(f"{year:04d}")
        else:
            while word:
                word, rest = divmod(word, PACK)
                out.append(chr(rest))
        head = (head + 1) % len(ring)
    return "".join(out)


if __name__ == "__main__":
    import pathlib
    import sys

    text = pathlib.Path(sys.argv[1]).read_text()
    digits, base, phrases = encode(text)
    print(f"{len(digits)} digits, base {base}, {len(phrases)} phrases", file=sys.stderr)
    print(f"round trip: {decode(digits) == text}", file=sys.stderr)
    print(" ".join(map(str, digits)))
