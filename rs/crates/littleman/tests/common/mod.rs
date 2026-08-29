//! Shared scaffolding: build tiny programs and run them without a judge.
//!
//! A port of `py/libs/runner/tests/helpers.py`.

#![allow(dead_code)]

use littleman::{Frame, Io, Machine, Man, Program, load_program};

/// No input, output ignored — for programs whose result is a little man's registers.
pub struct NullIo;

impl Io for NullIo {
    fn take(&mut self) -> Option<i64> {
        None
    }
    fn emit(&mut self, _value: i64, _tick: u64) -> bool {
        true
    }
    fn commit(&mut self, _frame: &Frame, _tick: u64) -> bool {
        true
    }
}

/// A fixed input sequence, released as fast as the input pipe will take it.
pub struct ListIo(pub Vec<i64>);

impl Io for ListIo {
    fn take(&mut self) -> Option<i64> {
        if self.0.is_empty() { None } else { Some(self.0.remove(0)) }
    }
    fn emit(&mut self, _value: i64, _tick: u64) -> bool {
        true
    }
    fn commit(&mut self, _frame: &Frame, _tick: u64) -> bool {
        true
    }
}

/// A 3x1 LM-75 wired on all three sides: a room above feeds ADDR, one to the left feeds DATA, and
/// one below feeds SWAP. The right side takes no pipe. The men are irrelevant — this is a topology.
/// Trailing padding is left out on purpose: `Grid::parse` pads every row to the widest one, so the
/// rows that end early are identical to the Python fixture's space-padded versions. The first row
/// sits on the opening-quote line because a `\` continuation would eat its leading spaces.
pub const THREE_PORT_DISPLAY: &str = "      +-+
      |@|
      +-+
       v
       v
+--+  +===+
|@ |>>:   :
+--+  +===+
       ^
       ^
      +-+
      |@|
      +-+";

/// A 1x1 display: one room writes the pixel, another swaps it in `gap` pipe cells later.
///
/// Both men send `1` on the same tick — colour 1 for DATA, and 1 ("preserve") for SWAP — so a
/// longer SWAP pipe is purely a delay, which is what makes the post-halt drain testable.
pub fn one_pixel_display(gap: usize) -> String {
    let mut rows = vec!["+----+  +=+", "|@1sH|>>: :", "+----+  +=+"];
    rows.extend(std::iter::repeat_n("         ^", gap));
    rows.extend(["      +----+", "      |@1sH|", "      +----+"]);
    rows.join("\n")
}

/// A single room holding `@` + body + `H`, walked west to east on one line.
pub fn one_room(body: &str) -> String {
    let interior = format!("@{body}H");
    let border = format!("+{}+", "-".repeat(interior.chars().count()));
    format!("{border}\n|{interior}|\n{border}")
}

/// Run a one-line room and hand back the little man once he halts.
pub fn walk(body: &str) -> Man {
    let program = load_program(&one_room(body)).expect("one_room should load");
    let mut machine = Machine::new(&program, NullIo);
    machine.run(10_000).expect("one_room should not fault");
    machine.men[0].clone()
}

/// Load a program, or panic with the load error — the tests below all expect valid grids.
pub fn program(source: &str) -> Program {
    load_program(source).unwrap_or_else(|error| panic!("should load: {error}"))
}
