use std::path::{Path, PathBuf};

use littleman::{TestCase, parse_cases};

use crate::cli::Args;
use crate::{
    PackError, anneal, assemble, check, compact, design, library, planar, report, seed, validate,
};

pub fn run(args: &Args) -> Result<(), PackError> {
    let rooms_dir = match &args.rooms {
        Some(dir) => dir.clone(),
        None => find_rooms_dir(&args.design)?,
    };
    let library = library::load_library(&rooms_dir)?;
    let design = design::load_design(&args.design, &library)?;
    planar::require_planar(&design)?;
    let cases = load_cases(args.cases.as_deref())?;

    if args.logic_check {
        return check::run(
            &library,
            &design,
            &args.design,
            &cases,
            args.ticks,
            args.logic_trace,
            args.json,
        );
    }

    let hint = load_hint(args)?;
    let start = seed::seed(&library, &design, args.seed, hint.as_ref())?;
    let seeded_state = start.realize(&library, &design);
    let seeded =
        validate::route(&library, &design, &seeded_state, littleman::ephemeral::NEGOTIATION_ROUNDS)
            .ok_or_else(|| PackError("seed routed once and then did not — bug".into()))?;
    let seed_dim = validate::max_dim(&seeded);
    let seed_judged = match cases.is_empty() {
        true => None,
        false => Some(validate::judge(&seeded, &cases, args.ticks)),
    };
    if let Some(judged) = &seed_judged
        && judged.passed != judged.total
    {
        return Err(PackError(format!(
            "the seed layout routes but passes only {}/{} cases — the room logic itself is wrong, \
             and packing cannot fix logic. Check the variants and the netlist first.",
            judged.passed, judged.total
        )));
    }
    print_seed_summary(&library, &design, &seeded_state, seed_dim);

    let seconds = if args.check { 0.0 } else { args.seconds };
    let options = anneal::Options {
        seconds,
        polish: if args.check { 0.0 } else { args.polish.unwrap_or(seconds * 0.2).max(0.0) },
        seed: args.seed,
        max_ticks: args.ticks,
        keep: args.keep.max(1),
        jobs: args.jobs.unwrap_or_else(default_jobs).max(1),
    };
    match args.check {
        true => eprintln!("--check: seeded and routed, not searched"),
        false => eprintln!(
            "annealing: {} chains x {:.0}s floorplan + {:.0}s polish",
            options.jobs, options.seconds, options.polish
        ),
    }
    let (mut results, stats) =
        anneal::anneal(&library, &design, start, &cases, &options).map_err(PackError)?;

    if !args.check && !cases.is_empty() && args.compact_seconds > 0.0 {
        let (alternatives, compact_stats) = compact::compact(
            &library,
            &design,
            &results[0],
            &cases,
            args.ticks,
            args.compact_seconds,
        );
        results.extend(alternatives);
        results = anneal::rank_candidates(results, options.keep);
        eprintln!("{}", compact_stats.report());
    }

    let out = args.out.clone().unwrap_or_else(|| report::default_out(&args.design));
    report::write(
        &report::Options {
            design_path: &args.design,
            json: args.json,
            seed_dim,
            seed_judged: seed_judged.as_ref(),
        },
        &design,
        &results,
        &out,
    )?;
    let moves = stats.report();
    if !args.json && !moves.is_empty() {
        println!("\nmoves:");
        for line in moves {
            println!("{line}");
        }
    }
    Ok(())
}

fn load_cases(path: Option<&Path>) -> Result<Vec<TestCase>, PackError> {
    let Some(path) = path else {
        eprintln!(
            "WARN no --cases: candidates are routed and bind-checked but NOT judged — pass \
             `icfp tests <slug> -o cases.json` output before trusting the result"
        );
        return Ok(Vec::new());
    };
    let raw = std::fs::read_to_string(path)
        .map_err(|e| PackError(format!("cannot read {}: {e}", path.display())))?;
    parse_cases(&raw).map_err(|e| PackError(format!("{}: {e}", path.display())))
}

fn print_seed_summary(
    library: &library::Library,
    design: &design::Design,
    state: &assemble::State,
    seed_dim: i32,
) {
    let occupied: usize = (0..design.instances.len())
        .map(|i| assemble::variant_of(library, design, state, i).occupied)
        .sum();
    let floor = (occupied as f64).sqrt().ceil() as i32;
    eprintln!(
        "seed: max-dim {seed_dim}, {} rooms, {} pipes, {occupied} occupied interior cells \
         (floor ~{floor}x{floor})",
        design.instances.len(),
        design.pipes.len(),
    );
}

/// The planar hint: `--hint`, or `hint.json` beside the design, or none (layered fallback).
fn load_hint(args: &Args) -> Result<Option<seed::Hint>, PackError> {
    let path = match &args.hint {
        Some(path) => path.clone(),
        None => {
            let default = args.design.with_file_name("hint.json");
            if !default.exists() {
                eprintln!(
                    "note: no planar hint — run `uv run python eman_hint.py <design>` for a \
                     certified planar seed; using the layered fallback"
                );
                return Ok(None);
            }
            default
        }
    };
    let raw = std::fs::read_to_string(&path)
        .map_err(|e| PackError(format!("cannot read {}: {e}", path.display())))?;
    #[derive(serde::Deserialize)]
    struct HintFile {
        pos: std::collections::BTreeMap<String, (i32, i32)>,
    }
    let parsed: HintFile =
        serde_json::from_str(&raw).map_err(|e| PackError(format!("{}: {e}", path.display())))?;
    eprintln!("planar hint: {} ({} rooms)", path.display(), parsed.pos.len());
    Ok(Some(parsed.pos))
}

/// Walk up from the design file looking for `rooms/` — the library is global to the repo.
fn find_rooms_dir(design: &Path) -> Result<PathBuf, PackError> {
    let start = design.parent().unwrap_or(Path::new("."));
    let absolute = std::fs::canonicalize(start)
        .map_err(|e| PackError(format!("cannot resolve {}: {e}", start.display())))?;
    for dir in absolute.ancestors() {
        let candidate = dir.join("rooms");
        if candidate.is_dir() {
            return Ok(candidate);
        }
    }
    Err(PackError(format!("no `rooms/` directory found above {} — pass --rooms", design.display())))
}

/// Leave two cores for whoever is using the machine.
fn default_jobs() -> usize {
    std::thread::available_parallelism().map_or(4, |cores| cores.get().saturating_sub(2).max(1))
}
