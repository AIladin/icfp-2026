//! Running a program against a test case, with the judge's real semantics.
//!
//! > You pass a test by emitting the correct output in the correct order ... You fail a test the
//! > moment that you emit incorrect output. — language-reference#Judging & halting
//!
//! > A test case contains one or more rounds ... The input for round N+1 is not available until all
//! > output for round N has been received. — grading#Rounds
//!
//! > Judging is still a streaming compare; every frame your display commits (each SWAP ...) must
//! > equal the next expected frame in order ... if [the problem is] round based, frames gate the
//! > next round of input exactly like regular output does. — grading#Display assignments

use serde::Serialize;

use crate::case::TestCase;
use crate::machine::{Frame, Io, Machine, NoTrace, Outcome, Tracer};
use crate::model::Program;

pub const DEFAULT_MAX_TICKS: u64 = 5_000_000;

#[derive(Debug, Clone, Default, Serialize)]
pub struct RunResult {
    pub case: String,
    pub passed: bool,
    pub ticks: u64,
    pub output: Vec<i64>,
    pub expected: Vec<i64>,
    pub matched: usize,
    pub rounds_done: usize,
    pub error: Option<String>,
    pub detail: String,
    /// The cell a wall / bad-op / no-pipe / display error happened at, for the failure report.
    pub cell: Option<(i32, i32)>,
    /// Display-judged cases only: the last frames committed, what was expected, and how far it got.
    pub frames: Vec<Frame>,
    pub expected_frames: Vec<Frame>,
    pub matched_frames: usize,
    /// Total frames committed; `frames` only keeps the last few, so these can differ.
    pub frame_count: u64,
}

#[derive(Debug, Clone, Default)]
pub struct Stage {
    pub inputs: Vec<i64>,
    pub out: Vec<i64>,
    pub frames: Vec<Frame>,
}

/// Feeds input round by round, comparing output and committed frames as they arrive.
pub struct CaseIo {
    pub stages: Vec<Stage>,
    /// The round whose output we are matching — the input gate.
    pub round: usize,
    /// Output values matched within that round.
    pub matched: usize,
    /// Frames committed and matched within that round.
    pub frames_matched: usize,
    pub total_matched: usize,
    pub total_frames: usize,
    feed_round: usize,
    feed_index: usize,
    pub failure: Option<String>,
    pub passed: bool,
    pub pass_tick: u64,
}

impl CaseIo {
    pub fn new(stages: Vec<Stage>) -> Self {
        let mut io = Self {
            stages,
            round: 0,
            matched: 0,
            frames_matched: 0,
            total_matched: 0,
            total_frames: 0,
            feed_round: 0,
            feed_index: 0,
            failure: None,
            passed: false,
            pass_tick: 0,
        };
        io.settle();
        io.passed = io.round >= io.stages.len();
        io
    }

    fn advance(&mut self, tick: u64) -> bool {
        self.settle();
        if self.round < self.stages.len() {
            return true;
        }
        self.passed = true;
        self.pass_tick = tick;
        false
    }

    /// A round with nothing left to produce is complete, which unlocks the next round's input.
    ///
    /// Both halves gate: on a display problem the frames are what the next round waits on.
    fn settle(&mut self) {
        while self.round < self.stages.len() {
            let stage = &self.stages[self.round];
            if self.matched < stage.out.len() || self.frames_matched < stage.frames.len() {
                return;
            }
            self.round += 1;
            self.matched = 0;
            self.frames_matched = 0;
        }
    }
}

impl Io for CaseIo {
    fn take(&mut self) -> Option<i64> {
        while self.feed_round < self.stages.len() && self.feed_round <= self.round {
            let inputs = &self.stages[self.feed_round].inputs;
            if self.feed_index < inputs.len() {
                self.feed_index += 1;
                return Some(inputs[self.feed_index - 1]);
            }
            self.feed_round += 1;
            self.feed_index = 0;
        }
        None
    }

    fn emit(&mut self, value: i64, tick: u64) -> bool {
        if self.round >= self.stages.len() {
            self.failure =
                Some(format!("emitted {value} after the expected output was already complete"));
            return false;
        }
        let expected = &self.stages[self.round].out;
        if self.matched >= expected.len() {
            // Only reachable on a display-judged round, which expects no output at all:
            // "It is an error to emit any output in a display-judged program." — grading
            self.failure = Some(format!(
                "emitted {value} in round {}, which expects no output",
                self.round + 1
            ));
            return false;
        }
        if value != expected[self.matched] {
            self.failure = Some(format!(
                "output value {} was {value}, expected {} (round {})",
                self.total_matched,
                expected[self.matched],
                self.round + 1
            ));
            return false;
        }
        self.matched += 1;
        self.total_matched += 1;
        self.advance(tick)
    }

