"""Generate a fuzz case file for `tcp` in `icfp tests` JSON shape."""

import json
import random
import sys


def make(name: str, order: list[int], vals: dict[int, int]) -> dict:
    n = len(order)
    rounds = []
    want = 0
    buf: dict[int, int] = {}
    for i, seq in enumerate(order):
        v = vals[seq]
        ins = [str(n)] if i == 0 else []
        ins += [str(seq), str(v)]
        if seq >= want + 16:
            rounds.append({"in": ins, "out": ["-1"]})
            break
        buf[seq] = v
        out = []
        while want in buf:
            out.append(str(buf.pop(want)))
            want += 1
        rounds.append({"in": ins, "out": out})
    return {"name": name, "rounds": rounds}


def rand_vals(n: int, rng: random.Random) -> dict[int, int]:
    return {i: rng.randint(1, 999) for i in range(n)}


def legal_order(n: int, rng: random.Random) -> list[int]:
    """A permutation that never trips `seq >= want + 16`."""
    order: list[int] = []
    seen: set[int] = set()
    remaining = set(range(n))
    want = 0
    while remaining:
        pool = [s for s in remaining if s < want + 16]
        s = rng.choice(pool)
        order.append(s)
        seen.add(s)
        remaining.discard(s)
        while want in seen:
            want += 1
    return order


def main(path: str, count: int = 60) -> None:
    rng = random.Random(20260725)
    cases: list[dict] = []

    # deterministic edge cases
    cases.append(make("n1", [0], {0: 42}))
    cases.append(make("n2-rev", [1, 0], {0: 7, 1: 8}))
    cases.append(make("n48-inorder", list(range(48)), rand_vals(48, rng)))
    cases.append(make("n48-rev", list(range(47, -1, -1)), rand_vals(48, rng)))
    cases.append(make("n16-rev", list(range(15, -1, -1)), rand_vals(16, rng)))
    # boundary: seq == want+15 is legal, want+16 is loss
    cases.append(make("edge-15-ok", [15] + list(range(15)), rand_vals(16, rng)))
    cases.append(make("edge-16-loss", [16] + list(range(16)), rand_vals(17, rng)))
    # loss only after a partial drain shifts `want`
    cases.append(make("edge-shifted", [0, 1, 17] + [2], rand_vals(18, rng)))
    cases.append(make("edge-shifted-ok", [0, 1, 16] + [2], rand_vals(18, rng)))
    # full window then release
    cases.append(make("window-full", list(range(1, 16)) + [0], rand_vals(16, rng)))
    cases.append(make("n17-blocks", [15, 14, 13, 12] + list(range(12)) + [16], rand_vals(17, rng)))

    for k in range(count):
        n = rng.randint(1, 48)
        order = list(range(n))
        rng.shuffle(order)
        cases.append(make(f"rand{k}-n{n}", order, rand_vals(n, rng)))

    # legal (never-lossy) scrambles: only reorder inside a sliding window
    for k in range(count):
        n = rng.randint(2, 48)
        order = legal_order(n, rng)
        cases.append(make(f"legal{k}-n{n}", order, rand_vals(n, rng)))

    with open(path, "w") as f:
        json.dump(cases, f)
    print(f"{len(cases)} cases -> {path}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 60)
