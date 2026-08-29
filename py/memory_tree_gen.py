"""Generate protocol rooms for the direct binary-tree `memory` experiment."""

from __future__ import annotations

import argparse
from pathlib import Path

from memory_gen3 import Canvas


def decoder_room() -> str:
    """One-bit request router with a selected reverse response path.

    Ports are intentionally spread across five walls/rows.  The generated netlist binding checker
    is the authority; comments name every r/s below so an accidental nearest-pipe change is loud.
    """
    c = Canvas()
    c.room(0, 0, 14, 10)

    # Return bus and common request decode: r=parent request.
    for y in range(2, 9):
        c.put(1, y, "^")
    c.text(1, 1, ">@rM2W/WX")

    # Remainder 0, upper/east branch: child request s, child response r.
    c.text(10, 1, "Ws")
    for y in range(1, 4):
        c.put(12, y, "v")
    c.put(12, 4, "<")
    c.put(11, 4, "r")
    c.put(10, 4, "v")
    for y in range(5, 8):
        c.put(10, y, "v")

    # Remainder 1, lower/west branch: child request s, child response r.
    for y in range(2, 5):
        c.put(9, y, "v")
    c.put(9, 5, "<")
    c.put(6, 5, "W")
    c.put(5, 5, "s")
    c.put(2, 5, "v")
    c.put(2, 6, "v")
    c.put(2, 7, ">")
    c.put(3, 7, "r")

    # Both branches merge at (10,7), send the response to the parent, and loop.
    c.put(10, 7, "v")
    c.put(10, 8, "<")
    c.put(9, 8, "s")

    # Shift the box right/down so west and north markers can sit outside its walls.
    c.cells = {(x + 1, y + 1): ch for (x, y), ch in c.cells.items()}

    # Port markers: uppercase incoming, lowercase outgoing.
    c.put(4, 0, "A")        # parent request -> first r
    c.put(15, 2, "b")       # upper child request
    c.put(15, 5, "C")       # upper child response
    c.put(0, 6, "d")        # lower child request
    c.put(0, 8, "E")        # lower child response
    c.put(10, 11, "f")      # parent response
    return c.render()


type PinPlacement = dict[str, tuple[str, int]]

COMPACT_BASE_PINS: PinPlacement = {
    "A": ("N", 2),
    "b": ("E", 0),
    "f": ("S", 2),
    "d": ("S", 5),
    "C": ("S", 9),
    "E": ("S", 11),
}

COMPACT_VARIANTS: dict[str, PinPlacement] = {
    # Parent request/response above; both child request/response pairs below.
    "layered-down": {
        "A": ("N", 2), "f": ("N", 1),
        "d": ("S", 8), "E": ("S", 9),
        "b": ("S", 10), "C": ("S", 11),
    },
    # The reverse layered orientation.
    "layered-up": {
        "A": ("S", 2), "f": ("S", 1),
        "d": ("N", 5), "E": ("N", 7),
        "b": ("N", 10), "C": ("N", 11),
    },
    # A compact recursive corner: parent west, child 0 east, child 1 south.
    "fork-east-south": {
        "A": ("W", 0), "f": ("W", 4),
        "b": ("E", 0), "C": ("E", 1),
        "d": ("S", 5), "E": ("S", 6),
    },
    # Keep the fast parent-request pin north while putting its response beside it to the west.
    "fork-northwest": {
        "A": ("N", 2), "f": ("W", 4),
        "b": ("E", 0), "C": ("E", 1),
        "d": ("S", 5), "E": ("S", 6),
    },
}


def _pin_cell(wall: str, offset: int) -> tuple[int, int]:
    return {
        "N": (offset, -2),
        "S": (offset, 6),
        "W": (-2, offset),
        "E": (13, offset),
    }[wall]


