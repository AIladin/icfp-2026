"""Generate re-pinned variants of a room, so `lmp` has something to choose between.

The packer can only re-face a pin by substituting a variant, so a room type with one variant is a
fixed constraint on every layout that uses it -- and a type whose pins all sit on one wall forces
every room wired to it onto that side, which is how a netlist ends up not seeding at all.

This moves pins and nothing else. The room's interior is never transformed:

- **Rotating a room is not safe**, however tempting the free tall/wide pair looks. A little man
  always starts heading **east** and rotating the grid does not rotate that, so a rotated room's
  `@` steps into whatever is east of it -- usually a wall, which ends the program. In a 2-column
  room like the shuttle there is not even anywhere to stand to repair it. Generate a differently
  shaped room from its generator instead.
- **Moving a pin is safe only when the bindings survive it.** Every candidate is checked with the
  loader's own nearest-pipe rule against the source's bindings: a placement that moves any `s` onto
  a different pipe, or ties two, is discarded. That check is what makes the enumeration below
  usable rather than a source of silent wrong-pipe bugs.

Two enumerations, picked by how much freedom the room actually has:

- At most one pipe per direction: nothing can mis-bind, so every pin goes everywhere -- the full
  cross product over walls and offsets.
- Otherwise: whole-set moves, sliding all the pins together to each wall and along it. For a room
  whose pins all share a wall this is exactly right, because then only the coordinate *along* that
  wall enters the distance, so the opposite wall is free and comes out identical.

    uv run python room_variants.py rooms/memory-relay          # write the variants
    uv run python room_variants.py rooms/ --all --dry-run      # see what it would write
"""

from __future__ import annotations

import argparse
import itertools
import tomllib
from dataclasses import dataclass
from pathlib import Path

WALLS = "NESW"


@dataclass
class Room:
    """A room as an interior grid plus pins, each on a wall at an offset along it."""

    interior: list[str]
    pins: dict[str, tuple[str, int]]

    @property
    def w(self) -> int:
        return len(self.interior[0])

    @property
    def h(self) -> int:
        return len(self.interior)

    def span(self, wall: str) -> int:
        return self.w if wall in "NS" else self.h

    def repin(self, placement: dict[str, tuple[str, int]]) -> Room:
        return Room(list(self.interior), dict(placement))

    def render(self) -> str:
        used = {w for w, _ in self.pins.values()}
        pad_l, pad_t = int("W" in used), int("N" in used)
        width = pad_l + self.w + 2 + int("E" in used)
        height = pad_t + self.h + 2 + int("S" in used)
        g = [[" "] * width for _ in range(height)]

        bx, by = pad_l, pad_t
        for i in range(self.w + 2):
            g[by][bx + i] = "+" if i in (0, self.w + 1) else "-"
            g[by + self.h + 1][bx + i] = "+" if i in (0, self.w + 1) else "-"
        for j in range(self.h):
            g[by + 1 + j][bx] = "|"
            g[by + 1 + j][bx + self.w + 1] = "|"
            for i, ch in enumerate(self.interior[j]):
                g[by + 1 + j][bx + 1 + i] = ch

        for letter, (wall, off) in self.pins.items():
            x, y = {
                "N": (bx + 1 + off, by - 1),
                "S": (bx + 1 + off, by + self.h + 2),
                "W": (bx - 1, by + 1 + off),
                "E": (bx + self.w + 2, by + 1 + off),
            }[wall]
            g[y][x] = letter
        return "\n".join("".join(r).rstrip() for r in g).rstrip("\n") + "\n"


def parse(path: Path) -> Room:
    lines = path.read_text().rstrip("\n").split("\n")
    grid = [x.ljust(max(len(v) for v in lines)) for x in lines]
    by = next(y for y, r in enumerate(grid) if r.lstrip().startswith("+") and "-" in r)
    bx = grid[by].index("+")
    ex = grid[by].index("+", bx + 1)
    bh = next(y for y in range(by + 1, len(grid)) if grid[y][bx] == "+")

    interior = [grid[y][bx + 1:ex] for y in range(by + 1, bh)]
    pins: dict[str, tuple[str, int]] = {}
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if not ch.isalpha() or (by <= y <= bh and bx <= x <= ex):
                continue
            if y == by - 1 and bx < x < ex:
                pins[ch] = ("N", x - bx - 1)
            elif y == bh + 1 and bx < x < ex:
                pins[ch] = ("S", x - bx - 1)
            elif x == bx - 1 and by < y < bh:
                pins[ch] = ("W", y - by - 1)
            elif x == ex + 1 and by < y < bh:
                pins[ch] = ("E", y - by - 1)
            else:
                raise ValueError(f"{path}: marker {ch!r} at ({x},{y}) is not beside a wall")
    return Room(interior, pins)


def pin_cell(room: Room, wall: str, off: int) -> tuple[int, int]:
    """A pin's cell in interior coordinates: past the wall, so two out from the interior.

    That cell *is* the pipe's segment attached to this room -- the thing the nearest-pipe rule
    measures to.
    """
    return {"N": (off, -2), "S": (off, room.h + 1),
            "W": (-2, off), "E": (room.w + 1, off)}[wall]


