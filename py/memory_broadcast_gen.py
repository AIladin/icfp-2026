"""Generate the broadcast/reduce tree experiment for `memory`.

The first target is deliberately one level: a broadcaster, a reducer and two one-bit named
persistent leaves.  It proves that every leaf can answer every packet, so both sides of the tree
re-enter their loops rather than leaving the unselected side blocked forever.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from memory_gen3 import Canvas

BIAS = 1_000_001


def broadcast_room() -> str:
    c = Canvas()
    c.room(0, 0, 7, 6)
    c.text(1, 1, "@>rsv")
    c.put(5, 2, "v")
    c.put(5, 3, "v")
    c.put(5, 4, "<")
    c.put(4, 4, "s")
    c.put(2, 4, "^")
    c.put(2, 3, "^")
    c.put(2, 2, "^")
    c.cells = {(x + 1, y + 1): ch for (x, y), ch in c.cells.items()}
    c.put(0, 3, "A")  # parent request, sole incoming pipe
    c.put(5, 0, "b")  # child 0 request, nearest to top s
    c.put(5, 7, "c")  # child 1 request, nearest to bottom s
    return c.render()


def reduce_room() -> str:
    c = Canvas()
    c.room(0, 0, 8, 6)
    # Spawn joins the cycle at (3,2).  The return turns east before crossing @, so @ is a nop.
    c.put(2, 2, "@")
    c.put(3, 2, "^")
    c.text(3, 1, ">rMv")
    c.put(6, 2, "v")
    c.put(6, 3, "v")
    c.put(6, 4, "<")
    c.text(3, 4, "s+r")  # walked west: r, +, s
    c.put(2, 4, "<")
    c.put(1, 4, "^")
    c.put(1, 3, "^")
    c.put(1, 2, ">")
    c.cells = {(x + 1, y + 1): ch for (x, y), ch in c.cells.items()}
    c.put(5, 0, "A")  # child 0 response, nearest to top r
    c.put(6, 7, "B")  # child 1 response, nearest to bottom r
    c.put(4, 7, "c")  # aggregate response, sole outgoing pipe
    return c.render()


def leaf_room(address: int) -> str:
    if address not in (0, 1):
        raise ValueError("the one-level probe only has addresses 0 and 1")
    c = Canvas()
    c.room(0, 0, 23, 10)
    # B starts as biased zero.  Initialisation descends at the far right, away from live branches.
    c.text(1, 1, f"@>`{BIAS}`M")
    c.put(21, 1, "v")
    c.put(21, 2, "v")
    c.put(21, 3, "v")
    c.put(21, 4, "<")

    if address == 0:
        # addr+1 == 1: with x entered west, bit 1 turns north to the match X.
        c.text(10, 4, "xbr")  # walked west: r, b, x
        c.put(10, 3, "X")
        c.text(11, 3, "M7W}M0s")  # positive/write: store packet >> 7, return zero
        c.put(18, 3, "v")
        c.text(7, 3, "WsW")  # walked west: W, s, W; preserve biased B
        c.put(6, 3, "v")
        c.put(10, 5, "0")  # wrong bit
        c.put(10, 6, "s")
        c.put(10, 7, "v")
        c.put(6, 8, ">")
        c.put(10, 8, ">")
        c.put(18, 8, "<")
    else:
        # addr+1 == 2: bit 0 turns south to the match X.
        c.text(10, 5, "xbr")  # walked west
        c.put(13, 5, "<")
        c.put(13, 4, "v")
        c.put(10, 6, "X")
        c.text(3, 6, "s0M}W7M")  # walked west: M,7,W,},M,0,s
        c.put(2, 6, "v")
        c.text(11, 6, "WsW")  # negative/read, walked east
        c.put(18, 6, "v")
        c.put(18, 7, "v")
        c.put(18, 8, "<")
        c.put(10, 4, "0")  # wrong bit
        c.put(10, 3, "s")
        c.put(10, 2, "<")
        c.put(2, 2, "v")
        c.put(2, 8, ">")

    # Shared return bus re-enters at the request receive without revisiting initialisation.
    c.put(14, 8, "^")
    for y in range(5, 8):
        c.put(14, y, "^")
    c.put(14, 4, "<")
    c.cells = {(x + 1, y + 1): ch for (x, y), ch in c.cells.items()}
    c.put(13, 0, "A")  # request, sole incoming
    c.put(13, 11, "b")  # response, sole outgoing
    return c.render()


def two_token_leaf_room(address: int) -> str:
    """One-bit leaf for the two-token request protocol.

    Every request is signed addr+1 followed by a payload.  Reads carry a dummy zero payload;
    writes carry the raw value.  This keeps persistent B naturally zero-initialised.
    """
    if address not in (0, 1):
        raise ValueError("the protocol probe only has addresses 0 and 1")
    c = Canvas()
    c.room(0, 0, 15, 8)

    # Shared return enters r,b,x heading east.  The low bit selects match versus mismatch.
    c.text(2, 3, "@>r b x")
    c.put(8, 3, "x")

    match_dir = 1 if address == 0 else 3
    mismatch_dir = 3 if address == 0 else 1
    dy = {1: 1, 3: -1}
    match_y = 3 + dy[match_dir]
    mismatch_y = 3 + dy[mismatch_dir]

    # Mismatch: consume the payload, force zero, send, then join the right return riser.
    c.put(8, mismatch_y, "r")
    mismatch_outer_y = mismatch_y + dy[mismatch_dir]
    c.put(8, mismatch_outer_y, ">")
    c.put(9, mismatch_outer_y, "0")
    c.put(10, mismatch_outer_y, "s")
    c.put(11, mismatch_outer_y, ">")
    c.put(13, mismatch_outer_y, "v")

    # Match: packet sign selects write (positive) from read (negative).
    c.put(8, match_y, "X")
    if match_dir == 1:
        # Enter sign X southbound: write turns west, read turns east.
        c.text(4, match_y, "s0Mr")  # walked west: r M 0 s
        c.text(9, match_y, "rWsW")
    else:
        # Enter sign X northbound: write turns east, read turns west.
        c.text(4, match_y, "WsWr")  # walked west: r W s W
        c.text(9, match_y, "rM0s")

    # Both selected branches and the mismatch path merge on row 6, then re-enter the receive.
    c.put(3, match_y, "v")
    c.put(13, match_y, "v")
    for y in range(2, 6):
        if (13, y) not in c.cells:
            c.put(13, y, "v")
    c.put(1, 6, "^")
    c.put(2, 6, "<")
    for x in range(3, 14):
        c.put(x, 6, "<")
    c.put(1, 5, "^")
    c.put(1, 4, "^")
    c.put(1, 3, ">")

    c.cells = {(x + 1, y + 1): ch for (x, y), ch in c.cells.items()}
    c.put(4, 0, "A")
    c.put(9, 9, "b")
    return c.render()


def select_zero_room() -> str:
    """Divide by two, send the quotient to one child and zero to the other."""
    c = Canvas()
    c.room(0, 0, 14, 10)
    c.text(1, 1, ">@rM2W/v")
    c.put(8, 2, "W")
    c.put(8, 3, "X")

    # Remainder zero: child 0 gets q, then child 1 gets zero.
    c.put(8, 4, "W")
    c.put(8, 5, "s")
    c.put(8, 6, "0")
    c.put(8, 7, "v")
    c.put(8, 8, "<")
    c.put(2, 8, "s")
    c.put(1, 8, "^")

    # Remainder one: child 1 gets q, then child 0 gets zero.
    c.put(7, 3, "W")
    c.put(6, 3, "<")
    c.put(3, 3, "v")
    c.put(3, 5, "s")
    c.put(3, 6, "0")
    c.put(3, 7, ">")
    c.put(10, 7, "s")
    c.put(11, 7, "^")
    c.put(11, 6, "<")
    c.put(1, 6, "^")
    c.put(1, 7, "^")

    # Both paths return to the request receive on the top row.
    for y in range(2, 6):
        c.put(1, y, "^")

    c.cells = {(x + 1, y + 1): ch for (x, y), ch in c.cells.items()}
    c.put(4, 0, "A")
    c.put(15, 5, "b")
    c.put(3, 11, "c")
    return c.render()


def select_leaf_room() -> str:
    """Persistent unnamed leaf: -1 read, zero inactive, positive code write."""
    c = Canvas()
    c.room(0, 0, 12, 8)
    c.text(1, 1, ">@r  v")
    c.put(6, 2, "v")
    c.put(6, 3, "X")
    # Entering X southbound: positive writes west, negative reads east, inactive goes straight.
    c.text(3, 3, "s0M")  # walked west: M 0 s
    c.text(7, 3, "WsW")
    c.put(2, 3, "v")
    c.put(10, 3, "v")
    c.put(6, 4, "0")
    c.put(6, 5, "s")
    c.put(6, 6, "<")
    # Return paths merge along the bottom and re-enter r.
    c.put(2, 6, "<")
    c.put(2, 5, "v")
    c.put(2, 4, "v")
    for y in range(1, 7):
        c.put(1, y, ">" if y == 1 else "^")
    c.put(10, 4, "v")
    c.put(10, 5, "v")
    c.put(10, 6, "<")
    for x in range(3, 10):
        if (x, 6) not in c.cells:
            c.put(x, 6, "<")
    c.cells = {(x + 1, y + 1): ch for (x, y), ch in c.cells.items()}
    c.put(4, 0, "A")
    c.put(7, 9, "b")
    return c.render()


def select_gate_room() -> str:
    """Allow one selector-tree request in flight and forward its raw response."""
    c = Canvas()
    c.room(0, 0, 10, 8)
    c.text(1, 1, ">@r   s")
    c.put(8, 1, "v")
    for y in range(2, 5):
        c.put(8, y, "v")
    c.put(8, 5, "<")
    c.put(7, 5, "r")
    c.put(2, 5, "s")
    c.put(1, 5, "^")
    for y in range(2, 5):
        c.put(1, y, "^")
    c.cells = {(x + 1, y + 1): ch for (x, y), ch in c.cells.items()}
    c.put(4, 0, "A")
    c.put(11, 3, "b")
    c.put(8, 9, "C")
    c.put(0, 6, "d")
    return c.render()


def write_select_zero_probe(root: Path) -> None:
    specs = {
        "memory-select-zero": (select_zero_room(), 'description = "select quotient and zero-broadcast"\n\n[ports]\nrequest = "A"\nchild0 = "b"\nchild1 = "c"\n'),
        "memory-select-leaf": (select_leaf_room(), 'description = "unnamed persistent select leaf"\n\n[ports]\nrequest = "A"\nresponse = "b"\n'),
        "memory-select-gate": (select_gate_room(), 'description = "single-in-flight selector gate"\n\n[ports]\nraw = "A"\nrequest = "b"\nresult = "C"\noutput = "d"\n'),
    }
    for name, (room, interface) in specs.items():
        path = root / "rooms" / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "base.room").write_text(room)
        (path / "interface.toml").write_text(interface)

    out = root / "programs/memory/select-zero-probe"
    out.mkdir(parents=True, exist_ok=True)
    design = '''problem = "memory"

[rooms]
input = "input"
output = "output"
gate = "memory-select-gate"
select = "memory-select-zero"
reduce = "memory-reduce"
leaf0 = "memory-select-leaf"
leaf1 = "memory-select-leaf"

[[pipes]]
from = "input.out"
to = "gate.raw"
[[pipes]]
from = "gate.request"
to = "select.request"
[[pipes]]
from = "select.child0"
to = "leaf0.request"
[[pipes]]
from = "select.child1"
to = "leaf1.request"
[[pipes]]
from = "leaf0.response"
to = "reduce.child0"
[[pipes]]
from = "leaf1.response"
to = "reduce.child1"
[[pipes]]
from = "reduce.response"
to = "gate.result"
[[pipes]]
from = "gate.output"
to = "output.feed"
'''
    (out / "design.eman.toml").write_text(design)
    # At one remaining address bit: read=-2+bit, write=code*2+bit.
    cases = [{"name": "both branches persistence", "rounds": [{
        "in": ["-2", "-1", "2000086", "-2", "-1", "3", "-1", "-2", "4000002", "-2", "-1"],
        "out": ["0", "0", "0", "1000043", "0", "0", "1", "1000043", "0", "2000001", "1"],
    }]}]
    (out / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")


def write_two_token_probe(root: Path) -> None:
    for address in range(2):
        name = f"memory-two-token-leaf{address}"
        path = root / "rooms" / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "base.room").write_text(two_token_leaf_room(address))
        (path / "interface.toml").write_text(
            'description = "one-bit two-token broadcast memory leaf"\n\n'
            '[ports]\nrequest = "A"\nresponse = "b"\n'
        )

    out = root / "programs/memory/two-token-leaf-probe"
    out.mkdir(parents=True, exist_ok=True)
    design = '''problem = "memory"

[rooms]
input = "input"
output = "output"
leaf = "memory-two-token-leaf0"

[[pipes]]
from = "input.out"
to = "leaf.request"
[[pipes]]
from = "leaf.response"
to = "output.feed"
'''
    (out / "design.eman.toml").write_text(design)

    # Probe packets target leaf 0 (code ±1) or miss it (code ±2); every packet has a payload.
    cases = [{
        "name": "fresh writes misses and extremes",
        "rounds": [{
            "in": ["-1", "0", "1", "42", "-1", "0", "2", "-5", "-2", "0",
                   "1", "-1000000", "-1", "0", "1", "1000000", "-1", "0"],
            "out": ["0", "0", "42", "0", "0", "0", "-1000000", "0", "1000000"],
        }],
    }]
    (out / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")


def write_probe(root: Path) -> None:
    specs = {
        "memory-broadcast": (
            broadcast_room(),
            'description = "broadcast one request to two children"\n\n'
            '[ports]\nrequest = "A"\nchild0 = "b"\nchild1 = "c"\n',
        ),
        "memory-reduce": (
            reduce_room(),
            'description = "add two child responses"\n\n'
            '[ports]\nchild0 = "A"\nchild1 = "B"\nresponse = "c"\n',
        ),
    }
    for address in range(2):
        specs[f"memory-named-leaf{address}"] = (
            leaf_room(address),
            'description = "one-bit named persistent memory leaf"\n\n'
            '[ports]\nrequest = "A"\nresponse = "b"\n',
        )
    for name, (room, interface) in specs.items():
        path = root / "rooms" / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "base.room").write_text(room)
        (path / "interface.toml").write_text(interface)

    out = root / "programs/memory/broadcast-probe"
    out.mkdir(parents=True, exist_ok=True)
    design = '''problem = "memory"

[rooms]
input = "input"
output = "output"
bcast = "memory-broadcast"
reduce = "memory-reduce"
leaf0 = "memory-named-leaf0"
leaf1 = "memory-named-leaf1"

[[pipes]]
from = "input.out"
to = "bcast.request"
[[pipes]]
from = "bcast.child0"
to = "leaf0.request"
[[pipes]]
from = "bcast.child1"
to = "leaf1.request"
[[pipes]]
from = "leaf0.response"
to = "reduce.child0"
[[pipes]]
from = "leaf1.response"
to = "reduce.child1"
[[pipes]]
from = "reduce.response"
to = "output.feed"
'''
    (out / "design.eman.toml").write_text(design)

    def read(address: int) -> int:
        return -128 + address + 1

    def write(address: int, value: int) -> int:
        return (value + BIAS) * 128 + address + 1

    cases = [
        {"name": "fresh alternating", "rounds": [{"in": [str(read(0)), str(read(1)), str(read(0))], "out": [str(BIAS)] * 3}]},
        {"name": "writes and negative", "rounds": [{"in": [str(write(0, 42)), str(read(0)), str(write(1, -5)), str(read(1)), str(read(0))], "out": ["0", str(BIAS + 42), "0", str(BIAS - 5), str(BIAS + 42)]}]},
        {"name": "extremes overwrite", "rounds": [{"in": [str(write(1, -1_000_000)), str(write(1, 1_000_000)), str(read(1)), str(read(0))], "out": ["0", "0", str(BIAS + 1_000_000), str(BIAS)]}]},
    ]
    (out / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-probe", action="store_true")
    parser.add_argument("--leaf", type=int, choices=(0, 1))
    parser.add_argument("--two-token-leaf", type=int, choices=(0, 1))
    parser.add_argument("--write-two-token-probe", action="store_true")
    parser.add_argument("--write-select-zero-probe", action="store_true")
    args = parser.parse_args()
    if args.leaf is not None:
        print(leaf_room(args.leaf), end="")
    if args.two_token_leaf is not None:
        print(two_token_leaf_room(args.two_token_leaf), end="")
    if args.write_probe:
        write_probe(Path(__file__).resolve().parents[1])
    if args.write_two_token_probe:
        write_two_token_probe(Path(__file__).resolve().parents[1])
    if args.write_select_zero_probe:
        write_select_zero_probe(Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
