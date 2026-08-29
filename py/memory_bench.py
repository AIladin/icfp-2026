"""Generate `memory` cases at the stated constraint ceiling.

`lm test --problem memory` only ever sees public data, and every public case is one or two
operations. The private ones run to the 1000-token limit, which is ~30x more ticks -- so a score
computed from public cases alone is worthless for optimisation. Score against this instead:

    uv run python memory_bench.py bench.json
    uv run lm test ../programs/memory.man --cases bench.json
"""

import json
import pathlib
import random
import sys

LIMIT = 10**6
ADDRS = 100


def case(name: str, ops: list[tuple[int, int, int]]) -> dict:
    inp: list[str] = []
    out: list[str] = []
    mem: dict[int, int] = {}
    for op, addr, value in ops:
        if op == 1:
            inp += ["1", str(addr), str(value)]
            mem[addr] = value
        else:
            inp += ["0", str(addr)]
            out.append(str(mem.get(addr, 0)))
    return {"name": name, "rounds": [{"in": inp, "out": out}]}


def build() -> list[dict]:
    rng = random.Random(7)

    # every address live, then reads -- worst case for a drum, which scans 2k+1 tokens per operation
    ops = [(1, a, rng.randint(-LIMIT, LIMIT)) for a in range(ADDRS)]
    ops += [(0, rng.randrange(ADDRS), 0) for _ in range(350)]
    ceiling = case("max-1000-tokens-100-addrs", ops)

    writes = [(1, rng.randrange(ADDRS), rng.randint(-LIMIT, LIMIT)) for _ in range(333)]

    sparse_ops = [(1, a, a * 7) for a in range(5)]
    sparse_ops += [(0, rng.randrange(5), 0) for _ in range(492)]

    return [ceiling, case("max-writes", writes), case("max-1000-tokens-5-addrs", sparse_ops)]


if __name__ == "__main__":
    cases = build()
    pathlib.Path(sys.argv[1]).write_text(json.dumps(cases))
    print(f"{len(cases)} cases, input tokens:", [len(c["rounds"][0]["in"]) for c in cases])
