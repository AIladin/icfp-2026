"""Planar layout hint for `lmp`.

Reads a `.eman.toml` netlist, checks the room graph is planar, and computes a certified
crossing-free straight-line grid drawing of it (NetworkX: `check_planarity` -> combinatorial
embedding -> Chrobak-Payne `combinatorial_embedding_to_pos`). The integer positions land in a
JSON hint that `lmp --hint` fattens into an actual room placement.

This exists because no Rust crate ships the layout half of planarity (rustworkx-core has only the
boolean test), and porting Chrobak-Payne mid-contest lost to a JSON side-file. Same precedent as
`lmr --problem` shelling out to the `icfp` CLI.

    uv run python eman_hint.py ../programs/sudoku-validity/sudoku.eman.toml
    uv run python eman_hint.py design.eman.toml -o hint.json
"""

import argparse
import json
import sys
import tomllib
from pathlib import Path

import networkx as nx


def load_netlist(path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    data = tomllib.loads(path.read_text())
    rooms = list(data.get("rooms", {}))
    if not rooms:
        sys.exit(f"{path}: no [rooms]")
    edges = []
    for pipe in data.get("pipes", []):
        source = pipe["from"].split(".")[0]
        target = pipe["to"].split(".")[0]
        for name in (source, target):
            if name not in rooms:
                sys.exit(f"{path}: pipe endpoint {name!r} is not a room instance")
        edges.append((source, target))
    return rooms, edges


def component_positions(graph: nx.Graph) -> dict[str, tuple[int, int]]:
    if len(graph) == 1:
        return {next(iter(graph)): (0, 0)}
    if len(graph) == 2:
        left, right = sorted(graph)
        return {left: (0, 0), right: (2, 0)}
    planar, embedding = nx.check_planarity(graph)
    if not planar:
        sys.exit(
            "the room graph is NOT PLANAR — pipes share the single layer with the rooms and can "
            "never cross, so no placement can route this netlist. Split a busy room into two "
            "rooms that divide its pipes (vertex splitting), or drop a pipe."
        )
    pos = nx.combinatorial_embedding_to_pos(embedding)
    return {node: (int(x), int(y)) for node, (x, y) in pos.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("design", type=Path, help="the .eman.toml netlist")
    ap.add_argument("-o", "--out", type=Path, help="hint path (default: <design dir>/hint.json)")
    args = ap.parse_args()

    rooms, edges = load_netlist(args.design)
    graph = nx.Graph()
    graph.add_nodes_from(rooms)
    graph.add_edges_from((a, b) for a, b in edges if a != b)

    positions: dict[str, tuple[int, int]] = {}
    offset = 0
    for component in nx.connected_components(graph):
        placed = component_positions(graph.subgraph(component).copy())
        span = max(x for x, _ in placed.values()) if placed else 0
        for node, (x, y) in placed.items():
            positions[node] = (x + offset, y)
        offset += span + 3

    out = args.out or args.design.parent / "hint.json"
    out.write_text(json.dumps({"pos": {n: list(p) for n, p in sorted(positions.items())}}, indent=2))
    width = max(x for x, _ in positions.values()) + 1
    height = max(y for _, y in positions.values()) + 1
    print(f"planar: yes  {len(rooms)} rooms on a {width}x{height} abstract grid -> {out}")


if __name__ == "__main__":
    main()
