//! `lmr` — load, run, and judge Littleman programs locally, at Rust speed.
//!
//! Flag for flag and `--json` shape for `--json` shape, this is the Python `lm`. The two are meant
//! to be interchangeable so that `diff <(lm … --json) <(lmr … --json)` is a parity check.
//!
//! The one thing it does not do is talk to the contest server: `--problem` shells out to
//! `icfp problem <slug> --json`, because `py/libs/api_client` is the only thing in this repo
//! allowed to make an HTTP request, and delegating means the two runners cannot disagree about how
//! a problem's test data was parsed.

use std::io::{IsTerminal, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};

use std::collections::BTreeMap;

use clap::{Args, Parser, Subcommand};
use littleman::ephemeral::{BANNER, Synthesis, pipe_graph, synthesise};
use littleman::{
    DEFAULT_MAX_TICKS, Frame, LoadError, Printer, Problem, Program, RunResult, failure_report,
    load_program, parse_cases, run_case, run_case_traced, run_free, run_free_traced, score,
    summary,
};

const EPHEMERAL_HELP: &str = "Synthesise pipes from the handoff markers (letter pairs a/A, or labelled b1/B1) instead of \
     requiring drawn ones. Proves the LOGIC, not the LAYOUT — and never replaces a submission.";
const LENGTH_HELP: &str =
    "Minimum cells per pipe, by pipe name: 'a=6,2=4'. Needs --ephemeral-pipes.";
const OUT_HELP: &str =
    "Write the synthesised grid here, to start packing from. Needs --ephemeral-pipes.";

/// The three `--ephemeral-*` flags, shared by `check`, `run` and `test` exactly as in `lm`.
#[derive(Args, Clone)]
struct EphemeralArgs {
    /// Synthesise pipes from handoff markers.
    #[arg(long = "ephemeral-pipes", help = EPHEMERAL_HELP)]
    ephemeral: bool,
    /// Minimum cells per pipe.
    #[arg(long = "pipe-length", default_value = "", help = LENGTH_HELP)]
    lengths: String,
    /// Write the synthesised grid here.
    #[arg(long = "ephemeral-out", help = OUT_HELP)]
    write_to: Option<PathBuf>,
}

#[derive(Parser)]
#[command(name = "lmr", about = "Run Littleman (.man) programs locally.", version)]
struct Cli {
    #[command(subcommand)]
    command: CommandKind,
}

#[derive(Subcommand)]
enum CommandKind {
    /// Load a program and report its structure — every load error, before spending a submission.
    Check(CheckArgs),
    /// Run a program with no expected output and print whatever it emits.
    Run(RunArgs),
    /// Judge a program against a problem's public test cases, exactly as the server would.
    Test(TestArgs),
}

#[derive(Args)]
struct CheckArgs {
    /// File holding the program grid.
    program: PathBuf,
    #[command(flatten)]
    ephemeral: EphemeralArgs,
}

#[derive(Args)]
struct RunArgs {
    /// File holding the program grid.
    program: PathBuf,
    /// Whitespace-separated integers to feed in.
    #[arg(long = "input", short = 'i', default_value = "")]
    values: String,
    /// Step cap.
    #[arg(long, default_value_t = DEFAULT_MAX_TICKS)]
    ticks: u64,
    /// Print machine state every tick.
    #[arg(long)]
    trace: bool,
    /// Also show output as text.
    #[arg(long = "ascii")]
    as_ascii: bool,
    /// Show every committed frame, not just the last.
    #[arg(long)]
    frames: bool,
    /// Draw frames as colour blocks instead of hex.
    #[arg(long)]
    pixels: bool,
    /// Emit raw JSON.
    #[arg(long = "json")]
    as_json: bool,
    #[command(flatten)]
    ephemeral: EphemeralArgs,
}

