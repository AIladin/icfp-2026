"""Smoke tests for `llm_asm`: build a one-room program, run it, compare the output."""

from __future__ import annotations

import json
import subprocess
import tempfile

from lllm_lay import Grid, lit
from llm_asm import Forever, If, Loop, Ops, SGrid, Seq, While


def build(prog) -> str:
    g = SGrid()
    x1, y1, _oy = prog.place(g, 2, 1)
    out = Grid(x1 + 12, y1 + 9)
    out.room(0, 0, x1 + 1, y1 + 1)
    for (x, y), ch in g.c.items():
        out.put(x, y, ch, over=True)
    out.put(1, 1 + prog.entry_dy, "@", over=True)
    # a pipe east out of the room into a 3x3 output room
    py = 1 + prog.entry_dy
    out.put(x1 + 2, py, ">")
    out.put(x1 + 3, py, ">")
    out.room(x1 + 4, py - 1, x1 + 6, py + 1)
    out.put(x1 + 5, py, "O")
    # an input room under the south wall (the CPU has one pipe each way, so placement is free)
    out.put(3, y1 + 3, "^")
    out.put(3, y1 + 2, "^")
    out.room(2, y1 + 4, 4, y1 + 6)
    out.put(3, y1 + 5, "I")
    return out.render()


def run(prog, expect: list[int], name: str, prefix: bool = False, stdin: str = "") -> bool:
    src = build(prog)
    with tempfile.NamedTemporaryFile("w", suffix=".man", delete=False) as f:
        f.write(src)
        path = f.name
    cmd = ["lmr", "run", path, "--json"] + (["--input", stdin] if stdin else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except ValueError:
        print(f"FAIL {name}: {r.stdout[-300:]}{r.stderr[-300:]}")
        return False
    got = [int(v) for v in d.get("output", [])]
    ok = got[: len(expect)] == expect if prefix else got == expect
    print(f"{'ok  ' if ok else 'FAIL'} {name:22s} got={got[:8]} want={expect[:8]} ticks={d.get('ticks')}")
    if not ok:
        print(src)
    return ok


def main() -> int:
    bad = 0
    bad += not run(Seq(Ops("5s"), Ops("H")), [5], "straight line")
    bad += not run(Seq(Ops("1s2s3s"), Ops("H")), [1, 2, 3], "several sends")
    bad += not run(Seq(Ops(lit(3) + "b"), Loop(Ops("7s")), Ops("9sH")), [7, 7, 7, 9], "loop 3")
    bad += not run(Seq(Ops("0b"), Loop(Ops("7s")), Ops("9sH")), [9], "loop 0")
    bad += not run(Seq(Ops("5"), If(Ops("1s"), Ops("2s"), Ops("3s")), Ops("9sH")), [3, 9], "if pos")
    bad += not run(Seq(Ops("0"), If(Ops("1s"), Ops("2s"), Ops("3s")), Ops("9sH")), [2, 9], "if zero")
    bad += not run(Seq(Ops("5N"), If(Ops("1s"), Ops("2s"), Ops("3s")), Ops("9sH")), [1, 9], "if neg")
    bad += not run(
        Seq(Ops(lit(2) + "b"), Loop(Seq(Ops("1s"), Ops("2s"))), Ops("9sH")),
        [1, 2, 1, 2, 9],
        "loop of seq",
    )
    bad += not run(
        Seq(
            Ops(lit(2) + "b"),
            Loop(Seq(Ops("4"), If(zero=Ops("8s"), pos=Ops("5s")))),
            Ops("9sH"),
        ),
        [5, 5, 9],
        "loop of if",
    )
    bad += not run(
        Seq(Ops("3"), If(pos=Seq(Ops(lit(2) + "b"), Loop(Ops("6s")))), Ops("9sH")),
        [6, 6, 9],
        "if of loop",
    )
    bad += not run(Seq(Ops("1s"), Forever(Ops("2s"))), [1, 2, 2, 2], "forever", prefix=True)
    bad += not run(
        Seq(While(Ops("r"), Ops("7s")), Ops("9sH")), [7, 7, 7, 9], "while", stdin="3 2 1 0"
    )
    bad += not run(
        Seq(While(Ops("r"), Seq(Ops("6"), If(pos=Ops("5s")), Ops("8s"))), Ops("9sH")),
        [5, 8, 5, 8, 9],
        "while of if",
        stdin="1 1 0",
    )
    print("all good" if not bad else f"{bad} failures")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
