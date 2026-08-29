"""Per-tick tracing and failure reports.

A trace line is one man executing one instruction:

    t=00007 (3,1) E A=42 B=0 BP=0 '*'
    t=00008 (4,1) E A=42 B=0 BP=0 's' blocked
"""

import sys
from typing import TextIO

from .grid import Grid
from .judge import RunResult
from .machine import Frame, Machine, Man
from .model import DIR_NAMES, Program


class Tracer:
    """Prints the machine's state as it runs. Pass an instance as ``trace=`` to a run."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self.stream = stream if stream is not None else sys.stderr
        self._last_tick = -1

    def step(self, machine: Machine, man: Man, char: str) -> None:
        self._pipes_once(machine)
        flags = " blocked" if man.blocked else (" stopped" if man.stopped else "")
        print(
            f"t={machine.tick:05d} ({man.x},{man.y}) {DIR_NAMES[man.dir]} "
            f"A={man.a} B={man.b} BP={man.bp} {char!r}{flags}",
            file=self.stream,
        )

    def device(self, machine: Machine, display: int, port: str, value: int) -> None:
        self._pipes_once(machine)
        screen = machine.screens[display]
        column, row = screen.cursor % screen.display.width, screen.cursor // screen.display.width
        print(
            f"t={machine.tick:05d} display {display} {port} {value} "
            f"cursor=({column},{row}) frames={machine.frame_count}",
            file=self.stream,
        )

    def _pipes_once(self, machine: Machine) -> None:
        """Pipe occupancy, printed once per tick before whatever else that tick did."""
        if machine.tick == self._last_tick:
            return
        self._last_tick = machine.tick
        pipes = _pipes(machine)
        if pipes:
            print(f"t={machine.tick:05d} pipes {pipes}", file=self.stream)


def _pipes(machine: Machine) -> str:
    parts = [
        f"#{index}=[{','.join('_' if slot is None else str(slot) for slot in slots)}]"
        for index, slots in enumerate(machine.pipes)
        if any(slot is not None for slot in slots)
    ]
    return " ".join(parts)


def summary(program: Program) -> str:
    """What the loader made of the program — the first thing to check when a run misbehaves."""
    width, height = program.grid.footprint()
    lines = [
        f"{width}x{height} grid, footprint {program.footprint()}",
        f"{len(program.rooms)} room(s), {len(program.pipes)} pipe(s), "
        f"{len(program.spawns)} little man/men",
    ]
    for index, room in enumerate(program.rooms):
        kind = "" if room.kind == "room" else f" [{room.kind}]"
        spawn = f" @{room.spawn}" if room.spawn else ""
        lines.append(
            f"  room {index}{kind} ({room.x0},{room.y0})-({room.x1},{room.y1}){spawn} "
            f"out={room.outgoing} in={room.incoming}"
        )
    for display in program.displays:
        room = program.rooms[display.room]
        ports = ", ".join(f"{name}=#{index}" for name, index in display.ports()) or "no pipes"
        lines.append(
            f"  display ({room.x0},{room.y0})-({room.x1},{room.y1}) "
            f"{display.width}x{display.height}, {ports}"
        )
    for index, pipe in enumerate(program.pipes):
        lines.append(
            f"  pipe {index} room {pipe.src_room} {pipe.source} -> room {pipe.dst_room} "
            f"{pipe.dest}, {len(pipe.cells)} cell(s)"
        )
    return "\n".join(lines)


def frame_diff(expected: Frame, got: Frame) -> str:
    """Expected beside committed, with every differing pixel marked underneath."""
    width = max((len(row) for row in expected + got), default=0)
    lines = [f"  {'expected':<{width}}   committed"]
    for index in range(max(len(expected), len(got))):
        want = expected[index] if index < len(expected) else ""
        have = got[index] if index < len(got) else ""
        marks = "".join(
            " " if i < len(want) and i < len(have) and want[i] == have[i] else "^"
            for i in range(max(len(want), len(have)))
        )
        lines.append(f"  {want:<{width}}   {have:<{width}}   {marks}")
    return "\n".join(lines)


def failure_report(grid: Grid, result: RunResult) -> str:
    """Why a case failed, with the divergence marked and the offending cell shown."""
    lines = [f"{result.error}: {result.detail}"]
    if result.expected_frames:
        lines.append(
            f"  {result.matched_frames}/{len(result.expected_frames)} frame(s) matched"
        )
        # The frame that failed is the one after the last match, and machine.frames ends with it.
        if result.frames and result.matched_frames < len(result.expected_frames):
            lines.append(
                frame_diff(result.expected_frames[result.matched_frames], result.frames[-1])
            )
    if result.expected:
        expected = " ".join(str(value) for value in result.expected)
        emitted = " ".join(str(value) for value in result.output)
        lines.append(f"  expected: {expected}")
        lines.append(f"  emitted:  {emitted}")
        marker = len(" ".join(str(value) for value in result.output[: result.matched]))
        lines.append("            " + " " * (marker + (1 if result.matched else 0)) + "^")
    if result.cell is not None:
        lines.append(grid.excerpt(*result.cell))
    return "\n".join(lines)
