//! `littleman_rs` — the Rust runner as a Python extension module.
//!
//! Deliberately thin. The ergonomics live in `py/libs/runner/src/littleman/fast.py`, which wraps
//! this in the *same* `load_program` / `run_case` / `run_free` / `score` API the pure-Python
//! `littleman` package exposes, so a solver swaps implementations by changing one import.
//!
//! Two things are objects rather than arguments, because a search loop reuses them: a loaded
//! [`Program`] and a parsed [`Case`]. Everything else crosses the boundary as plain Python data.

use pyo3::create_exception;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};

use littleman::{DEFAULT_MAX_TICKS, RunResult, TestCase};

create_exception!(littleman_rs, LoadError, PyValueError, "The program is structurally invalid.");
create_exception!(
    littleman_rs,
    EphemeralError,
    PyValueError,
    "The handoff markers cannot be turned into pipes."
);

/// A loaded program: topology only, no run state, so load once and run it against many cases.
#[pyclass(frozen, module = "littleman_rs")]
pub struct Program(littleman::Program);

#[pymethods]
impl Program {
    /// Parse and validate a `.man` program, raising `LoadError` on anything structural.
    #[new]
    fn new(source: &str) -> PyResult<Self> {
        littleman::load_program(source)
            .map(Program)
            .map_err(|error| LoadError::new_err(error.to_string()))
    }

    /// `max(width, height)²` over the content bounding box — the size term of the score.
    fn footprint(&self) -> i64 {
        self.0.footprint()
    }

    /// What the loader made of the program, the same text `lmr check` prints.
    fn summary(&self) -> String {
        littleman::summary(&self.0)
    }

    #[getter]
    fn displays(&self) -> usize {
        self.0.displays.len()
    }

    #[getter]
    fn rooms(&self) -> usize {
        self.0.rooms.len()
    }

    #[getter]
    fn pipes(&self) -> usize {
        self.0.pipes.len()
    }

    fn __repr__(&self) -> String {
        let (width, height) = self.0.grid.footprint();
        format!("<littleman_rs.Program {width}x{height} footprint={}>", self.0.footprint())
    }
}

/// One test case, parsed once so a search loop does not re-parse it per candidate.
///
/// Built from the JSON of an `icfp_api.models.TestCase` — that is what keeps the two runners
/// agreeing about `publicTestData`'s two shapes rather than each guessing separately.
#[pyclass(frozen, module = "littleman_rs")]
pub struct Case(TestCase);

#[pymethods]
impl Case {
    #[new]
    fn new(json: &str) -> PyResult<Self> {
        let value = serde_json::from_str(json)
            .map_err(|error| PyValueError::new_err(format!("case is not JSON: {error}")))?;
        TestCase::from_json(value)
            .map(Case)
            .map_err(|error| PyValueError::new_err(format!("not a test case: {error}")))
    }

    #[getter]
    fn name(&self) -> &str {
        &self.0.name
    }

    #[getter]
    fn rounds(&self) -> usize {
        self.0.rounds.len()
    }

    fn __repr__(&self) -> String {
        format!("<littleman_rs.Case {:?} rounds={}>", self.0.name, self.0.rounds.len())
    }
}

/// Run one test case to a verdict. Returns the fields of a `littleman.judge.RunResult`.
#[pyfunction]
#[pyo3(signature = (program, case, max_ticks = DEFAULT_MAX_TICKS))]
fn run_case<'py>(
    py: Python<'py>,
    program: &Program,
    case: &Case,
    max_ticks: u64,
) -> PyResult<Bound<'py, PyDict>> {
    let result = py.detach(|| littleman::run_case(&program.0, &case.0, max_ticks));
    to_dict(py, &result)
}

/// Run with no expected output: all input available, everything emitted is collected.
#[pyfunction]
#[pyo3(signature = (program, values, max_ticks = DEFAULT_MAX_TICKS))]
fn run_free<'py>(
    py: Python<'py>,
    program: &Program,
    values: Vec<i64>,
    max_ticks: u64,
) -> PyResult<Bound<'py, PyDict>> {
    let result = py.detach(|| littleman::run_free(&program.0, values, max_ticks));
    to_dict(py, &result)
}

