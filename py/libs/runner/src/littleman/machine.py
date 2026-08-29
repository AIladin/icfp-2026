"""The machine: little men walking the grid, and the four-phase tick loop.

> Within one tick, in order:
> 1. Pipes shift ... 2. I/O ... 3. Execution ... 4. Movement
> — language-reference#Tick order

Until `Y` (Split) arrived, executing the men sequentially in reading order was equivalent to
executing them simultaneously: a room held at most one man, a pipe has exactly one source room and
one destination room, and a pipe's source and destination cells are always distinct (pipes are at
least 2 cells long). So no two men could ever touch the same pipe cell within one phase.

`Y` breaks the one-man-per-room premise, and the spec replaces it with an explicit order:

> Little men act in creation order, every tick. On a split, the copy born to the right takes over
> the splitting man's place in that order; the copy born to the left becomes the newest little man
> and acts after all others. — split#Y, precisely

``self.men`` *is* that order, so the right copy is spliced in at the splitter's index and the left
copy is appended. Removing the dead never reorders the living.
"""

from dataclasses import dataclass
from typing import Protocol

from .errors import RunError
from .model import DELTAS, EAST, NORTH, SOUTH, WEST, Cell, Display, Program

# > The maximum number of live little men is 65536. Exceeding this limit is an error and ends your
# > program. — split#Y, precisely
MAX_MEN = 65536

_UINT64 = 0xFFFFFFFFFFFFFFFF
_SIGN_BIT = 1 << 63
_LOAD_CHARS = frozenset("0123456789`")
_HEX = "0123456789abcdef"
# Committed frames are kept only for reports and `lm run`; the judge compares them streaming, so a
# program that swaps every tick must not be able to fill memory with its own history.
_FRAME_HISTORY = 64

# One committed frame in the contest's wire format: `height` rows of `width` hex digits.
type Frame = tuple[str, ...]


def wrap(value: int) -> int:
    """Every value in the language is a signed 64-bit integer; arithmetic wraps silently."""
    value &= _UINT64
    return value - (1 << 64) if value & _SIGN_BIT else value


@dataclass(slots=True)
class Man:
    room: int
    x: int
    y: int
    dir: int = EAST
    a: int = 0
    b: int = 0
    bp: int = 0
    stopped: bool = False
    blocked: bool = False
    # Placed by a `Y` during this tick's execution phase. A newborn is already *on* his cell, so he
    # skips the movement phase he was born in and executes that cell on the next tick — exactly as
    # if he had walked onto it. Cleared by the movement phase.
    born: bool = False
    # A wall step is fatal, but not until the man would *execute* on the cell — the next tick's I/O
    # phase runs first, so a value still in the output pipe is emitted before the run dies. Confirmed
    # against the server 2026-07-24; see `Output survives the wall error` in the vault.
    fault: RunError | None = None


class Io(Protocol):
    """How the machine talks to the judge: input it may release, output it must account for."""

    def take(self) -> int | None:
        """The next input value, or None when nothing is released yet (a withheld round)."""

    def emit(self, value: int, tick: int) -> bool:
        """Consume an output value; return False to end the run (passed, or failed on a mismatch)."""

    def commit(self, frame: Frame, tick: int) -> bool:
        """Account for a frame an LM-75 just swapped in. Same contract as ``emit``."""


class Tracer(Protocol):
    """Where a run reports what it just did, one call per event."""

    def step(self, machine: "Machine", man: Man, char: str) -> None: ...

    def device(self, machine: "Machine", display: int, port: str, value: int) -> None: ...


class Screen:
    """One LM-75's state: two buffers of colour indices, and the cursor into ``next``.

    > The current and next buffers are initially filled with color 0 (black). The cursor begins at
    > position 0, 0. — language-reference#The LM-75 Display
    """

    __slots__ = ("current", "cursor", "display", "next")

    def __init__(self, display: Display) -> None:
        self.display = display
        self.current = bytearray(display.pixels)
        self.next = bytearray(display.pixels)
        self.cursor = 0

    def frame(self) -> Frame:
        """The current buffer in the wire format: one lowercase hex digit per pixel, row by row."""
        width = self.display.width
        return tuple(
            "".join(_HEX[colour] for colour in self.current[start : start + width])
            for start in range(0, len(self.current), width)
        )


