"""little-little-man — a plain-Python reference interpreter.

Written before any littleman cells, so the machine can be diffed against it.  The parsing
rules here are *exactly* the ones the machine will implement, not a convenient shortcut:

- a **vertical wall** is a maximal run of `|` with `+` directly above and directly below.
  `|` is not an LLM instruction, so outside a pipe it can only be a room wall, and a pipe's
  vertical body always has an arrowhead at each end -- never a `+`.
- rooms come from those walls **two at a time in reading order**: a room contributes its left
  and right wall at the same row, and rooms are disjoint, so consecutive discoveries pair up.
- a **pipe cell** is any cell outside every room holding one of `-|<>^v`.
- a **pipe start** is an arrowhead whose backward cell is on a room border; the chain is then
  followed forward until the cell in front is on a room border.
"""

from __future__ import annotations

import json
import sys

SIDE = 16

ARROWS = {">": (1, 0), "<": (-1, 0), "^": (0, -1), "v": (0, 1)}
DIR_E, DIR_S, DIR_W, DIR_N = 0, 1, 2, 3
DELTA = {DIR_E: (1, 0), DIR_S: (0, 1), DIR_W: (-1, 0), DIR_N: (0, -1)}
DIR_OF_ARROW = {">": DIR_E, "v": DIR_S, "<": DIR_W, "^": DIR_N}

COLOR_OP = {
    "<": 3, ">": 3, "^": 3, "v": 3, "X": 3, "H": 3,
    "M": 12, "+": 10, "-": 10, "s": 13, "r": 13,
    " ": 0, "@": 0,
}


class Room:
    def __init__(self, x0: int, y0: int, x1: int, y1: int):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1

    def on_border(self, x: int, y: int) -> bool:
        if not (self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1):
            return False
        return x in (self.x0, self.x1) or y in (self.y0, self.y1)

    def inside(self, x: int, y: int) -> bool:
        return self.x0 < x < self.x1 and self.y0 < y < self.y1

    def __repr__(self) -> str:
        return f"Room({self.x0},{self.y0}-{self.x1},{self.y1})"


class Pipe:
    def __init__(self, cells: list[tuple[int, int]], src_room: int, dst_room: int):
        self.cells = cells  # flow order: cells[0] is the source arrowhead
        self.src_room = src_room
        self.dst_room = dst_room
        self.vals: list[int | None] = [None] * len(cells)


class Man:
    def __init__(self, x: int, y: int, room: int):
        self.x, self.y, self.room = x, y, room
        self.d = DIR_E
        self.a = 0
        self.b = 0
        self.halted = False  # standing on an `H`


