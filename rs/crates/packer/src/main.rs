//! `lmp` — compile a `.eman.toml` netlist + the global `rooms/` library into a packed `.man`.
//!
//! Place-and-route in the EDA sense: rooms are components, handoff markers are pins, pipes are
//! nets on a single layer. Cost is `max(w, h)` of the routed grid, nothing else; ticks are
//! reported so a human can veto a regression, never optimised.
//!
//! No HTTP: cases come from `icfp tests <slug> -o cases.json`, same philosophy as `lmr`.
//! The output is a CANDIDATE — the server has twice loaded a different pipe graph than a locally
//! green grid, so every packed program still goes through `icfp submit --wait`.

mod anneal;
mod app;
mod assemble;
mod check;
mod cli;
mod compact;
mod design;
mod error;
mod floorplan;
mod library;
mod planar;
mod report;
mod rng;
mod seed;
mod validate;

use clap::Parser;

pub(crate) use error::PackError;

fn main() {
    let args = cli::Args::parse();
    if let Err(error) = app::run(&args) {
        eprintln!("error: {error}");
        std::process::exit(1);
    }
}
