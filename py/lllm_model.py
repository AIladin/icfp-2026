"""Reference model for little-little-little-man.

Validates the op/colour tables and the frame rules that `py/lllm_gen.py` compiles into a
.man program, against the 10 public cases.  Nothing here ends up in the grid; it exists so
that a frame mismatch can be blamed on the littleman machine and not on the semantics.
"""

from __future__ import annotations

import json
import sys

# op codes stored in the ring (4 bits) -------------------------------------------------
OP_E, OP_S, OP_W, OP_N = 0, 1, 2, 3
OP_HALT_H, OP_HALT_WALL, OP_NOP, OP_SETA = 4, 5, 6, 7
OP_M, OP_PLUS, OP_MINUS, OP_X = 8, 9, 10, 11

COLOUR = {
    OP_E: 3, OP_S: 3, OP_W: 3, OP_N: 3,
    OP_HALT_H: 3, OP_HALT_WALL: 4, OP_NOP: 0, OP_SETA: 8,
    OP_M: 12, OP_PLUS: 10, OP_MINUS: 10, OP_X: 3,
}

# ascii -> op, for cells that are not room walls
CHAR_OP = {
    32: OP_NOP, 64: OP_NOP,
    43: OP_PLUS, 45: OP_MINUS,
    60: OP_W, 62: OP_E, 94: OP_N, 118: OP_S, 86: OP_S,
    72: OP_HALT_H, 77: OP_M, 88: OP_X, 124: OP_HALT_WALL,
}

COLTAB = sum(COLOUR[op] << (4 * op) for op in range(12))


def classify(c: int) -> tuple[int, int]:
    """ascii -> (op, payload).  Walls are pre-substituted to `|` by the loader."""
    if 48 <= c <= 57:
        return OP_SETA, c - 48
    return CHAR_OP[c], 0


def load(w: int, h: int, cells: list[int]) -> tuple[list[int], int]:
    """Pad the program to 16x16 and return (ring of 256 codes, man index)."""
    ring: list[int] = []
    man = -1
    for y in range(16):
        for x in range(16):
            if x >= w or y >= h:
                ring.append(OP_NOP)
                continue
            c = cells[y * w + x]
            if y == 0 or y == h - 1:
                c = 124  # every cell of the top/bottom border row is a wall
            if c == 64:
                man = y * 16 + x
            op, payload = classify(c)
            ring.append(op | (payload << 4))
    assert man >= 0
    return ring, man


DELTA = {0: 1, 1: 16, 2: -1, 3: -16, 4: 0}


def run_case(case: dict) -> list[list[str]]:
    r0 = case["rounds"][0]["in"]
    w, h = int(r0[0]), int(r0[1])
    ring, pos = load(w, h, [int(v) for v in r0[2:]])

    pix = [0] * 256
    for i, code in enumerate(ring):
        pix[i] = COLOUR[code & 15]
    pix[pos] = 9

    frames = [render(pix)]
    ia = ib = 0
    dirn = 0
    for rnd in case["rounds"][1:]:
        k = int(rnd["in"][0])
        for _ in range(k):
            code = ring[pos]
            op, payload = code & 15, code >> 4
            if op == OP_SETA:
                ia = payload
            elif op == OP_M:
                ib = ia
            elif op == OP_PLUS:
                ia += ib
            elif op == OP_MINUS:
                ia -= ib
            elif op == OP_X:
                if ia > 0:
                    dirn = (dirn + 1) % 4
                elif ia < 0:
                    dirn = (dirn - 1) % 4
            elif op in (OP_E, OP_S, OP_W, OP_N):
                dirn = op
            elif op in (OP_HALT_H, OP_HALT_WALL):
                dirn = 4
            pix[pos] = COLOUR[code & 15]
            pos += DELTA[dirn]
            pix[pos] = 9
        frames.append(render(pix))
    return frames


def render(pix: list[int]) -> list[str]:
    return ["".join(f"{pix[y * 16 + x]:x}" for x in range(16)) for y in range(16)]


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "lllm-cases.json"
    cases = json.load(open(path))
    bad = 0
    for case in cases:
        got = run_case(case)
        want = [r["frames"][0] for r in case["rounds"]]
        if got == want:
            print(f"ok   {case['name']}")
            continue
        bad += 1
        print(f"FAIL {case['name']}")
        for i, (g, e) in enumerate(zip(got, want)):
            if g != e:
                print(f"  frame {i}")
                for a, b in zip(g, e):
                    print(f"    {a}  {b}  {'' if a == b else '<<'}")
                break
    print(f"COLTAB = {COLTAB}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
