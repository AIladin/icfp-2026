#!/usr/bin/env python3
"""Build independent frame-mismatch probes for the checksum replay machine.

Each mutation remains a valid LLM input. Expected frames are recomputed with the reference model,
not copied from the public case. These cases intentionally are not replay keys.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "py"))

from llm_model import Program  # noqa: E402

PUBLIC = ROOT / "cases-llm.json"
OUT = Path(__file__).resolve().parent / "cases-wrong-frames-more.json"


def mutate_case(
    source: dict,
    *,
    name: str,
    x: int,
    y: int,
    old: str,
    new: str,
    all_rounds: bool,
) -> dict:
    case = copy.deepcopy(source)
    case["name"] = name
    if not all_rounds:
        case["rounds"] = case["rounds"][:1]

    values = list(map(int, case["rounds"][0]["in"]))
    w, h = values[:2]
    chars = [chr(value) for value in values[2:]]
    index = y * w + x
    if chars[index] != old:
        raise ValueError(f"{source['name']} ({x},{y}) is {chars[index]!r}, expected {old!r}")
    chars[index] = new
    case["rounds"][0]["in"] = [str(w), str(h), *(str(ord(ch)) for ch in chars)]

    program = Program(w, h, chars)
    for round_no, rnd in enumerate(case["rounds"]):
        if round_no:
            for _ in range(int(rnd["in"][0])):
                program.step()
        rnd["frames"] = [program.frame()]
    return case


def main() -> None:
    public = json.loads(PUBLIC.read_text())
    probes = [
        mutate_case(
            public[0],
            name="first steps: initial colour H to M",
            x=2,
            y=2,
            old="H",
            new="M",
            all_rounds=False,
        ),
        mutate_case(
            public[0],
            name="first steps: same-colour H to X diverges later",
            x=2,
            y=2,
            old="H",
            new="X",
            all_rounds=True,
        ),
        mutate_case(
            public[1],
            name="countdown relay: same-colour digit 1 to 2",
            x=2,
            y=1,
            old="1",
            new="2",
            all_rounds=True,
        ),
        mutate_case(
            public[2],
            name="hello neighbor: initial colour H to M",
            x=4,
            y=1,
            old="H",
            new="M",
            all_rounds=False,
        ),
        mutate_case(
            public[5],
            name="switchboard: initial empty cell to M",
            x=2,
            y=7,
            old=" ",
            new="M",
            all_rounds=False,
        ),
        mutate_case(
            public[7],
            name="coin toss: initial empty cell to M",
            x=4,
            y=1,
            old=" ",
            new="M",
            all_rounds=False,
        ),
    ]
    OUT.write_text(json.dumps(probes, indent=2) + "\n")
    for case in probes:
        checksum = sum(map(int, case["rounds"][0]["in"]))
        print(f"{checksum:5d}  {case['name']}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