def audit_compact_pins(pins: PinPlacement) -> list[str]:
    """Audit all nearest `r`/`s` bindings for this room-specific geometry."""
    uses = [
        ("r", (2, 0), "A"),
        ("s0", (10, 0), "b"),
        ("s1", (5, 2), "d"),
        ("s-parent", (2, 4), "f"),
    ]
    rows: list[str] = []
    for label, (x, y), expected in uses:
        candidates = "ACE" if label == "r" else "bdf"
        ranked = sorted(
            (abs(x - px) + abs(y - py), pin, wall, offset)
            for pin in candidates
            for wall, offset in [pins[pin]]
            for px, py in [_pin_cell(wall, offset)]
        )
        distance, got, wall, offset = ranked[0]
        margin = ranked[1][0] - distance
        if got != expected or margin <= 0:
            raise ValueError(
                f"{label} binds {got} at {wall}{offset}, expected {expected}; margin {margin}"
            )
        rows.append(
            f"{label:8s} ({x:2d},{y:2d}) -> {got} at {wall}{offset}; margin {margin}"
        )
    return rows


def compact_decoder_room(pins: PinPlacement | None = None) -> str:
    """One-bit router whose response side relies on strict single-flight gating.

    After exactly one child request is sent, ``R`` accepts the only child response that can exist.
    The parent request pipe must not contain a second ready value while this room waits at ``R``;
    a gate or a stream-safe decoder immediately above the compact subtree enforces that invariant.
    """
    pins = COMPACT_BASE_PINS if pins is None else pins
    audit_compact_pins(pins)
    walls = {wall for wall, _ in pins.values()}
    ox = int("W" in walls)
    oy = int("N" in walls)
    c = Canvas()
    c.room(ox, oy, 14, 7)  # 98 rectangle cells, versus 140 for decoder_room().

    def put(x: int, y: int, ch: str) -> None:
        c.put(ox + x, oy + y, ch)

    # Parent request decode.  After / and W: A = low address bit, B = packet // 2.
    for i, ch in enumerate(">@rM2W/WXWs"):
        put(1 + i, 1, ch)
    put(12, 1, "v")

    # Remainder 0: the top-row W/s sends the quotient to child 0, then descends.
    put(12, 2, "v")
    put(12, 3, "v")
    put(12, 4, "<")

    # Remainder 1: X turns south, then W/s sends the quotient to child 1.
    put(9, 2, "v")
    put(9, 3, "<")
    put(7, 3, "W")
    put(6, 3, "s")
    put(5, 3, "v")

    # Both request arms merge before one broad receive.  Only the selected child can answer.
    put(5, 4, "v")
    put(5, 5, "<")
    put(4, 5, "R")
    put(3, 5, "s")
    put(1, 5, "^")
    for y in range(2, 5):
        put(1, y, "^")

    for letter, (wall, offset) in pins.items():
        x, y = {
            "N": (ox + 1 + offset, oy - 1),
            "S": (ox + 1 + offset, oy + 7),
            "W": (ox - 1, oy + 1 + offset),
            "E": (ox + 14, oy + 1 + offset),
        }[wall]
        c.put(x, y, letter)
    return c.render()


def memory_cell_room() -> str:
    """Persistent leaf: zero reads B, any nonzero odd code writes B, then acknowledges."""
    c = Canvas()
    c.room(0, 0, 9, 8)  # 72 rectangle cells.
    c.text(1, 1, ">@r v")
    c.put(5, 2, "X")

    # Positive and negative writes both store their odd value code, return zero, and merge below.
    c.put(4, 2, "M")
    c.put(3, 2, "v")
    c.put(6, 2, "M")
    c.put(7, 2, "v")
    for x in (3, 7):
        c.put(x, 3, "0")
        c.put(x, 4, "s")
        c.put(x, 5, "v")

    # A zero request is READ: expose B, send it, then restore it.
    c.put(5, 3, "W")
    c.put(5, 4, "s")
    c.put(5, 5, "W")

    # All paths join the bottom return bus.
    c.put(1, 6, "^")
    for y in range(2, 6):
        c.put(1, y, "^")
    for x in range(3, 8):
        c.put(x, 6, "<")

    c.cells = {(x + 1, y + 1): ch for (x, y), ch in c.cells.items()}
    c.put(4, 0, "A")
    c.put(6, 9, "b")
    return c.render()


