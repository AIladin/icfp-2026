//! Failure modes, split the way the contest splits them.
//!
//! A [`LoadError`] is structural and is caught before any tick runs — the server reports these as
//! `loadError` with no test case run at all. A [`RunError`] happens mid-run and ends the whole
//! program; its `kind` is one of the three names the language reference uses, or `display`.

use thiserror::Error;

use crate::model::Cell;

/// The program is structurally invalid: it would never start.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
#[error("{0}")]
pub struct LoadError(pub String);

/// Which of the machine's fatal mistakes happened. The first three are the reference's own names.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RunErrorKind {
    /// A step onto a cell that is not room interior.
    Wall,
    /// A character that is not an instruction.
    BadOp,
    /// A pipe instruction in a room with no pipe of that direction.
    NoPipe,
    /// The LM-75's own validation: a bad ADDR, colour or SWAP value.
    Display,
    /// A split took the number of live little men past [`crate::machine::MAX_MEN`].
    Population,
}

impl RunErrorKind {
    /// The name the judge reports, and the string the Python runner puts in `RunResult.error`.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Wall => "wall",
            Self::BadOp => "bad-op",
            Self::NoPipe => "no-pipe",
            Self::Display => "display",
            Self::Population => "population",
        }
    }
}

impl std::fmt::Display for RunErrorKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// A fatal mistake mid-run. Ends the whole program.
///
/// [`RunErrorKind::Display`] is the LM-75's own validation. The reference does not name it
/// alongside the other three, but it ends the run the same way.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
#[error("{kind}: {detail}")]
pub struct RunError {
    pub kind: RunErrorKind,
    pub detail: String,
    pub cell: Option<Cell>,
}

impl RunError {
    pub fn new(kind: RunErrorKind, detail: String, cell: Cell) -> Self {
        Self { kind, detail, cell: Some(cell) }
    }
}

/// Anything this crate raises, for callers that want one type.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum LittlemanError {
    #[error(transparent)]
    Load(#[from] LoadError),
    #[error(transparent)]
    Run(#[from] RunError),
}