#[derive(Args)]
struct TestArgs {
    /// File holding the program grid.
    program: PathBuf,
    /// Fetch public cases for this slug (via the `icfp` CLI).
    #[arg(long, short = 'p')]
    problem: Option<String>,
    /// Read cases from `icfp tests` JSON.
    #[arg(long, short = 'c')]
    cases: Option<PathBuf>,
    /// Only run cases whose name contains this.
    #[arg(long = "case")]
    only: Option<String>,
    /// Step cap; defaults to the problem's.
    #[arg(long)]
    ticks: Option<u64>,
    /// Print machine state every tick.
    #[arg(long)]
    trace: bool,
    /// Emit raw JSON.
    #[arg(long = "json")]
    as_json: bool,
    #[command(flatten)]
    ephemeral: EphemeralArgs,
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    let outcome = match cli.command {
        CommandKind::Check(args) => check(args),
        CommandKind::Run(args) => run(args),
        CommandKind::Test(args) => test(args),
    };
    match outcome {
        Ok(true) => ExitCode::SUCCESS,
        Ok(false) => ExitCode::FAILURE,
        // An empty message means the failure already put its own line on stderr, verbatim as `lm`
        // writes it. `lm` prints its `--pipe-length` usage complaint without a prefix, and flag
        // parity is measured by diffing the two.
        Err(message) => {
            if !message.is_empty() {
                eprintln!("error: {message}");
            }
            ExitCode::FAILURE
        }
    }
}

/// An OS error the way Python's `strerror` words it — `to_string()` adds a ` (os error 2)` tail
/// that `lm` has no way to produce, and a mistyped path is a message the two must agree on.
fn reason(error: &std::io::Error) -> String {
    let text = error.to_string();
    text.split_once(" (os error ").map_or(text.clone(), |(head, _)| head.to_string())
}

fn load(path: &Path, ephemeral: &EphemeralArgs) -> Result<Program, String> {
    let source = std::fs::read_to_string(path)
        .map_err(|error| format!("{}: {}", path.display(), reason(&error)))?;
    if !ephemeral.ephemeral {
        return load_program(&source).map_err(|LoadError(message)| message);
    }
    let lengths = pipe_lengths(&ephemeral.lengths)?;
    let result = synthesise(&source, &lengths).map_err(|error| error.0)?;
    show_synthesis(&result, ephemeral.write_to.as_deref())?;
    Ok(result.program)
}

/// `--pipe-length '1=6,2=4'` -> {'1': 6, '2': 4}.
fn pipe_lengths(spec: &str) -> Result<BTreeMap<String, usize>, String> {
    let mut lengths = BTreeMap::new();
    for item in spec.split(',') {
        if item.trim().is_empty() {
            continue;
        }
        let (label, count) = item.split_once('=').unwrap_or((item, ""));
        let count = count.trim();
        if count.is_empty() || !count.bytes().all(|b| b.is_ascii_digit()) {
            // Printed here, with `lm`'s own single quotes and without the `error:` prefix `lm`
            // also omits for this one.
            eprintln!("--pipe-length wants LABEL=CELLS pairs, got '{}'", item.trim());
            return Err(String::new());
        }
        lengths.insert(label.trim().to_string(), count.parse().map_err(|_| "bad count")?);
    }
    Ok(lengths)
}

/// The grid we invented, the pipe graph it produced, and everything that can move under it.
///
/// Everything goes to stderr, as it does in `lm`, so `--json` on stdout stays a clean diff.
fn show_synthesis(result: &Synthesis, write_to: Option<&Path>) -> Result<(), String> {
    eprintln!("{BANNER}");
    // `source` already ends in a newline; `lm` prints it through rich, which adds one more.
    eprintln!("{}", result.source);
    for line in pipe_graph(&result.program, &result.labels).iter().chain(result.report.iter()) {
        eprintln!("{line}");
    }
    for warning in &result.warnings {
        eprintln!("{warning}");
    }
    if result.warnings.is_empty() {
        eprintln!("no nearest-pipe ambiguity under this geometry");
    }
    if let Some(path) = write_to {
        std::fs::write(path, &result.source)
            .map_err(|error| format!("{}: {error}", path.display()))?;
        eprintln!("synthesised grid written to {}", path.display());
    }
    Ok(())
}