def packetizer_room(bits: int = 7) -> str:
    """Convert PREP's FIFO op/value/address stream into one tree packet.

    READ is ``0, addr`` -> ``addr``.  WRITE is ``1, value, addr`` ->
    ``(2*value+1)*2**bits + addr``.  The low address bits route the address; the final signed odd
    quotient is a write code, while zero is a read code.
    """
    if bits not in range(1, 10):
        raise ValueError(f"packetizer supports a single-digit positive bit count, got {bits}")
    c = Canvas()
    c.room(0, 0, 21, 8)

    # The read arm loops over the top: r op, X, r addr, s packet.
    c.put(1, 1, "v")
    c.put(7, 1, "<")
    c.text(1, 2, ">@rXrs^")

    # A positive op turns south.  Compute (2*v+1)<<7, park it in B, receive addr, add, send.
    c.put(4, 3, ">")
    c.text(5, 3, f"rM+M1+M{bits}W{{Mr+s")
    c.put(19, 3, "v")
    c.put(19, 4, "v")
    c.put(19, 5, "v")
    c.put(19, 6, "<")

    # Write return rises into the same loop entry.
    c.put(1, 6, "^")
    c.put(1, 5, "^")
    c.put(1, 4, "^")
    c.put(1, 3, "^")

    c.cells = {(x + 1, y + 1): ch for (x, y), ch in c.cells.items()}
    c.put(4, 0, "A")
    c.put(17, 9, "b")
    return c.render()


def prep_room() -> str:
    """Gate raw memory operations, feed PACK, await completion, and decode reads."""
    c = Canvas()
    c.room(0, 0, 16, 8)

    # r/b remembers op in BP; r/M parks addr in B; d sends READ straight or WRITE south.
    c.text(1, 1, ">@rbrMd0sWs")
    c.put(14, 1, "v")

    # WRITE emits FIFO op=1, raw value, then the parked address.
    c.put(7, 2, "v")
    c.put(7, 3, ">")
    c.text(8, 3, "1srsWs")
    c.put(14, 3, "v")

    # Both paths wait for one tree response with B=2.  READ divides odd code by two and emits it;
    # WRITE's BP-positive d arm discards the acknowledgement.
    c.put(14, 2, "v")
    c.put(14, 4, "v")
    c.put(14, 5, "v")
    c.put(14, 6, "<")
    c.put(7, 6, "2")
    c.put(6, 6, "M")
    c.put(5, 6, "r")
    c.put(4, 6, "d")
    c.put(3, 6, "/")
    c.put(2, 6, "s")
    c.put(4, 5, "<")

    # Shared return bus.
    for y in range(2, 7):
        c.put(1, y, "^")

    c.cells = {(x + 1, y + 1): ch for (x, y), ch in c.cells.items()}
    c.put(5, 0, "A")   # raw input; nearest to all three raw r cells
    c.put(0, 7, "C")   # tree result; nearest to the wait r
    c.put(17, 4, "b")  # FIFO stream to PACK
    c.put(0, 6, "d")   # decoded READ output
    return c.render()


def echo_room() -> str:
    c = Canvas()
    c.room(0, 0, 7, 5)
    c.text(1, 1, ">@rv")
    c.put(4, 2, "s")
    c.put(4, 3, "<")
    c.put(1, 2, "^")
    c.put(1, 3, "^")
    c.put(3, 5, "A")
    c.put(5, 5, "b")
    return c.render()


