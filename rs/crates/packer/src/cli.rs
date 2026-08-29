use std::path::PathBuf;

use clap::Parser;
use littleman::DEFAULT_MAX_TICKS;

#[derive(Parser)]
#[command(name = "lmp", about = "Pack a .eman.toml netlist into a .man program", version)]
pub struct Args {
    /// The .eman.toml design to pack.
    pub design: PathBuf,
    /// Cases JSON from `icfp tests <slug> -o cases.json`; without it candidates are NOT judged.
    #[arg(short, long)]
    pub cases: Option<PathBuf>,
    /// Where to write the best program (default: the design path with .eman.toml -> .man).
    #[arg(short, long)]
    pub out: Option<PathBuf>,
    /// The rooms library (default: the nearest `rooms/` directory above the design).
    #[arg(long)]
    pub rooms: Option<PathBuf>,
    /// Planar layout hint from `uv run python eman_hint.py <design>` (default: hint.json next to
    /// the design, if present).
    #[arg(long)]
    pub hint: Option<PathBuf>,
    /// Seed, route and judge the design, then stop — no search. This checks the concrete layout,
    /// including binding and pipe lengths, but may be expensive for a large design.
    #[arg(long)]
    pub check: bool,
    /// Run a fast room-logic check, then stop — no seed search and no .man output. Composes each
    /// room's first allowed variant and installs runtime pipes at their declared minimum lengths.
    /// Unlike --check, this does not prove those lengths can be routed in a packed layout.
    #[arg(long, conflicts_with = "check")]
    pub logic_check: bool,
    /// Sample the first case during --logic-check every N ticks, printing pipe occupancy and man
    /// state. This diagnoses a step cap without producing a trace line on every tick.
    #[arg(long, value_name = "N", requires = "logic_check")]
    pub logic_trace: Option<u64>,
    /// Annealing budget in seconds, for the B*-tree floorplan stage.
    #[arg(long, default_value_t = 60.0)]
    pub seconds: f64,
    /// Budget for the coordinate polish stage that follows it (default: 20% of --seconds, 0 skips).
    /// The tree compacts globally but has no single-room move; this is where that relief happens.
    #[arg(long)]
    pub polish: Option<f64>,
    /// Bounded greedy room-band compaction after search, in seconds. Zero disables it. It runs
    /// only with cases and keeps the pre-compaction winner as an alternative.
    #[arg(long, default_value_t = 2.0)]
    pub compact_seconds: f64,
    /// RNG seed. Fixes the seeding sweep exactly; the *search* still varies run to run, because
    /// its budget is wall-clock and a busy machine gets fewer iterations.
    #[arg(long, default_value_t = littleman::ephemeral::SEED)]
    pub seed: u64,
    /// Tick cap per case while judging.
    #[arg(long, default_value_t = DEFAULT_MAX_TICKS)]
    pub ticks: u64,
    /// How many distinct-footprint candidates to keep and write.
    #[arg(long, default_value_t = 3)]
    pub keep: usize,
    /// Parallel annealing chains (default: cores - 2, leaving room to keep working).
    #[arg(long)]
    pub jobs: Option<usize>,
    /// Emit the summary as JSON.
    #[arg(long)]
    pub json: bool,
}