fn check(args: CheckArgs) -> Result<bool, String> {
    println!("{}", summary(&load(&args.program, &args.ephemeral)?));
    Ok(true)
}

fn run(args: RunArgs) -> Result<bool, String> {
    let program = load(&args.program, &args.ephemeral)?;
    let values: Vec<i64> = args
        .values
        .split_whitespace()
        .map(|value| value.parse::<i64>().map_err(|_| format!("{value:?} is not an integer")))
        .collect::<Result<_, _>>()?;

    let result = if args.trace {
        run_free_traced(&program, values, args.ticks, Printer::new(std::io::stderr()))
    } else {
        run_free(&program, values, args.ticks)
    };

    if args.as_json {
        println!("{}", to_json(&result)?);
        return Ok(result.passed);
    }

    println!("{}", join(&result.output));
    if args.as_ascii {
        println!("ascii: {:?}", as_text(&result.output));
    }
    let kept: &[Frame] = if args.frames {
        &result.frames
    } else {
        result.frames.last().map_or(&[], std::slice::from_ref)
    };
    show_frames(kept, result.frame_count, args.pixels);
    println!("{} tick(s)", result.ticks);
    if result.passed {
        return Ok(true);
    }
    eprintln!("{}", failure_report(&program.grid, &result));
    Ok(false)
}

fn test(args: TestArgs) -> Result<bool, String> {
    if args.problem.is_some() == args.cases.is_some() {
        return Err("pass exactly one of --problem or --cases".into());
    }

    let (mut suite, scoring, cap) = match (&args.problem, &args.cases) {
        (Some(slug), _) => {
            let problem = fetch(slug)?;
            let scoring = if problem.scoring.is_empty() {
                "footprint-tick".into()
            } else {
                problem.scoring.clone()
            };
            (problem.cases(), scoring, problem.tick_cap)
        }
        (_, Some(path)) => {
            let payload = std::fs::read_to_string(path)
                .map_err(|error| format!("{}: {error}", path.display()))?;
            let cases =
                parse_cases(&payload).map_err(|error| format!("{}: {error}", path.display()))?;
            (cases, "footprint-tick".to_string(), None)
        }
        _ => unreachable!("exactly one is set"),
    };
    let cap = args.ticks.or(cap).unwrap_or(DEFAULT_MAX_TICKS);

    if let Some(only) = &args.only {
        let only = only.to_lowercase();
        suite.retain(|case| case.name.to_lowercase().contains(&only));
    }
    if suite.is_empty() {
        return Err("no test cases to run".into());
    }

    let program = load(&args.program, &args.ephemeral)?;
    let results: Vec<RunResult> = suite
        .iter()
        .map(|case| {
            if args.trace {
                run_case_traced(&program, case, cap, Printer::new(std::io::stderr()))
            } else {
                run_case(&program, case, cap)
            }
        })
        .collect();
    let total = score(&program, &results, &scoring);
    let passed = results.iter().all(|result| result.passed);

    if args.as_json {
        // A struct rather than `serde_json::json!`: the macro builds a `Value`, whose map sorts
        // keys, and the contract with `lm --json` is that the two outputs diff cleanly.
        let payload = TestJson {
            footprint: program.footprint(),
            scoring: &scoring,
            score: total,
            results: &results,
        };
        println!("{}", serde_json::to_string_pretty(&payload).map_err(|e| e.to_string())?);
        return Ok(passed);
    }

    report(&program, &results, &scoring, total);
    Ok(passed)
}

/// The `lm test --json` payload, field for field and in the same order.
#[derive(serde::Serialize)]
struct TestJson<'a> {
    footprint: i64,
    scoring: &'a str,
    score: Option<f64>,
    results: &'a [RunResult],
}

/// `icfp problem <slug> --json`, the repo's one HTTP layer, run as a subprocess.
fn fetch(slug: &str) -> Result<Problem, String> {
    let output = Command::new("icfp")
        .args(["problem", slug, "--json"])
        .output()
        .map_err(|error| format!("could not run `icfp` ({error}) — is the devenv shell active?"))?;
    if !output.status.success() {
        let message = String::from_utf8_lossy(&output.stderr);
        return Err(format!("`icfp problem {slug} --json` failed: {}", message.trim()));
    }
    serde_json::from_slice(&output.stdout)
        .map_err(|error| format!("could not read `icfp problem {slug} --json`: {error}"))
}