class Program:
    def __init__(self, w: int, h: int, chars: list[str]):
        self.g = [[" "] * SIDE for _ in range(SIDE)]
        for y in range(h):
            for x in range(w):
                self.g[y][x] = chars[y * w + x]
        self.rooms = self._find_rooms()
        self.wall = [[False] * SIDE for _ in range(SIDE)]
        for r in self.rooms:
            for y in range(r.y0, r.y1 + 1):
                for x in range(r.x0, r.x1 + 1):
                    if r.on_border(x, y):
                        self.wall[y][x] = True
        self.inroom = [[-1] * SIDE for _ in range(SIDE)]
        for i, r in enumerate(self.rooms):
            for y in range(r.y0 + 1, r.y1):
                for x in range(r.x0 + 1, r.x1):
                    self.inroom[y][x] = i
        self.pipecell = [[False] * SIDE for _ in range(SIDE)]
        for y in range(SIDE):
            for x in range(SIDE):
                if self.wall[y][x] or self.inroom[y][x] >= 0:
                    continue
                if self.g[y][x] in "-|<>^v":
                    self.pipecell[y][x] = True
        self.pipes = self._find_pipes()
        self.men = self._find_men()
        self.stopped = False

    # ---------------------------------------------------------------- parsing
    def at(self, x: int, y: int) -> str:
        if 0 <= x < SIDE and 0 <= y < SIDE:
            return self.g[y][x]
        return "\0"

    def _find_rooms(self) -> list[Room]:
        walls: list[tuple[int, int, int]] = []  # (x, y0, y1) in reading order of the top `+`
        for y in range(SIDE):
            for x in range(SIDE):
                if self.g[y][x] != "+" or self.at(x, y + 1) != "|":
                    continue
                yy = y + 1
                while self.at(x, yy) == "|":
                    yy += 1
                if self.at(x, yy) == "+":
                    walls.append((x, y, yy))
        rooms = []
        for i in range(0, len(walls) - 1, 2):
            (xa, y0, y1), (xb, y0b, y1b) = walls[i], walls[i + 1]
            if (y0, y1) != (y0b, y1b):
                raise ValueError(f"unpaired vertical walls {walls[i]} {walls[i + 1]}")
            rooms.append(Room(xa, y0, xb, y1))
        return rooms

    def _room_border_at(self, x: int, y: int) -> int:
        for i, r in enumerate(self.rooms):
            if r.on_border(x, y):
                return i
        return -1

    def _find_pipes(self) -> list[Pipe]:
        seen = [[False] * SIDE for _ in range(SIDE)]
        pipes = []
        for y in range(SIDE):
            for x in range(SIDE):
                if not self.pipecell[y][x] or seen[y][x]:
                    continue
                ch = self.g[y][x]
                if ch not in ARROWS:
                    continue
                dx, dy = ARROWS[ch]
                src = self._room_border_at(x - dx, y - dy)
                if src < 0:
                    continue
                cells, cx, cy, cd = [], x, y, (dx, dy)
                while True:
                    cells.append((cx, cy))
                    seen[cy][cx] = True
                    nx, ny = cx + cd[0], cy + cd[1]
                    dst = self._room_border_at(nx, ny)
                    if dst >= 0:
                        break
                    if not self.pipecell[ny][nx]:
                        raise ValueError(f"pipe from {x},{y} runs off at {nx},{ny}")
                    cx, cy = nx, ny
                    if self.g[cy][cx] in ARROWS:
                        cd = ARROWS[self.g[cy][cx]]
                pipes.append(Pipe(cells, src, dst))
        return pipes

    def _find_men(self) -> list[Man]:
        men = []
        for y in range(SIDE):
            for x in range(SIDE):
                if self.g[y][x] == "@" and self.inroom[y][x] >= 0:
                    men.append(Man(x, y, self.inroom[y][x]))
        return men

    # ---------------------------------------------------------------- nearest pipe
    def _nearest(self, man: Man, outgoing: bool) -> Pipe | None:
        best, bestd = None, None
        for p in self.pipes:
            if outgoing:
                if p.src_room != man.room:
                    continue
                hx, hy = p.cells[0]
            else:
                if p.dst_room != man.room:
                    continue
                hx, hy = p.cells[-1]
            d = abs(hx - man.x) + abs(hy - man.y)
            if bestd is None or d < bestd:
                best, bestd = p, d
        return best

    # ---------------------------------------------------------------- one tick
    def step(self) -> None:
        if self.stopped or all(m.halted for m in self.men):
            return
        for p in self.pipes:
            n = len(p.vals)
            for i in range(n - 2, -1, -1):
                if p.vals[i] is not None and p.vals[i + 1] is None:
                    p.vals[i + 1] = p.vals[i]
                    p.vals[i] = None
        taken = {}
        for m in self.men:
            if m.halted:
                continue
            ch = self.g[m.y][m.x]
            move = True
            if ch == "H":
                m.halted = True
                continue
            elif ch.isdigit():
                m.a = int(ch)
            elif ch == "M":
                m.b = m.a
            elif ch == "+":
                m.a += m.b
            elif ch == "-":
                m.a -= m.b
            elif ch in ARROWS:
                m.d = DIR_OF_ARROW[ch]
            elif ch == "X":
                if m.a > 0:
                    m.d = (m.d + 1) & 3
                elif m.a < 0:
                    m.d = (m.d + 3) & 3
            elif ch == "s":
                p = self._nearest(m, True)
                if p is None or p.vals[0] is not None:
                    move = False
                else:
                    taken[id(p)] = ("s", m.a, p)
            elif ch == "r":
                p = self._nearest(m, False)
                if p is None or p.vals[-1] is None:
                    move = False
                else:
                    m.a = p.vals[-1]
                    taken[(id(p), "r")] = ("r", 0, p)
            if move:
                dx, dy = DELTA[m.d]
                m.x += dx
                m.y += dy
        for key, (kind, val, p) in taken.items():
            if kind == "s":
                p.vals[0] = val
            else:
                p.vals[-1] = None
        for m in self.men:
            if self.wall[m.y][m.x]:
                self.stopped = True

    # ---------------------------------------------------------------- rendering
    def base_color(self, x: int, y: int) -> int:
        if self.wall[y][x]:
            return 4
        if self.pipecell[y][x]:
            return 6
        ch = self.g[y][x]
        if ch.isdigit():
            return 8
        return COLOR_OP.get(ch, 0)

    def frame(self) -> list[str]:
        px = [[self.base_color(x, y) for x in range(SIDE)] for y in range(SIDE)]
        for p in self.pipes:
            for (x, y), v in zip(p.cells, p.vals):
                if v is not None:
                    px[y][x] = 14
        for m in self.men:
            px[m.y][m.x] = 9
        return ["".join("%x" % c for c in row) for row in px]


def run_case(case: dict) -> tuple[int, int]:
    rounds = case["rounds"]
    first = [int(v) for v in rounds[0]["in"]]
    w, h = first[0], first[1]
    prog = Program(w, h, [chr(c) for c in first[2:]])
    ok = bad = 0
    for i, rnd in enumerate(rounds):
        if i:
            for _ in range(int(rnd["in"][0])):
                prog.step()
        got = prog.frame()
        want = [r.lower() for r in rnd["frames"][0]]
        if got == want:
            ok += 1
        else:
            bad += 1
            if bad == 1:
                print(f"  round {i} mismatch:")
                for a, b in zip(got, want):
                    print(f"    {a}  {b}  {'' if a == b else '<<'}")
    return ok, bad


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "../cases-llm.json"
    cases = json.load(open(path))
    total_ok = total_bad = 0
    for c in cases:
        ok, bad = run_case(c)
        total_ok += ok
        total_bad += bad
        print(f"{'ok ' if not bad else 'BAD'} {c['name']:20s} {ok}/{ok + bad}")
    print(f"{total_ok}/{total_ok + total_bad} frames")
    return 0 if not total_bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
