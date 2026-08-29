//! The planarity gate. Pipes live on a single layer and can never cross — two pipes cannot share
//! a grid cell — so a netlist whose room graph is non-planar is unroutable *by theorem*, not by
//! router weakness. Refusing it up front with that explanation beats hours of failed seeds.

use rustworkx_core::petgraph::graph::UnGraph;
use rustworkx_core::planar::is_planar;

use crate::PackError;
use crate::design::Design;

pub fn require_planar(design: &Design) -> Result<(), PackError> {
    let mut graph: UnGraph<(), ()> = UnGraph::new_undirected();
    let nodes: Vec<_> = (0..design.instances.len()).map(|_| graph.add_node(())).collect();
    let mut seen = std::collections::BTreeSet::new();
    for pipe in &design.pipes {
        let (a, b) = (pipe.from.0, pipe.to.0);
        // Parallel pipes and 2-cycles do not affect planarity; the test wants a simple graph.
        if a != b && seen.insert((a.min(b), a.max(b))) {
            graph.add_edge(nodes[a], nodes[b], ());
        }
    }
    if is_planar(&graph) {
        return Ok(());
    }
    Err(PackError(
        "the netlist's room graph is NOT PLANAR. Pipes are drawn on the same single layer as the \
         rooms and two pipes can never cross a cell, so no placement of these rooms can route \
         this design — this is a theorem, not a router limitation. Split a busy room into two \
         rooms that divide its pipes between them (vertex splitting can restore planarity; merely \
         relaying a pipe through an extra room cannot), or drop a pipe."
            .into(),
    ))
}