fn to_json(result: &RunResult) -> Result<String, String> {
    serde_json::to_string_pretty(result).map_err(|error| error.to_string())
}

fn join(values: &[i64]) -> String {
    values.iter().map(|value| value.to_string()).collect::<Vec<_>>().join(" ")
}

/// Render output as text, which is all some problems' integers are.
fn as_text(values: &[i64]) -> String {
    values
        .iter()
        .map(|&value| u32::try_from(value).ok().and_then(char::from_u32).unwrap_or('?'))
        .collect()
}

/// Committed frames, newest last. Hex rows are the wire format, so they diff against the API.
fn show_frames(frames: &[Frame], count: u64, pixels: bool) {
    if count == 0 {
        return;
    }
    let shown = frames.len() as u64;
    let kept = if shown < count { format!(" (showing the last {shown})") } else { String::new() };
    println!("{count} frame(s) committed{kept}");
    let colour = std::io::stdout().is_terminal();
    let mut out = std::io::stdout().lock();
    for (offset, frame) in frames.iter().enumerate() {
        let _ = writeln!(out, "frame {}", count - shown + offset as u64);
        for row in frame {
            if !pixels {
                let _ = writeln!(out, "{row}");
                continue;
            }
            for char in row.chars() {
                let index = char.to_digit(16).unwrap_or(0);
                if colour {
                    let _ = write!(out, "\x1b[48;5;{index}m  \x1b[0m");
                } else {
                    let _ = write!(out, "{char}{char}");
                }
            }
            let _ = writeln!(out);
        }
    }
}

fn report(program: &Program, results: &[RunResult], scoring: &str, total: Option<f64>) {
    let judged_on_frames = results.iter().any(|result| !result.expected_frames.is_empty());
    let name_width =
        results.iter().map(|r| display_name(r).len()).max().unwrap_or(4).max("case".len());

    let mut header = format!("{:<name_width$}  verdict  {:>8}", "case", "ticks");
    if judged_on_frames {
        header.push_str(&format!("  {:>9}", "frames"));
    }
    header.push_str("  output");
    println!("{header}");

    for result in results {
        let verdict =
            if result.passed { "pass" } else { result.error.as_deref().unwrap_or("fail") };
        let mut row =
            format!("{:<name_width$}  {verdict:<7}  {:>8}", display_name(result), result.ticks);
        if judged_on_frames {
            let frames = format!("{}/{}", result.matched_frames, result.expected_frames.len());
            row.push_str(&format!("  {frames:>9}"));
        }
        let emitted = join(&result.output);
        row.push_str(&format!("  {}", &emitted[..emitted.len().min(60)]));
        println!("{}", row.trim_end());
    }

    let passed = results.iter().filter(|result| result.passed).count();
    println!("passed {passed}/{}  footprint {}", results.len(), program.footprint());
    if let Some(total) = total {
        println!("score  {}  ({scoring})", thousands(total));
    }
    for result in results {
        if result.passed {
            continue;
        }
        eprintln!("\n{}", display_name(result));
        eprintln!("{}", failure_report(&program.grid, result));
    }
}

fn display_name(result: &RunResult) -> &str {
    if result.case.is_empty() { "(unnamed)" } else { &result.case }
}

/// `7,702,428` — the same grouping `lm`'s `{:,.0f}` produces, so scores diff by eye.
fn thousands(value: f64) -> String {
    let rounded = format!("{:.0}", value);
    let (sign, digits) = rounded.strip_prefix('-').map_or(("", rounded.as_str()), |d| ("-", d));
    let mut grouped = String::new();
    for (index, char) in digits.chars().enumerate() {
        if index > 0 && (digits.len() - index) % 3 == 0 {
            grouped.push(',');
        }
        grouped.push(char);
    }
    format!("{sign}{grouped}")
}