    fn commit(&mut self, frame: &Frame, tick: u64) -> bool {
        if self.round >= self.stages.len() {
            self.failure =
                Some("committed a frame after the expected frames were already complete".into());
            return false;
        }
        let expected = &self.stages[self.round].frames;
        if self.frames_matched >= expected.len() {
            self.failure = Some(format!(
                "committed a frame in round {}, which expects {} frame(s)",
                self.round + 1,
                expected.len()
            ));
            return false;
        }
        if *frame != expected[self.frames_matched] {
            self.failure = Some(format!(
                "frame {} differs from the expected frame (round {}, frame {} of that round)",
                self.total_frames,
                self.round + 1,
                self.frames_matched + 1
            ));
            return false;
        }
        self.frames_matched += 1;
        self.total_frames += 1;
        self.advance(tick)
    }
}

/// No expectations: all input is available at once and output is only collected.
pub struct FreeIo {
    values: Vec<i64>,
    index: usize,
}

impl FreeIo {
    pub fn new(values: Vec<i64>) -> Self {
        Self { values, index: 0 }
    }
}

impl Io for FreeIo {
    fn take(&mut self) -> Option<i64> {
        if self.index >= self.values.len() {
            return None;
        }
        self.index += 1;
        Some(self.values[self.index - 1])
    }

    fn emit(&mut self, _value: i64, _tick: u64) -> bool {
        true
    }

    fn commit(&mut self, _frame: &Frame, _tick: u64) -> bool {
        true
    }
}

/// Run one test case to a verdict.
pub fn run_case(program: &Program, case: &TestCase, max_ticks: u64) -> RunResult {
    run_case_traced(program, case, max_ticks, NoTrace)
}

/// `ticks` is the tick the final correct output was emitted — or, on a display-judged case, the
/// tick the final expected frame was committed.
pub fn run_case_traced<T: Tracer>(
    program: &Program,
    case: &TestCase,
    max_ticks: u64,
    trace: T,
) -> RunResult {
    let mut stages = Vec::with_capacity(case.rounds.len());
    for round in &case.rounds {
        let (Some(inputs), Some(out)) = (parse_values(&round.inputs), parse_values(&round.out))
        else {
            return RunResult {
                case: case.name.clone(),
                error: Some("bad-case".into()),
                detail: "a test case value is not an integer".into(),
                ..Default::default()
            };
        };
        stages.push(Stage { inputs, out, frames: round.frames.clone().unwrap_or_default() });
    }

    let expected: Vec<i64> = stages.iter().flat_map(|stage| stage.out.clone()).collect();
    let expected_frames: Vec<Frame> = stages.iter().flat_map(|s| s.frames.clone()).collect();
    if let Some(detail) = display_mismatch(program, &expected_frames) {
        return RunResult {
            case: case.name.clone(),
            expected_frames,
            error: Some("display".into()),
            detail,
            ..Default::default()
        };
    }

    let io = CaseIo::new(stages);
    if io.passed {
        // Nothing is expected, so the case is already passed before the first tick.
        return RunResult {
            case: case.name.clone(),
            passed: true,
            rounds_done: io.stages.len(),
            ..Default::default()
        };
    }

    let mut machine = Machine::traced(program, io, trace);
    let outcome = match machine.run(max_ticks) {
        Ok(outcome) => outcome,
        Err(error) => {
            let detail = error.detail.clone();
            return failed(
                &case.name,
                &mut machine,
                expected,
                error.kind.as_str(),
                detail,
                error.cell,
            );
        }
    };

    if machine.io.passed {
        return RunResult {
            case: case.name.clone(),
            passed: true,
            ticks: machine.io.pass_tick,
            matched: machine.io.total_matched,
            rounds_done: machine.io.stages.len(),
            matched_frames: machine.io.total_frames,
            frame_count: machine.frame_count,
            output: std::mem::take(&mut machine.output),
            frames: std::mem::take(&mut machine.frames),
            expected,
            expected_frames,
            error: None,
            detail: String::new(),
            cell: None,
        };
    }
    if let Some(failure) = machine.io.failure.clone() {
        let kind = if expected_frames.is_empty() { "output-mismatch" } else { "frame-mismatch" };
        return failed(&case.name, &mut machine, expected, kind, failure, None);
    }
    if outcome == Outcome::StepCap {
        let detail = format!("hit the step cap of {max_ticks} ticks");
        return failed(&case.name, &mut machine, expected, "step-cap", detail, None);
    }
    let produced = if expected_frames.is_empty() {
        format!("{}/{} expected values", machine.io.total_matched, expected.len())
    } else {
        format!("{}/{} expected frames", machine.io.total_frames, expected_frames.len())
    };
    let detail = format!("every little man stopped after {produced}");
    failed(&case.name, &mut machine, expected, "ended-early", detail, None)
}

