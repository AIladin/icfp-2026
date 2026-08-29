"""Four adaptive memory banks as two proven B=2 heads behind a streaming bit-1 router."""

from __future__ import annotations

import argparse
from pathlib import Path

from memory_gen3 import Canvas


ROUTER_W = 18
ROUTER_H = 9


def router_room() -> str:
    """Route raw operations by address bit 1; gate reads but pipeline independent writes."""
    c = Canvas()
    c.room(0, 0, ROUTER_W + 2, ROUTER_H + 2)

    def put(x: int, y: int, ch: str) -> None:
        c.put(x, y, ch)

    # Shared entry: B=op, BP=addr, then ]/x branches on address bit 1.
    put(1, 4, ">")
    put(2, 4, "@")
    for x, ch in enumerate("rMrb]x", start=3):
        put(x, 4, ch)

    # Pair 0 lane.  W/s/W/s sends op then addr while restoring A=op for X.  It shares
    # the first interior row with pair 1's harmless west return, saving one full room row.
    put(8, 3, "^")
    put(8, 2, "^")
    put(8, 1, ">")
    for x, ch in enumerate("WsWsWX", start=9):
        put(x, 1, ch)

    # Pair-0 READ receives its selected head's response and emits it.
    put(16, 1, "r")
    put(17, 1, "s")
    put(18, 1, "v")

    # Pair-0 WRITE turns west below the lane, reads/sends the raw value, then joins the east return.
    put(14, 2, "v")
    put(14, 3, "<")
    put(11, 3, "r")
    put(10, 3, "s")
    put(9, 3, "v")
    put(9, 4, ">")
    put(18, 4, "v")

    # Pair 1: route east of the split, descend, then traverse a westbound mirrored lane.
    put(8, 5, ">")
    put(12, 5, "v")
    put(12, 6, "v")
    put(12, 7, "<")
    for x, ch in zip(range(10, 4, -1), "WsWsWX", strict=True):
        put(x, 7, ch)

    # Pair-1 READ loops under the lane to its specific result receive and the shared output send.
    put(2, 7, "v")
    put(2, 8, ">")
    put(15, 8, "r")
    put(16, 8, "s")
    put(17, 8, "v")
    put(17, 9, "<")

    # Pair-1 WRITE turns north, reads/sends the raw value, then returns above the entry.
    put(5, 6, "<")
    put(4, 6, "r")
    put(3, 6, "s")
    put(2, 6, "^")
    put(2, 1, "<")

    # Top and bottom return buses re-enter at (1,4).
    put(1, 1, "v")
    put(1, 2, "v")
    put(1, 3, "v")
    for y in range(5, 10):
        put(1, y, "^")
    put(18, 9, "<")

    # Shift for north/west markers.  Port groups are placed by their audited instruction zones.
    c.cells = {(x + 1, y + 1): ch for (x, y), ch in c.cells.items()}
    c.put(9, 0, "A")    # raw input
    c.put(21, 2, "C")   # pair 0 result
    c.put(21, 9, "E")   # pair 1 result
    c.put(13, 0, "b")   # pair 0 request stream
    c.put(8, 12, "d")   # pair 1 request stream
    c.put(21, 5, "f")   # output
    return c.render()


def write_rooms(root: Path) -> None:
    path = root / "rooms/memory-pair-router"
    path.mkdir(parents=True, exist_ok=True)
    (path / "base.room").write_text(router_room())
    (path / "interface.toml").write_text(
        'description = "stream writes and gate reads across two B=2 memory heads"\n\n'
        '[ports]\nraw = "A"\nresult0 = "C"\nresult1 = "E"\n'
        'pair0 = "b"\npair1 = "d"\noutput = "f"\n'
    )


def write_design(root: Path) -> None:
    out = root / "programs/memory/banked4-pairs"
    out.mkdir(parents=True, exist_ok=True)
    lines = [
        '# Four adaptive banks: address bit 1 selects a B=2 head; each head splits on',
        '# (addr+1)&1. Every ring has 25 legal addresses. The 30-cell leg minima are',
        '# throughput-load-bearing; see [[A full adaptive memory ring needs throughput slack]].',
        'problem = "memory"', '', '[rooms]', 'input = "input"', 'output = "output"',
        'router = "memory-pair-router"', 'head0 = "memory-head-sbs"',
        'head1 = "memory-head-sbs"',
    ]
    for bank in range(4):
        lines.append(f'relay{bank} = "memory-relay"')

    def pipe(source: str, target: str, minimum: int | None = None) -> None:
        lines.extend(("", "[[pipes]]", f'from = "{source}"', f'to = "{target}"'))
        if minimum is not None:
            lines.append(f"min = {minimum}")

    pipe("input.out", "router.raw")
    pipe("router.pair0", "head0.input")
    pipe("router.pair1", "head1.input")
    pipe("head0.output", "router.result0")
    pipe("head1.output", "router.result1")
    pipe("router.output", "output.feed")
    for pair in range(2):
        for local in range(2):
            bank = 2 * pair + local
            pipe(f"head{pair}.ring_out{local}", f"relay{bank}.feed", 30)
            pipe(f"relay{bank}.out", f"head{pair}.ring_in{local}", 30)
    (out / "design.eman.toml").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--room", action="store_true")
    args = parser.parse_args()
    if args.room:
        print(router_room(), end="")
    if args.write:
        root = Path(__file__).resolve().parents[1]
        write_rooms(root)
        write_design(root)


if __name__ == "__main__":
    main()