def bindings(room: Room) -> dict[tuple[int, int], str] | None:
    """What every nearest-pipe instruction binds to. None if any of them is an exact tie.

    `s` ranges over the outgoing pins, `r`/`q` over the incoming ones. `S`, `R` and `U` are not
    nearest-pipe operations, so they constrain nothing. A tie is refused outright: it is one repack
    away from a silently re-pointed send.
    """
    out_pins = [p for p in room.pins if p.islower()]
    in_pins = [p for p in room.pins if p.isupper()]
    bound: dict[tuple[int, int], str] = {}
    for y, row in enumerate(room.interior):
        for x, ch in enumerate(row):
            group = out_pins if ch == "s" else in_pins if ch in "rq" else None
            if not group:
                continue
            scored = sorted(
                (abs(x - cx) + abs(y - cy), cy, cx, p)
                for p in group
                for cx, cy in [pin_cell(room, *room.pins[p])]
            )
            if len(scored) > 1 and scored[0][0] == scored[1][0]:
                return None
            bound[(x, y)] = scored[0][3]
    return bound


def placements(room: Room) -> list[dict[str, tuple[str, int]]]:
    """Candidate pin placements to try, before any of them has been validated."""
    letters = sorted(room.pins)
    free = sum(p.islower() for p in letters) <= 1 and sum(p.isupper() for p in letters) <= 1

    if free:
        slots = [(w, o) for w in WALLS for o in range(room.span(w))]
        return [
            dict(zip(letters, combo, strict=True))
            for combo in itertools.product(slots, repeat=len(letters))
            if len(set(combo)) == len(combo)
        ]

    # Otherwise move the whole set together: onto each wall, and slid along it. Sliding changes the
    # distances, so most shifts will be rejected -- but the opposite wall never is, because with
    # every pin sharing a wall the perpendicular term is the same for all of them and cancels.
    base = [room.pins[p][1] for p in letters]
    out: list[dict[str, tuple[str, int]]] = []
    for wall in WALLS:
        for shift in range(-max(base), room.span(wall) - max(base)):
            offs = [b + shift for b in base]
            if min(offs) < 0 or max(offs) >= room.span(wall):
                continue
            out.append({p: (wall, o) for p, o in zip(letters, offs, strict=True)})

    # And peel one or two pins off onto another wall, leaving the rest where they are. This is the
    # one that matters for a room taller than it is wide: everything wired to it has to stack below
    # it while its pins all share the south wall, but a drum whose pair moves to the east wall can
    # sit *beside* the head instead, which is where the footprint is.
    for k in (1, 2):
        for group in itertools.combinations(letters, k):
            for wall in WALLS:
                for offs in itertools.permutations(range(room.span(wall)), k):
                    place = dict(room.pins)
                    place.update(zip(group, ((wall, o) for o in offs), strict=True))
                    if len(set(place.values())) == len(place):
                        out.append(place)
    return out


def variants(room: Room, limit: int) -> dict[str, Room]:
    """Every candidate placement that reproduces the source room's bindings exactly."""
    want = bindings(room)
    if want is None:
        raise ValueError("the source room already has a tied binding")
    out: dict[str, Room] = {}
    for place in placements(room):
        cand = room.repin(place)
        if bindings(cand) != want:
            continue
        name = "-".join(f"{p}{w.lower()}{o}" for p, (w, o) in sorted(place.items()))
        out[name] = cand
        if len(out) >= limit:
            break
    return out


def process(type_dir: Path, dry: bool, limit: int) -> str:
    ports = tomllib.loads((type_dir / "interface.toml").read_text()).get("ports", {})
    sources = sorted(type_dir.glob("*.room"))
    # Generated names carry offsets, so they contain digits -- and they sort before a hand-written
    # `south.room`. Enumerating from one of those would quietly re-base the whole search on a
    # variant instead of the room as designed.
    canonical = next((p for p in sources if not any(c.isdigit() for c in p.stem)), sources[0])
    got = variants(parse(canonical), limit)

    # Hand-written variants already in the library win; an identical generated one would only make
    # the packer search the same arrangement twice.
    existing = {p.read_text() for p in sources}
    written = 0
    for name, room in got.items():
        if room.render() in existing:
            continue
        if not dry:
            (type_dir / f"{name}.room").write_text(room.render())
        written += 1
    walls = sorted({w for r in got.values() for w, _ in r.pins.values()})
    return (f"{type_dir.name:20s} {len(ports)} ports: {len(got)} valid placements, "
            f"+{written} new, walls used {walls}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path, help="a rooms/<type> directory, or rooms/ with --all")
    ap.add_argument("--all", action="store_true", help="process every type under path")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=400, help="cap on variants written per type")
    args = ap.parse_args()

    targets = (
        sorted(p for p in args.path.iterdir() if (p / "interface.toml").exists())
        if args.all else [args.path]
    )
    for t in targets:
        print(process(t, args.dry_run, args.limit))


if __name__ == "__main__":
    main()