def write_rooms(root: Path) -> None:
    rooms = root / "rooms"
    specs = {
        "memory-tree-decoder": (
            decoder_room(),
            'description = "one-bit request/response memory-tree router"\n\n'
            '[ports]\nparent_req = "A"\nchild_req0 = "b"\nchild_resp0 = "C"\n'
            'child_req1 = "d"\nchild_resp1 = "E"\nparent_resp = "f"\n',
        ),
        "memory-tree-decoder-r": (
            compact_decoder_room(),
            'description = "single-flight one-bit request/response memory-tree router"\n\n'
            '[ports]\nparent_req = "A"\nchild_req0 = "b"\nchild_resp0 = "C"\n'
            'child_req1 = "d"\nchild_resp1 = "E"\nparent_resp = "f"\n',
        ),
        "memory-tree-cell": (
            memory_cell_room(),
            'description = "persistent signed-code memory-tree leaf"\n\n'
            '[ports]\nrequest = "A"\nresponse = "b"\n',
        ),
        "memory-tree-packetizer": (
            packetizer_room(),
            'description = "pack op/value/address FIFO into one direct-tree packet"\n\n'
            '[ports]\nstream = "A"\nrequest = "b"\n',
        ),
        "memory-tree-packetizer2": (
            packetizer_room(2),
            'description = "two-address-bit direct-tree packetizer probe"\n\n'
            '[ports]\nstream = "A"\nrequest = "b"\n',
        ),
        "memory-tree-prep": (
            prep_room(),
            'description = "single-flight raw memory operation gate"\n\n'
            '[ports]\nraw = "A"\nresult = "C"\nstream = "b"\noutput = "d"\n',
        ),
        "memory-tree-echo": (
            echo_room(),
            'description = "echo leaf for memory-tree router protocol tests"\n\n'
            '[ports]\nrequest = "A"\nresponse = "b"\n',
        ),
    }
    for name, (room, interface) in specs.items():
        path = rooms / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "base.room").write_text(room)
        (path / "interface.toml").write_text(interface)
    compact_path = rooms / "memory-tree-decoder-r"
    for name, pins in COMPACT_VARIANTS.items():
        (compact_path / f"{name}.room").write_text(compact_decoder_room(pins))


