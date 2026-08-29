//! Local interpreter and judge for Littleman (`.man`) programs.
//!
//! A port of `py/libs/runner/src/littleman/`, module for module, and it must stay that way: the
//! Python runner is the **reference oracle**, with server-confirmed results behind it. When the two
//! disagree, Python is right until the contest server rules otherwise.
//!
//! ```no_run
//! use littleman::{DEFAULT_MAX_TICKS, load_program, parse_cases, run_case, score};
//!
//! let source = std::fs::read_to_string("prog.man")?;
//! let program = load_program(&source)?;                    // every structural rule
//! let cases = parse_cases(&std::fs::read_to_string("cases.json")?)?;
//!
//! let results: Vec<_> =
//!     cases.iter().map(|case| run_case(&program, case, DEFAULT_MAX_TICKS)).collect();
//! println!("{:?}", score(&program, &results, "footprint-tick"));
//! # Ok::<(), Box<dyn std::error::Error>>(())
//! ```
//!
//! A [`Program`] is topology only and holds no run state, so load once and run it against many
//! cases. All mutable state lives in [`Machine`].

pub mod case;
pub mod ephemeral;
pub mod errors;
pub mod grid;
pub mod judge;
pub mod load;
pub mod machine;
pub mod model;
pub mod trace;

pub use case::{Problem, Round, TestCase, parse_cases};
pub use ephemeral::{
    EphemeralError, Marker, NegotiatedCongestion, NegotiatedFailure, Router, Synthesis, synthesise,
    synthesise_markers, synthesise_markers_capped, synthesise_markers_negotiated,
    synthesise_markers_negotiated_attempt,
};
pub use errors::{LittlemanError, LoadError, RunError, RunErrorKind};
pub use grid::Grid;
pub use judge::{
    CaseIo, DEFAULT_MAX_TICKS, FreeIo, RunResult, Stage, run_case, run_case_traced, run_free,
    run_free_traced, score,
};
pub use load::load_program;
pub use machine::{Frame, Io, Machine, Man, NoTrace, Outcome, Screen, Tracer};
pub use model::{Display, EAST, NORTH, Op, Pipe, Port, Program, Room, RoomKind, SOUTH, WEST};
pub use trace::{Printer, failure_report, frame_diff, summary};
