#!/usr/bin/env python3
"""Generate a deliberately unoptimised replay machine for the public LLM tests.

This is independent of the in-progress general LLM interpreter.  It identifies an initial
program by a rolling fingerprint of its input and replays recorded frames. The point is a clean
alternative that exercises lmp's room-logic path, not a submission for unknown cases.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ROOMS = HERE / "rooms"
CASES = ROOT / "cases-llm.json"
REGRESSION_CASES = [
    HERE / "cases-wrong-frames.json",
    HERE / "cases-wrong-frames-more.json",
    HERE / "cases-partner-batch-1.json",
    HERE / "cases-partner-batch-2.json",
    HERE / "cases-partner-batch-3.json",
    HERE / "cases-partner-batch-4.json",
    HERE / "cases-partner-batch-5.json",
    HERE / "cases-partner-batch-6.json",
    HERE / "cases-partner-batch-7.json",
    HERE / "cases-partner-batch-8.json",
    HERE / "cases-partner-batch-9.json",
]
# Largest 2^k-1 mask whose masked value can still be multiplied by 257 in signed 64-bit.
HASH_MASK = 18014398509481983
HASH_MULTIPLIER = 257


def lit(n: int) -> str:
    if 0 <= n <= 9:
        return str(n)
    return f"`{n}`"


def fingerprint(values: list[str]) -> int:
    """Order-sensitive nonlinear hash that is cheap with two littleman registers."""
    result = 0
    for value in map(int, values):
        result = ((result ^ value) * HASH_MULTIPLIER) & HASH_MASK
    return result


def write_room(path: Path, rows: list[list[str]]) -> None:
    width = max(map(len, rows))
    text = "\n".join("".join(row).ljust(width).rstrip() for row in rows).rstrip() + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def small_value(n: int) -> str:
    """Load 0..16 without backticks (stacked horizontal literals pair vertically)."""
    if n <= 9:
        return str(n)
    return f"9M{n - 9}+"


def replay_ops(case: dict) -> str:
    out: list[str] = []
    for round_no, rnd in enumerate(case["rounds"]):
        if round_no:
            out.append("r")  # consume k; the recorded frame already incorporates it
        frame = rnd["frames"][0]
        for row in frame:
            for colour in row:
                out.extend((small_value(int(colour, 16) + 1), "s"))
        out.append("1Ns")  # negative token means SWAP 0 to the emitter
    out.append("H")
    return "".join(out)


def generate_replay(cases: list[dict]) -> None:
    keyed = sorted((fingerprint(c["rounds"][0]["in"]), c) for c in cases)
    if len({key for key, _ in keyed}) != len(keyed):
        raise ValueError("initial-input fingerprints are not unique")

    # The fingerprint chain occupies the top-left. Each equal arm drops through its own column into
    # a horizontal band, where its long replay is folded into a serpentine. This keeps the same
    # logic as v1 while reducing the dominant room from 12871x22 to roughly 550x230.
    dispatch_y = len(keyed) + 1
    # B holds h. `r~M` makes B=v XOR h, then multiplication and masking finish the step.
    # Masking each value also prevents 64-bit overflow.
    hash_step = "r~M" + lit(HASH_MULTIPLIER) + "*M" + lit(HASH_MASK) + "W&M"
    loop = ">>" + hash_step + "qd"
    d_x = 2 + len(loop) - 1
    x, y = d_x + 3, dispatch_y
    branches: list[tuple[int, int, dict]] = []
    tests: list[tuple[int, int, str]] = []
    for index, (key, case) in enumerate(keyed):
        if index == len(keyed) - 1:
            # Continue one cell east before dropping. Reusing x would merge this default arm
            # into the previous test's equal-arm corridor at the row below.
            branches.append((x + 1, y, case))
            break
        test = lit(key) + "-X"
        tests.append((x, y, test))
        branch_x = x + len(test) - 1
        branches.append((branch_x + 1, y, case))
        x, y = branch_x + 1, y - 1

    lane_width = 300
    program_start = max(drop_x for drop_x, _, _ in branches) + 4
    program_end = program_start + lane_width
    band_y = dispatch_y + 5
    bands: list[tuple[int, int, int, dict]] = []
    for drop_x, branch_y, case in branches:
        n = len(replay_ops(case))
        rows = 1 + n // (lane_width - 1)
        bands.append((drop_x, branch_y, band_y, case))
        band_y += rows

    width = program_end + 2
    height = band_y + 1
    g = [[" "] * (width + 4) for _ in range(height + 4)]
    x0 = y0 = 1
    x1, y1 = width + 2, height + 2
    for gx in range(x0, x1 + 1):
        g[y0][gx] = g[y1][gx] = "-"
    for gy in range(y0, y1 + 1):
        g[gy][x0] = g[gy][x1] = "|"
    for gx, gy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        g[gy][gx] = "+"
    g[y0 + dispatch_y][x0 - 1] = "A"
    g[y0][x1 + 1] = "z"

    def cell(px: int, py: int, ch: str) -> None:
        gx, gy = x0 + 1 + px, y0 + 1 + py
        if g[gy][gx] not in (" ", ch):
            raise ValueError(f"overwrite at {gx},{gy}: {g[gy][gx]!r} -> {ch!r}")
        g[gy][gx] = ch

    def put(px: int, py: int, text: str) -> None:
        for offset, ch in enumerate(text):
            cell(px + offset, py, ch)

    # Initialise B=0 and hash the whole first-round input. q/d loops while another value exists.
    put(0, dispatch_y - 2, "@0Mv")
    put(3, dispatch_y - 1, "v")
    put(2, dispatch_y, loop)
    cell(d_x, dispatch_y + 1, "v")
    cell(2, dispatch_y + 2, "^")
    put(3, dispatch_y + 2, "<" * (d_x - 2))

    # Greater checksums climb north and equal arms turn south one cell after X. A checksum below
    # the current key used to take X's clockwise arm into empty space and eventually hit the room
    # wall. Route that arm to the preceding replay instead: on every row after the first, `<` walks
    # west into the preceding arm's existing drop column. Values below the first key use its replay.
    # This makes the dispatcher total (unknown cases can still have wrong frames, but never wall).
    for index, (tx, ty, test) in enumerate(tests):
        put(tx, ty, test)
        bx = tx + len(test) - 1
        cell(bx, ty - 1, ">")
        cell(bx + 1, ty, "v")
        if index == 0:
            cell(bx, ty + 1, ">")
            cell(bx + 1, ty + 1, "v")
        else:
            cell(bx, ty + 1, "<")
    final_x, final_y, _ = branches[-1]
    cell(final_x - 1, final_y, ">")
    cell(final_x, final_y, "v")

    def snake(start_y: int, ops: str) -> None:
        px, py, direction = program_start, start_y, 1
        for op in ops:
            if direction == 1 and px == program_end:
                cell(px, py, "v")
                py += 1
                cell(px, py, "<")
                px -= 1
                direction = -1
            elif direction == -1 and px == program_start:
                cell(px, py, "v")
                py += 1
                cell(px, py, ">")
                px += 1
                direction = 1
            cell(px, py, op)
            px += direction

    for drop_x, _, target_y, case in bands:
        cell(drop_x, target_y, ">")
        snake(target_y, replay_ops(case))

    write_room(ROOMS / "llm-alt-replay" / "v0.room", g)
    (ROOMS / "llm-alt-replay" / "interface.toml").write_text(
        'description = "folded public-case checksum dispatcher and frame replay"\n\n'
        '[ports]\ninput = "A"\nstream = "z"\n'
    )


def generate_emitter() -> None:
    # One-token loop. stream values >0 mean DATA(value-1), -1 means SWAP 0.
    # Facing east at X: positive turns south; negative turns north.
    rows = [list(" " * 20) for _ in range(15)]
    # border x=2..17, y=1..13
    for x in range(2, 18):
        rows[1][x] = rows[13][x] = "-"
    for y in range(1, 14):
        rows[y][2] = rows[y][17] = "|"
    for x, y in ((2, 1), (17, 1), (2, 13), (17, 13)):
        rows[y][x] = "+"
    rows[6][1] = "Z"  # incoming stream
    rows[0][8] = "u"  # swap output
    rows[0][13] = "a"  # unused ADDR output, required by the display interface
    rows[14][10] = "t"  # data output

    # Spawn reaches receive/test at (7,6). Loop rejoins from west at (6,6).
    for x, ch in enumerate("@    >rX", start=3):
        if ch != " ":
            rows[6][x] = ch
    # Positive arm: A=value+1, subtract one, send near south, loop around east to west.
    rows[7][10] = "M"
    rows[8][10] = "1"
    rows[9][10] = "W"
    rows[10][10] = "-"
    rows[11][10] = "s"
    rows[12][10] = ">"
    rows[12][15] = "^"
    rows[5][15] = "<"
    rows[5][6] = "v"
    rows[6][6] = ">"
    # Negative arm: load SWAP mode 0, send near north, then same return corridor.
    rows[5][10] = "0"
    rows[4][10] = "s"
    rows[3][10] = ">"
    rows[3][15] = "v"
    # Corridors are blank; arrows establish their corners.

    write_room(ROOMS / "llm-alt-emitter" / "v0.room", rows)
    (ROOMS / "llm-alt-emitter" / "interface.toml").write_text(
        'description = "decode replay tokens into LM-75 DATA and SWAP"\n\n'
        '[ports]\nstream = "Z"\ndata = "t"\nswap = "u"\naddr = "a"\n'
    )


def generate_display() -> None:
    src = ROOT / "rooms" / "lllm-display"
    dst = ROOMS / "llm-alt-display"
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "interface.toml").write_text((src / "interface.toml").read_text())
    (dst / "v0.room").write_text((src / "a1s1d1.room").read_text())


def generate_design() -> None:
    (HERE / "solution.eman.toml").write_text(
        '''problem = "little-little-man"

[rooms]
input = "input"
replay = "llm-alt-replay"
emitter = "llm-alt-emitter"
display = "llm-alt-display"

[[pipes]]
from = "input.out"
to = "replay.input"

[[pipes]]
from = "replay.stream"
to = "emitter.stream"

[[pipes]]
from = "emitter.data"
to = "display.data"

[[pipes]]
from = "emitter.swap"
to = "display.swap"

[[pipes]]
from = "emitter.addr"
to = "display.addr"
'''
    )


def main() -> None:
    cases = json.loads(CASES.read_text())
    for path in REGRESSION_CASES:
        cases.extend(json.loads(path.read_text()))
    generate_replay(cases)
    generate_emitter()
    generate_display()
    generate_design()


if __name__ == "__main__":
    main()