class Machine:
    def __init__(self, program: Program, io: Io, *, trace: Tracer | None = None) -> None:
        self.program = program
        self.io = io
        self.trace = trace
        self.pipes: list[list[int | None]] = [[None] * len(pipe.cells) for pipe in program.pipes]
        self.men = [Man(room, cell[0], cell[1]) for room, cell in program.spawns]
        self.screens = [Screen(display) for display in program.displays]
        self.output: list[int] = []
        # The last _FRAME_HISTORY committed frames, for reports; frame_count is the real total.
        self.frames: list[Frame] = []
        self.frame_count = 0
        self.tick = 0
        # Two men can only ever share a cell if the program can split: a room holds at most one
        # `@`, so without `Y` every man has a room to himself and the collision rules are dead
        # letters. Deciding it once here keeps the per-tick scan off every program that never
        # splits. A test that places men by hand sets this itself.
        self.can_collide = any("Y" in row for row in program.grid.rows)

    def run(self, max_ticks: int) -> str:
        """Run to completion. Returns 'halted', 'judged' (the io ended it), or 'step-cap'."""
        while self.tick < max_ticks:
            if all(man.stopped for man in self.men):
                return self._drain(max_ticks)
            self.tick += 1
            self._shift_pipes()
            if not self._transfer_io():
                return "judged"
            if not self._execute_all():
                return "judged"
            if not self._display_step():
                return "judged"
            self._move_all()
        return "step-cap"

    def _drain(self, max_ticks: int) -> str:
        """> pipes and I/O rooms keep ticking until the output pipe drains — Tick order fine print

        Display pipes are drained too, so a SWAP still in flight when the last man halts commits
        rather than being lost. The reference names only the output pipe; see the runner's CLAUDE.md.
        """
        while self.tick < max_ticks:
            if not self._in_flight():
                return "halted"
            self.tick += 1
            self._shift_pipes()
            if not self._transfer_io():
                return "judged"
            if not self._display_step():
                return "judged"
        return "step-cap"

    def _in_flight(self) -> bool:
        """Whether any value is still on its way to the output room or to a display."""
        out = self.program.output_pipe
        if out is not None and any(slot is not None for slot in self.pipes[out]):
            return True
        return any(
            slot is not None
            for display in self.program.displays
            for _, index in display.ports()
            for slot in self.pipes[index]
        )

    def _shift_pipes(self) -> None:
        for slots in self.pipes:
            for i in range(len(slots) - 1, 0, -1):
                if slots[i] is None and slots[i - 1] is not None:
                    slots[i] = slots[i - 1]
                    slots[i - 1] = None

    def _transfer_io(self) -> bool:
        out = self.program.output_pipe
        if out is not None:
            slots = self.pipes[out]
            value = slots[-1]
            if value is not None:
                slots[-1] = None
                self.output.append(value)
                if not self.io.emit(value, self.tick):
                    return False
        source = self.program.input_pipe
        if source is not None:
            slots = self.pipes[source]
            if slots[0] is None:
                value = self.io.take()
                if value is not None:
                    slots[0] = value
        return True

    def _execute_all(self) -> bool:
        grid = self.program.grid
        split = False
        # `len` is read once: a left copy appended by a split does not execute on the tick it was
        # born, and a right copy has already been passed by the time it replaces its splitter.
        for index in range(len(self.men)):
            man = self.men[index]
            if man.stopped or man.born:
                continue
            if man.fault is not None:
                raise man.fault
            char = grid.at(man.x, man.y)
            if char == "Y":
                self._split(index, man)
                split = True
            else:
                self._execute(man, char)
            if self.trace is not None:
                self.trace.step(self, man, char)
        if split:
            # Births are the only way two men can end the execution phase on one cell, so this scan
            # covers both "born onto an occupant" and "two `Y`s spawning onto the same cell".
            self._cull(self._overlaps())
        return True

    def _split(self, index: int, man: Man) -> None:
        """`Y`: two copies born beside the splitter, each heading away from him.

        > `Y` splits the little man in two. The copies are born on the cells to his left and his
        > right — left and right relative to his heading as he enters the `Y` — each heading away
        > from the `Y`. The original man does not continue past the `Y`; only the two copies remain.
        > — split#Y, precisely

        Directions are clockwise, so right of the heading is ``dir + 1`` and left is ``dir - 1``.
        `Y` is unconditional: both births happen (or raise) whatever is standing there.
        """
        right = self._birth(man, (man.dir + 1) % 4)
        left = self._birth(man, (man.dir - 1) % 4)
        self.men[index] = right
        self.men.append(left)
        if len(self.men) > MAX_MEN:
            raise RunError(
                "population",
                f"a split took the population past {MAX_MEN} live little men",
                (man.x, man.y),
            )

    def _birth(self, man: Man, direction: int) -> Man:
        """One copy, on the cell one step ``direction`` from the splitter and facing that way.

        > If the birth cell is a wall, the program halts with an error. — split#Y, precisely

        Any cell that is not room interior is a wall here, exactly as it is for a step (assumption
        5 in the runner's CLAUDE.md) — a room's own border, another room, a pipe, or open paper.
        """
        dx, dy = DELTAS[direction]
        cell = (man.x + dx, man.y + dy)
        room = self.program.room_of.get(cell)
        if room is None:
            raise RunError(
                "wall",
                f"a little man was split into the wall at ({cell[0]},{cell[1]}) "
                f"from ({man.x},{man.y})",
                cell,
            )
        return Man(room, cell[0], cell[1], direction, man.a, man.b, man.bp, born=True)

    def _overlaps(self) -> set[int]:
        """Indices of men sharing a cell with another man. Both parties die, and it is not an error.

        > If two little men in the same room collide, they both die. This is not an error.
        > — split#Y, precisely
        """
        seen: dict[Cell, int] = {}
        doomed: set[int] = set()
        for index, man in enumerate(self.men):
            other = seen.setdefault((man.x, man.y), index)
            if other != index:
                doomed.add(other)
                doomed.add(index)
        return doomed

    def _cull(self, doomed: set[int]) -> None:
        """Drop the dead. Survivors keep their relative order, which *is* the creation order."""
        if doomed:
            self.men = [man for index, man in enumerate(self.men) if index not in doomed]

    def _display_step(self) -> bool:
        """> Displays consume and process input. — Tick order, phase 3

        > The display can read a value from all 3 of its pipes in the same tick. The display
        > processes ADDR first, then DATA, then SWAP. — language-reference#The LM-75 Display

        Running this after the men is safe either way: a man only ever writes a pipe's *source*
        cell and a display only reads its *destination* cell, and pipes are at least two cells long.
        """
        for number, screen in enumerate(self.screens):
            for port, index in screen.display.ports():
                slots = self.pipes[index]
                value = slots[-1]
                if value is None:
                    continue
                slots[-1] = None
                if not self._apply(screen, self.program.pipes[index].dest, port, value):
                    return False
                if self.trace is not None:
                    self.trace.device(self, number, port, value)
        return True

    def _apply(self, screen: Screen, cell: tuple[int, int], port: str, value: int) -> bool:
        """One value into one port. Every out-of-range value ends the whole program."""
        display = screen.display
        match port:
            case "ADDR":
                if not 0 <= value < display.pixels:
                    raise RunError(
                        "display",
                        f"ADDR {value} is outside a {display.width}x{display.height} display "
                        f"(0..{display.pixels - 1})",
                        cell,
                    )
                screen.cursor = value
            case "DATA":
                if not 0 <= value <= 15:
                    raise RunError(
                        "display", f"colour {value} is not one of the 16 colours (0..15)", cell
                    )
                screen.next[screen.cursor] = value
                # Next column, else next row, else back to the upper-left — which is what advancing
                # a `row * width + column` cursor modulo the pixel count does.
                screen.cursor = (screen.cursor + 1) % display.pixels
            case _:
                if value not in (0, 1):
                    raise RunError("display", f"SWAP {value} is neither 0 nor 1", cell)
                screen.current[:] = screen.next
                if value == 0:
                    screen.next = bytearray(display.pixels)
                    screen.cursor = 0
                return self._commit(screen.frame())
        return True

    def _commit(self, frame: Frame) -> bool:
        self.frame_count += 1
        self.frames.append(frame)
        del self.frames[:-_FRAME_HISTORY]
        return self.io.commit(frame, self.tick)

    def _move_all(self) -> None:
        room_of = self.program.room_of
        before = [(man.x, man.y) for man in self.men] if self.can_collide else []
        for man in self.men:
            if man.born:
                # Born already standing on his cell during this tick's execution phase; he executes
                # it next tick, so this movement phase is the one he does not get.
                man.born = False
                continue
            if man.stopped or man.blocked:
                continue
            dx, dy = DELTAS[man.dir]
            cell = (man.x + dx, man.y + dy)
            if cell not in room_of:
                # Armed here, thrown at the next tick's execution phase — phases 1 and 2 of that
                # tick still run, so the output pipe gets to deliver.
                man.fault = RunError(
                    "wall",
                    f"a little man walked into the wall at ({cell[0]},{cell[1]}) "
                    f"from ({man.x},{man.y})",
                    cell,
                )
                continue
            man.x, man.y = cell
        if self.can_collide and len(self.men) > 1:
            self._cull(self._overlaps() | self._swaps(before))

    def _swaps(self, before: list[Cell]) -> set[int]:
        """Indices of men who moved *through* each other. Both die, and it is not an error.

        > This includes two men arriving on the same cell in the same tick, and two adjacent men
        > moving through each other (swapping cells) in the same tick. — split#Y, precisely

        Arriving on one cell is ``_overlaps``; this is the other half, which needs each man's cell
        from *before* the phase as well as after. A man who did not move cannot swap: he still
        stands where he started, so nobody can have taken his old cell for his new one.
        """
        # Cells at the start of the phase are distinct — every collision is culled as it happens.
        origin = {cell: index for index, cell in enumerate(before)}
        doomed: set[int] = set()
        for index, man in enumerate(self.men):
            other = origin.get((man.x, man.y))
            if other is None or other == index:
                continue
            if (self.men[other].x, self.men[other].y) == before[index]:
                doomed.add(index)
                doomed.add(other)
        return doomed

    def _execute(self, man: Man, char: str) -> None:
        man.blocked = False
        if char in _LOAD_CHARS:
            # Absent from the table means this cell loads nothing walked this way: a digit inside a
            # literal, a backtick that does not delimit along this axis, or an empty literal.
            value = self.program.loads.get((man.x, man.y, man.dir))
            if value is not None:
                man.a = value
            return

        match char:
            case " " | "." | "@":
                return
            case "H":
                man.stopped = True
            case "M":
                man.b = man.a
            case "W":
                man.a, man.b = man.b, man.a
            case "+":
                man.a = wrap(man.a + man.b)
            case "-":
                man.a = wrap(man.a - man.b)
            case "*":
                man.a = wrap(man.a * man.b)
            case "N":
                man.a = wrap(-man.a)
            case "/":
                # Floored, remainder into B. B = 0 gives A = 0 with the dividend kept in B.
                if man.b == 0:
                    man.a, man.b = 0, man.a
                else:
                    quotient, man.b = divmod(man.a, man.b)
                    man.a = wrap(quotient)
            case "%":
                man.a = 0 if man.b == 0 else man.a % man.b
            case "&":
                man.a = wrap(man.a & man.b)
            case "|":
                man.a = wrap(man.a | man.b)
            case "~":
                man.a = wrap(man.a ^ man.b)
            case "{":
                man.a = wrap(man.a << man.b) if 0 <= man.b <= 63 else 0
            case "}":
                man.a = _shift_right(man.a, man.b)
            case ">":
                man.dir = EAST
            case "<":
                man.dir = WEST
            case "^":
                man.dir = NORTH
            case "v" | "V":
                man.dir = SOUTH
            case "X":
                if man.a > 0:
                    man.dir = (man.dir + 1) % 4
                elif man.a < 0:
                    man.dir = (man.dir - 1) % 4
            case "b":
                man.bp = man.a
            case "m":
                man.bp = wrap(man.bp - 1)
            case "]":
                man.bp = man.bp >> 1
            case "d":
                if man.bp > 0:
                    man.dir = (man.dir + 1) % 4
            case "a":
                if man.bp > 0:
                    man.dir = (man.dir - 1) % 4
            case "x":
                # Always turns, and reads the raw low bit: a negative backpack is not zero.
                man.dir = (man.dir + 1) % 4 if man.bp & 1 else (man.dir - 1) % 4
            case "q":
                slots = self.pipes[self._incoming(man, "q")]
                man.bp = sum(slot is not None for slot in slots)
            case "s":
                self._send(man)
            case "S":
                self._broadcast(man)
            case "r":
                self._receive(man)
            case "R" | "U":
                self._select(man, turn=char == "U")
            case _:
                raise RunError(
                    "bad-op",
                    f"{char!r} at ({man.x},{man.y}) is not an instruction",
                    (man.x, man.y),
                )

    def _incoming(self, man: Man, char: str) -> int:
        pipe = self.program.nearest_in.get((man.x, man.y))
        if pipe is None:
            raise RunError(
                "no-pipe",
                f"{char!r} at ({man.x},{man.y}) ran in a room with no incoming pipe",
                (man.x, man.y),
            )
        return pipe

    def _send(self, man: Man) -> None:
        pipe = self.program.nearest_out.get((man.x, man.y))
        if pipe is None:
            raise RunError(
                "no-pipe",
                f"'s' at ({man.x},{man.y}) ran in a room with no outgoing pipe",
                (man.x, man.y),
            )
        slots = self.pipes[pipe]
        if slots[0] is not None:
            man.blocked = True
            return
        slots[0] = man.a

    def _broadcast(self, man: Man) -> None:
        outgoing = self.program.rooms[man.room].outgoing
        if not outgoing:
            raise RunError(
                "no-pipe",
                f"'S' at ({man.x},{man.y}) ran in a room with no outgoing pipe",
                (man.x, man.y),
            )
        # All or nothing: it never writes to just some of them.
        if any(self.pipes[index][0] is not None for index in outgoing):
            man.blocked = True
            return
        for index in outgoing:
            self.pipes[index][0] = man.a

    def _receive(self, man: Man) -> None:
        slots = self.pipes[self._incoming(man, "r")]
        if slots[-1] is None:
            man.blocked = True
            return
        man.a, slots[-1] = slots[-1], None

    def _select(self, man: Man, *, turn: bool) -> None:
        """`R` takes from any ready incoming pipe, reading order breaking ties; `U` then turns."""
        incoming = self.program.incoming_sorted.get(man.room, [])
        if not incoming:
            char = "U" if turn else "R"
            raise RunError(
                "no-pipe",
                f"{char!r} at ({man.x},{man.y}) ran in a room with no incoming pipe",
                (man.x, man.y),
            )
        for index in incoming:
            slots = self.pipes[index]
            if slots[-1] is None:
                continue
            man.a, slots[-1] = slots[-1], None
            if turn:
                # Turn away from the pipe he read from: face the way that pipe flows into the room.
                man.dir = self.program.pipes[index].entry_dir
            return
        man.blocked = True


def _shift_right(a: int, b: int) -> int:
    """Arithmetic right shift: 0 when B < 0, sign-filled when B > 63."""
    if b < 0:
        return 0
    if b > 63:
        return -1 if a < 0 else 0
    return a >> b
