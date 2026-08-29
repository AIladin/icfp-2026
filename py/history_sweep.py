"""Search for a phrase set that beats BPE's, judged by the exact digit count.

The drum's width is a step function of the symbol count ([[Literal drum]]): 2 015 symbols fit
width 84, the BPE baseline is 2 029. The true cost of a dictionary P is

    cost(P) = sum(len(p) + 1 for p in P) + 1 + tokens(text, P)

and BPE approximates both terms: it picks phrases by pair frequency, and it tokenizes by replaying
merges in order. Given a *fixed* P the optimal tokenization is a shortest-path DP over the text, and
given the DP it is cheap to exact-evaluate add/drop/swap moves on P. Constraints: len(p) <= 8
(one packed base-128 word), |P| <= 40 (base = 92 + |P| + 1 must stay <= 133 so a 17-digit literal
still carries 8 symbols), and no phrase contains the YEAR marker.
"""

from __future__ import annotations

import collections
import sys

from history_phrase import END, YEAR, decode, fold_years, merge_pairs

MAX_PHRASES = 40


def tokenize(text: str, phrases: list[str]) -> list[str | int]:
    """Optimal parse: fewest tokens, each a raw char or a phrase index."""
    n = len(text)
    starts: dict[str, list[int]] = collections.defaultdict(list)
    for i, p in enumerate(phrases):
        starts[p[0]].append(i)
    cost = [0] + [n + 1] * n
    back: list[tuple[int, str | int]] = [(0, "")] * (n + 1)
    for i in range(n):
        if cost[i] + 1 < cost[i + 1]:
            cost[i + 1], back[i + 1] = cost[i] + 1, (i, text[i])
        for pi in starts.get(text[i], ()):
            p = phrases[pi]
            j = i + len(p)
            if j <= n and cost[i] + 1 < cost[j] and text.startswith(p, i):
                cost[j], back[j] = cost[i] + 1, (i, pi)
    out: list[str | int] = []
    i = n
    while i:
        i, tok = back[i]
        out.append(tok)
    return out[::-1]


def cost(text: str, phrases: list[str]) -> int:
    header = sum(len(p) + 1 for p in phrases) + 1
    return header + len(tokenize(text, phrases))


def candidates(text: str, max_len: int) -> list[str]:
    """Substrings that could pay for themselves: >= 3 occurrences, no YEAR marker."""
    counts: collections.Counter[str] = collections.Counter()
    for length in range(2, max_len + 1):
        for i in range(len(text) - length + 1):
            sub = text[i : i + length]
            if YEAR not in sub:
                counts[sub] += 1
    return [s for s, c in counts.items() if c >= 3 and (len(s) - 1) * (c - 1) > len(s) + 1]


def improve(text: str, phrases: list[str], pool: list[str], evict_depth: int = 4, verbose: bool = True) -> list[str]:
    """First-improvement add/drop/swap, exact-evaluated. Estimates order the pool, DP settles it."""
    best = cost(text, phrases)
    phrases = list(phrases)
    while True:
        toks = tokenize(text, phrases)
        used = collections.Counter(t for t in toks if isinstance(t, int))
        moved = False

        # drop: a phrase whose uses no longer pay for its header line
        for pi in sorted(range(len(phrases)), key=lambda i: used[i]):
            trial = [p for i, p in enumerate(phrases) if i != pi]
            c = cost(text, trial)
            if c < best:
                best, phrases, moved = c, trial, True
                if verbose:
                    print(f"  drop -> {c}", file=sys.stderr)
                break
        if moved:
            continue

        # add (or swap in, evicting one of the weakest, when full)
        have = set(phrases)
        weakest = sorted(range(len(phrases)), key=lambda i: used[i])[:evict_depth]
        scored = sorted(pool, key=lambda s: -(len(s) - 1) * text.count(s))
        for q in scored:
            if q in have or moved:
                continue
            if len(phrases) < MAX_PHRASES:
                trials = [phrases + [q]]
            else:
                trials = [[p for i, p in enumerate(phrases) if i != w] + [q] for w in weakest]
            for trial in trials:
                c = cost(text, trial)
                if c < best:
                    best, phrases, moved = c, trial, True
                    if verbose:
                        print(f"  {'add' if len(trial) > len(have) else 'swap'} {q!r} -> {c}", file=sys.stderr)
                    break
        if not moved:
            return phrases


def emit(text: str, phrases: list[str]) -> list[int]:
    """The digit stream for a phrase set: header, then relative ring offsets, head carried."""
    head_digits: list[int] = []
    for phrase in phrases:
        head_digits.append(len(phrase))
        head_digits += [ord(c) for c in reversed(phrase)]
    head_digits.append(END)

    slots = len(phrases) + 1  # the year rides in the ring too
    out, head = list(head_digits), 0
    for tok in tokenize(text, phrases):
        if isinstance(tok, str) and tok != YEAR:
            out.append(ord(tok) - 31)
            continue
        target = len(phrases) if tok == YEAR else tok
        step = (target - head) % slots
        out.append(92 + step)
        head = (head + step + 1) % slots
    return out


def main() -> None:
    raw = open(sys.argv[1]).read()
    text = fold_years(raw)

    results: dict[str, tuple[int, list[str]]] = {}
    for rounds in range(30, 61, 2):
        try:
            _, phrases = merge_pairs(text, rounds)
        except ValueError:
            break
        if len(phrases) > MAX_PHRASES:
            break
        c = cost(text, phrases)
        results[f"bpe{rounds}+dp"] = (c, phrases)
        print(f"bpe rounds={rounds}: {len(phrases)} phrases, dp cost {c}", file=sys.stderr)

    seed_name = min(results, key=lambda k: results[k][0])
    seed_cost, seed = results[seed_name]
    print(f"\nseed: {seed_name} at {seed_cost}, refining...", file=sys.stderr)

    pool = candidates(text, 8)
    print(f"pool: {len(pool)} candidate substrings", file=sys.stderr)
    tuned = improve(text, seed, pool)
    final = cost(text, tuned)

    # iterated local search: kick a few phrases out, re-converge, keep the best
    import random

    rng = random.Random(0)
    for kick in range(24):
        jolted = list(tuned)
        for _ in range(3):
            jolted.pop(rng.randrange(len(jolted)))
        trial = improve(text, jolted, pool, verbose=False)
        c = cost(text, trial)
        if c < final:
            final, tuned = c, trial
            print(f"kick {kick}: {c}", file=sys.stderr)
        if final <= 1984 - 31:  # a whole width-83 row of slack: stop
            break

    digits = emit(text, tuned)
    assert len(digits) == final, (len(digits), final)
    assert decode(digits, years=True) == raw
    base = 92 + len(tuned) + 1
    print(f"\nfinal: {final} symbols, base {base}, {len(tuned)} phrases "
          f"(baseline 2029, width-84 needs <=2015)", file=sys.stderr)
    print(" ".join(map(str, digits)))


if __name__ == "__main__":
    main()