def write_tree_probe(root: Path) -> None:
    """Write the complete seven-level 128-leaf routing probe (no memory semantics yet)."""
    out = root / "programs/memory/tree128-probe"
    out.mkdir(parents=True, exist_ok=True)
    lines = ['problem = "memory"', "", "[rooms]", 'input = "input"', 'output = "output"']
    for depth in range(7):
        for prefix in range(1 << depth):
            lines.append(f'd{depth}_{prefix} = "memory-tree-decoder"')
    for leaf in range(128):
        lines.append(f'leaf{leaf} = "memory-tree-echo"')

    def pipe(source: str, target: str) -> None:
        lines.extend(("", "[[pipes]]", f'from = "{source}"', f'to = "{target}"'))

    pipe("input.out", "d0_0.parent_req")
    pipe("d0_0.parent_resp", "output.feed")
    for depth in range(7):
        for prefix in range(1 << depth):
            parent = f"d{depth}_{prefix}"
            for bit in range(2):
                child_prefix = prefix | (bit << depth)
                if depth == 6:
                    request = f"leaf{child_prefix}.request"
                    response = f"leaf{child_prefix}.response"
                else:
                    child = f"d{depth + 1}_{child_prefix}"
                    request = f"{child}.parent_req"
                    response = f"{child}.parent_resp"
                pipe(f"{parent}.child_req{bit}", request)
                pipe(response, f"{parent}.child_resp{bit}")
    (out / "design.eman.toml").write_text("\n".join(lines) + "\n")

    # No semantic oracle: the protocol's declared identity is floor(token / 128).
    samples = [(0, 0), (99, 2_000_001), (127, 1)] + [(i, i + 1) for i in range(100)]
    tokens = [str(q * 128 + address) for address, q in samples]
    expected = [str(q) for _, q in samples]
    import json

    cases = [{"name": "all legal addresses", "rounds": [{"in": tokens, "out": expected}]}]
    (out / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")


def write_compact_probes(root: Path) -> None:
    """Write gated depth-1/depth-2 probes and a full 128-leaf echo tree."""

    def pipe(lines: list[str], source: str, target: str) -> None:
        lines.extend(("", "[[pipes]]", f'from = "{source}"', f'to = "{target}"'))

    # Depth one: an explicit gate proves that buffered raw input cannot be consumed by R.
    one = root / "programs/memory/tree-r-probe"
    one.mkdir(parents=True, exist_ok=True)
    lines = [
        'problem = "memory"', "", "[rooms]", 'input = "input"', 'output = "output"',
        'gate = "memory-select-gate"', 'dec = "memory-tree-decoder-r"',
        'leaf0 = "memory-tree-echo"', 'leaf1 = "memory-tree-echo"',
    ]
    pipe(lines, "input.out", "gate.raw")
    pipe(lines, "gate.request", "dec.parent_req")
    pipe(lines, "dec.child_req0", "leaf0.request")
    pipe(lines, "leaf0.response", "dec.child_resp0")
    pipe(lines, "dec.child_req1", "leaf1.request")
    pipe(lines, "leaf1.response", "dec.child_resp1")
    pipe(lines, "dec.parent_resp", "gate.result")
    pipe(lines, "gate.output", "output.feed")
    (one / "design.eman.toml").write_text("\n".join(lines) + "\n")

    import json

    one_inputs = [0, 2, 4, 6, 1, 3, 5, 7, 0, 3, 2, 5, 4, 7, 6, 1]
    one_cases = [{
        "name": "gated repeated and alternating branches",
        "rounds": [{
            "in": [str(value) for value in one_inputs],
            "out": [str(value // 2) for value in one_inputs],
        }],
    }]
    (one / "cases.json").write_text(json.dumps(one_cases, indent=2) + "\n")

    # Depth two: the old stream-safe root gates two compact child routers.
    two = root / "programs/memory/tree-r-depth2-probe"
    two.mkdir(parents=True, exist_ok=True)
    lines = [
        'problem = "memory"', "", "[rooms]", 'input = "input"', 'output = "output"',
        'root = "memory-tree-decoder"', 'd0 = "memory-tree-decoder-r"',
        'd1 = "memory-tree-decoder-r"',
    ]
    for leaf in range(4):
        lines.append(f'leaf{leaf} = "memory-tree-echo"')
    pipe(lines, "input.out", "root.parent_req")
    pipe(lines, "root.child_req0", "d0.parent_req")
    pipe(lines, "d0.parent_resp", "root.child_resp0")
    pipe(lines, "root.child_req1", "d1.parent_req")
    pipe(lines, "d1.parent_resp", "root.child_resp1")
    for low_bit, decoder in enumerate(("d0", "d1")):
        for high_bit in range(2):
            leaf = low_bit | (high_bit << 1)
            pipe(lines, f"{decoder}.child_req{high_bit}", f"leaf{leaf}.request")
            pipe(lines, f"leaf{leaf}.response", f"{decoder}.child_resp{high_bit}")
    pipe(lines, "root.parent_resp", "output.feed")
    (two / "design.eman.toml").write_text("\n".join(lines) + "\n")
    two_inputs = [0, 4, 8, 1, 5, 9, 2, 6, 10, 3, 7, 11, 0, 3, 1, 2] * 2
    two_cases = [{
        "name": "nested repeated and cross branches",
        "rounds": [{
            "in": [str(value) for value in two_inputs],
            "out": [str(value // 4) for value in two_inputs],
        }],
    }]
    (two / "cases.json").write_text(json.dumps(two_cases, indent=2) + "\n")

    # Full tree: retain one stream-safe old root; all 126 descendants use the compact router.
    full = root / "programs/memory/tree128-r-probe"
    full.mkdir(parents=True, exist_ok=True)
    lines = ['problem = "memory"', "", "[rooms]", 'input = "input"', 'output = "output"']
    for depth in range(7):
        room_type = "memory-tree-decoder" if depth == 0 else "memory-tree-decoder-r"
        for prefix in range(1 << depth):
            lines.append(f'd{depth}_{prefix} = "{room_type}"')
    for leaf in range(128):
        lines.append(f'leaf{leaf} = "memory-tree-echo"')
    pipe(lines, "input.out", "d0_0.parent_req")
    pipe(lines, "d0_0.parent_resp", "output.feed")
    for depth in range(7):
        for prefix in range(1 << depth):
            parent = f"d{depth}_{prefix}"
            for bit in range(2):
                child_prefix = prefix | (bit << depth)
                if depth == 6:
                    request = f"leaf{child_prefix}.request"
                    response = f"leaf{child_prefix}.response"
                else:
                    child = f"d{depth + 1}_{child_prefix}"
                    request = f"{child}.parent_req"
                    response = f"{child}.parent_resp"
                pipe(lines, f"{parent}.child_req{bit}", request)
                pipe(lines, response, f"{parent}.child_resp{bit}")
    (full / "design.eman.toml").write_text("\n".join(lines) + "\n")
    samples = [(0, 0), (99, 2_000_001), (127, 1)] + [(i, i + 1) for i in range(100)]
    full_cases = [{
        "name": "all legal addresses",
        "rounds": [{
            "in": [str(q * 128 + address) for address, q in samples],
            "out": [str(q) for _, q in samples],
        }],
    }]
    (full / "cases.json").write_text(json.dumps(full_cases, indent=2) + "\n")


def write_semantic_probes(root: Path) -> None:
    """Write independent PACK and persistent-leaf protocol probes."""
    import json

    packet = root / "programs/memory/tree-packetizer-probe"
    packet.mkdir(parents=True, exist_ok=True)
    (packet / "design.eman.toml").write_text('''problem = "memory"

[rooms]
input = "input"
output = "output"
pack = "memory-tree-packetizer"

[[pipes]]
from = "input.out"
to = "pack.stream"
[[pipes]]
from = "pack.request"
to = "output.feed"
''')
    packet_cases = [{
        "name": "reads writes signs and boundaries",
        "rounds": [{
            "in": ["0", "0", "0", "99", "1", "0", "5", "1", "42", "7",
                   "1", "-5", "8", "1", "-1000000", "99", "1", "1000000", "0"],
            "out": ["0", "99", "133", "10887", "-1144", "-255999773", "256000128"],
        }],
    }]
    (packet / "cases.json").write_text(json.dumps(packet_cases, indent=2) + "\n")

    cell = root / "programs/memory/tree-cell-probe"
    cell.mkdir(parents=True, exist_ok=True)
    (cell / "design.eman.toml").write_text('''problem = "memory"

[rooms]
input = "input"
output = "output"
cell = "memory-tree-cell"

[[pipes]]
from = "input.out"
to = "cell.request"
[[pipes]]
from = "cell.response"
to = "output.feed"
''')
    cell_cases = [{
        "name": "fresh overwrite signed and boundary codes",
        "rounds": [{
            "in": ["0", "85", "0", "-9", "0", "1", "0", "-1999999", "0",
                   "2000001", "0"],
            "out": ["0", "0", "85", "0", "-9", "0", "1", "0", "-1999999", "0",
                    "2000001"],
        }],
    }]
    (cell / "cases.json").write_text(json.dumps(cell_cases, indent=2) + "\n")

    real = root / "programs/memory/tree-real-depth2-probe"
    real.mkdir(parents=True, exist_ok=True)
    lines = [
        'problem = "memory"', "", "[rooms]", 'input = "input"', 'output = "output"',
        'prep = "memory-tree-prep"', 'pack = "memory-tree-packetizer2"',
        'root = "memory-tree-decoder"', 'd0 = "memory-tree-decoder-r"',
        'd1 = "memory-tree-decoder-r"',
    ]
    for leaf in range(4):
        lines.append(f'leaf{leaf} = "memory-tree-cell"')

    def pipe(source: str, target: str) -> None:
        lines.extend(("", "[[pipes]]", f'from = "{source}"', f'to = "{target}"'))

    pipe("input.out", "prep.raw")
    pipe("prep.stream", "pack.stream")
    pipe("pack.request", "root.parent_req")
    pipe("root.child_req0", "d0.parent_req")
    pipe("d0.parent_resp", "root.child_resp0")
    pipe("root.child_req1", "d1.parent_req")
    pipe("d1.parent_resp", "root.child_resp1")
    for low_bit, decoder in enumerate(("d0", "d1")):
        for high_bit in range(2):
            leaf = low_bit | (high_bit << 1)
            pipe(f"{decoder}.child_req{high_bit}", f"leaf{leaf}.request")
            pipe(f"leaf{leaf}.response", f"{decoder}.child_resp{high_bit}")
    pipe("root.parent_resp", "prep.result")
    pipe("prep.output", "output.feed")
    (real / "design.eman.toml").write_text("\n".join(lines) + "\n")
    real_cases = [{
        "name": "four persistent cells signed and ordered",
        "rounds": [{
            "in": ["0", "0", "0", "3", "1", "0", "42", "0", "0", "1", "3", "-5",
                   "0", "3", "1", "1", "-1000000", "1", "2", "1000000", "0", "1",
                   "0", "2", "1", "0", "0", "0", "0", "0", "3"],
            "out": ["0", "0", "42", "-5", "-1000000", "1000000", "0", "-5"],
        }],
    }]
    (real / "cases.json").write_text(json.dumps(real_cases, indent=2) + "\n")


def write_real_tree(root: Path) -> None:
    """Write the complete 100-cell direct tree for its optimistic logic/area price gate."""
    out = root / "programs/memory/tree128-real"
    out.mkdir(parents=True, exist_ok=True)
    lines = [
        'problem = "memory"', "", "[rooms]", 'input = "input"', 'output = "output"',
        'prep = "memory-tree-prep"', 'pack = "memory-tree-packetizer"',
    ]
    for depth in range(7):
        room_type = "memory-tree-decoder" if depth == 0 else "memory-tree-decoder-r"
        for prefix in range(1 << depth):
            lines.append(f'd{depth}_{prefix} = "{room_type}"')
    for leaf in range(128):
        room_type = "memory-tree-cell" if leaf < 100 else "memory-tree-echo"
        lines.append(f'leaf{leaf} = "{room_type}"')

    def pipe(source: str, target: str) -> None:
        lines.extend(("", "[[pipes]]", f'from = "{source}"', f'to = "{target}"'))

    pipe("input.out", "prep.raw")
    pipe("prep.stream", "pack.stream")
    pipe("pack.request", "d0_0.parent_req")
    pipe("d0_0.parent_resp", "prep.result")
    pipe("prep.output", "output.feed")
    for depth in range(7):
        for prefix in range(1 << depth):
            parent = f"d{depth}_{prefix}"
            for bit in range(2):
                child_prefix = prefix | (bit << depth)
                if depth == 6:
                    request = f"leaf{child_prefix}.request"
                    response = f"leaf{child_prefix}.response"
                else:
                    child = f"d{depth + 1}_{child_prefix}"
                    request = f"{child}.parent_req"
                    response = f"{child}.parent_resp"
                pipe(f"{parent}.child_req{bit}", request)
                pipe(response, f"{parent}.child_resp{bit}")
    (out / "design.eman.toml").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-rooms", action="store_true")
    parser.add_argument("--write-tree-probe", action="store_true")
    parser.add_argument("--write-compact-probes", action="store_true")
    parser.add_argument("--write-semantic-probes", action="store_true")
    parser.add_argument("--write-real-tree", action="store_true")
    parser.add_argument("--decoder", action="store_true")
    parser.add_argument("--compact-decoder", action="store_true")
    parser.add_argument("--audit-compact", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.write_rooms:
        write_rooms(root)
    if args.write_tree_probe:
        write_tree_probe(root)
    if args.write_compact_probes:
        write_compact_probes(root)
    if args.write_semantic_probes:
        write_semantic_probes(root)
    if args.write_real_tree:
        write_real_tree(root)
    if args.decoder:
        print(decoder_room(), end="")
    if args.compact_decoder:
        print(compact_decoder_room(), end="")
    if args.audit_compact:
        for name, pins in {"base": COMPACT_BASE_PINS, **COMPACT_VARIANTS}.items():
            print(f"{name}:")
            print("\n".join(f"  {row}" for row in audit_compact_pins(pins)))


if __name__ == "__main__":
    main()