/// Why this program cannot be judged on frames at all, if so.
///
/// > Your program must contain exactly one display at the resolution that the assignment states.
/// > — grading#Display assignments
fn display_mismatch(program: &Program, expected_frames: &[Frame]) -> Option<String> {
    if expected_frames.is_empty() {
        return None;
    }
    if program.displays.len() != 1 {
        return Some(format!(
            "a display-judged case needs exactly one display; this program has {}",
            program.displays.len()
        ));
    }
    let display = &program.displays[0];
    let frame = &expected_frames[0];
    let height = frame.len() as i32;
    let width = frame.first().map_or(0, |row| row.len()) as i32;
    if (display.width, display.height) != (width, height) {
        return Some(format!(
            "the expected frames are {width}x{height} but the program's display is {}x{}",
            display.width, display.height
        ));
    }
    None
}

/// Run with no expected output: all input available, everything emitted is collected.
pub fn run_free(program: &Program, values: Vec<i64>, max_ticks: u64) -> RunResult {
    run_free_traced(program, values, max_ticks, NoTrace)
}

pub fn run_free_traced<T: Tracer>(
    program: &Program,
    values: Vec<i64>,
    max_ticks: u64,
    trace: T,
) -> RunResult {
    let mut machine = Machine::traced(program, FreeIo::new(values), trace);
    let outcome = machine.run(max_ticks);
    let (error, detail, cell) = match &outcome {
        Err(error) => (Some(error.kind.as_str().into()), error.detail.clone(), error.cell),
        Ok(Outcome::StepCap) => {
            (Some("step-cap".into()), format!("hit the step cap of {max_ticks} ticks"), None)
        }
        Ok(_) => (None, String::new(), None),
    };
    RunResult {
        case: "free run".into(),
        passed: error.is_none(),
        ticks: machine.tick,
        frame_count: machine.frame_count,
        output: std::mem::take(&mut machine.output),
        frames: std::mem::take(&mut machine.frames),
        error,
        detail,
        cell,
        ..Default::default()
    }
}

fn failed<T: Tracer>(
    name: &str,
    machine: &mut Machine<'_, CaseIo, T>,
    expected: Vec<i64>,
    error: &str,
    detail: String,
    cell: Option<(i32, i32)>,
) -> RunResult {
    RunResult {
        case: name.to_string(),
        passed: false,
        ticks: machine.tick,
        expected,
        matched: machine.io.total_matched,
        rounds_done: machine.io.round,
        error: Some(error.to_string()),
        detail,
        cell,
        expected_frames: machine.io.stages.iter().flat_map(|s| s.frames.clone()).collect(),
        matched_frames: machine.io.total_frames,
        frame_count: machine.frame_count,
        output: std::mem::take(&mut machine.output),
        frames: std::mem::take(&mut machine.frames),
    }
}

/// `max(w, h)² × average ticks`, or just `max(w, h)²`. `None` unless every case passed.
///
/// Ticks after the final correct output are not counted, which [`RunResult::ticks`] already
/// reflects.
pub fn score(program: &Program, results: &[RunResult], scoring: &str) -> Option<f64> {
    if results.is_empty() || !results.iter().all(|result| result.passed) {
        return None;
    }
    let footprint = program.footprint() as f64;
    if scoring == "footprint" {
        return Some(footprint);
    }
    let total: u64 = results.iter().map(|result| result.ticks).sum();
    Some(footprint * (total as f64 / results.len() as f64))
}

fn parse_values(values: &[String]) -> Option<Vec<i64>> {
    values.iter().map(|value| value.trim().parse::<i64>().ok()).collect()
}