/// The `RunResult` dataclass's fields, ready for `RunResult(**payload)`.
///
/// `frames` come back as tuples of `str`, matching the Python runner's `Frame` alias, so the two
/// implementations' results compare equal without any coercion in between.
fn to_dict<'py>(py: Python<'py>, result: &RunResult) -> PyResult<Bound<'py, PyDict>> {
    let frames = |frames: &[Vec<String>]| -> PyResult<Bound<'py, PyList>> {
        let rows: Vec<Bound<'py, PyTuple>> =
            frames.iter().map(|frame| PyTuple::new(py, frame)).collect::<PyResult<_>>()?;
        PyList::new(py, rows)
    };

    let payload = PyDict::new(py);
    payload.set_item("case", &result.case)?;
    payload.set_item("passed", result.passed)?;
    payload.set_item("ticks", result.ticks)?;
    payload.set_item("output", &result.output)?;
    payload.set_item("expected", &result.expected)?;
    payload.set_item("matched", result.matched)?;
    payload.set_item("rounds_done", result.rounds_done)?;
    payload.set_item("error", &result.error)?;
    payload.set_item("detail", &result.detail)?;
    payload.set_item("cell", result.cell)?;
    payload.set_item("frames", frames(&result.frames)?)?;
    payload.set_item("expected_frames", frames(&result.expected_frames)?)?;
    payload.set_item("matched_frames", result.matched_frames)?;
    payload.set_item("frame_count", result.frame_count)?;
    Ok(payload)
}

/// Synthesise pipes from handoff markers — the Rust twin of `littleman.ephemeral.synthesise`.
///
/// Returns `(source, labels, warnings, report, graph)` as plain Python data rather than a class:
/// the parity harness diffs those five things, and nothing else needs a handle on the result.
/// The synthesised grid and the pipe graph are the contract; see
/// `docs/vault/heap/The retry order is a specification, not a shuffle.md` for why they must match
/// the Python router cell for cell.
#[pyfunction]
#[pyo3(signature = (source, min_lengths = None))]
fn synthesise<'py>(
    py: Python<'py>,
    source: &str,
    min_lengths: Option<std::collections::BTreeMap<String, usize>>,
) -> PyResult<Bound<'py, PyTuple>> {
    let lengths = min_lengths.unwrap_or_default();
    let result = littleman::ephemeral::synthesise(source, &lengths)
        .map_err(|error| EphemeralError::new_err(error.0))?;
    let labels = PyDict::new(py);
    for (index, label) in &result.labels {
        labels.set_item(index, label)?;
    }
    let graph = littleman::ephemeral::pipe_graph(&result.program, &result.labels);
    (result.source, labels, result.warnings, result.report, graph).into_pyobject(py)
}

/// `count` steps of the router's xorshift64, so the parity harness can pin the generator itself.
///
/// The permutations it drives are a cross-language contract; this is the cheapest possible check
/// that both sides still agree about the bits underneath them.
#[pyfunction]
fn xorshift_chain(seed: u64, count: usize) -> Vec<u64> {
    let mut state = seed;
    (0..count)
        .map(|_| {
            state = littleman::ephemeral::xorshift(state);
            state
        })
        .collect()
}

/// The version of the `littleman` crate this module was built from.
#[pyfunction]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[pymodule]
fn littleman_rs(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<Program>()?;
    module.add_class::<Case>()?;
    module.add("LoadError", module.py().get_type::<LoadError>())?;
    module.add("EphemeralError", module.py().get_type::<EphemeralError>())?;
    module.add("DEFAULT_MAX_TICKS", DEFAULT_MAX_TICKS)?;
    module.add_function(wrap_pyfunction!(run_case, module)?)?;
    module.add_function(wrap_pyfunction!(run_free, module)?)?;
    module.add_function(wrap_pyfunction!(synthesise, module)?)?;
    module.add_function(wrap_pyfunction!(xorshift_chain, module)?)?;
    module.add_function(wrap_pyfunction!(version, module)?)?;
    Ok(())
}
