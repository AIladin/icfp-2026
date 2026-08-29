//! Simulated annealing over placements, in two stages that fail at opposite ends.
//!
//! **Stage 1 anneals a [`Floorplan`]** — a B\*-tree, where the placement is derived by contour
//! packing and is compact and overlap-free by construction. One topological move re-compacts
//! everything downstream of it, which is how the search gets from a sprawling seed to something
//! tight. What it cannot do is nudge one room two cells without disturbing half the design.
//!
//! **Stage 2 polishes the winner's coordinates** with the free-coordinate move set — translate,
//! swap, pull toward the centroid — which is exactly the local relief the tree has no move for.
//! It is one-directional on purpose: a polished placement is no longer admissible, so it cannot be
//! handed back to the tree. The deliverable is a `.man`, not a floorplan.
//!
//! Every candidate that passes the geometric pre-filter is actually routed — single-layer
//! routability is the real constraint and no proxy captures it — and the cost is `max(w, h)` of the
//! routed grid, with total pipe cells as a tiebreak so a max-dim plateau still has a gradient.

use std::time::Instant;

use littleman::TestCase;
use littleman::ephemeral::NEGOTIATION_ROUNDS;
use littleman::model::DELTAS;
use rayon::prelude::*;

use crate::assemble::State;
use crate::design::Design;
use crate::floorplan::Floorplan;
use crate::library::Library;
use crate::rng::Rng;
use crate::validate::{self, Judged};

#[derive(Clone)]
pub struct Candidate {
    pub state: State,
    pub source: String,
    pub max_dim: i32,
    pub route_cells: usize,
    pub judged: Option<Judged>,
    pub report: Vec<String>,
    pub warnings: Vec<String>,
}

pub struct Options {
    pub seconds: f64,
    /// Budget for the coordinate polish stage. Zero skips it.
    pub polish: f64,
    pub seed: u64,
    pub max_ticks: u64,
    pub keep: usize,
    /// Independent SA chains run in parallel. Every evaluation is pure, so this is throughput and
    /// basin diversity for free; see [`anneal`].
    pub jobs: usize,
}

/// Negotiation rounds inside the search loop — a hopeless placement should give up early. The
/// admission path negotiates the full pool, so a keeper never loses to an early cut-off.
const SEARCH_ROUNDS: usize = 6;

const MOVES: usize = 6;
const MOVE_NAMES: [&str; MOVES] = ["relocate", "swap", "variant", "halo-", "halo+", "global-halo"];

/// Iterations without a new best before a chain is considered locked, at minimum — the real
/// threshold grows with how long the chain has already run.
const MIN_PATIENCE: u64 = 400;

/// Restarts from the best allowed before a locked chain gives up entirely.
const RESTARTS: u32 = 3;

/// Per-move-kind acceptance accounting. The whole reason the previous placer plateaued was a move
/// set whose neighbours were nearly all infeasible, and that failure is invisible unless counted:
/// a move kind that is tried constantly and never routes is the search hitting a wall, not
/// exploring.
#[derive(Default, Clone)]
pub struct Stats {
    pub tried: [u64; MOVES],
    pub unroutable: [u64; MOVES],
    pub accepted: [u64; MOVES],
    pub polish_tried: u64,
    pub polish_unroutable: u64,
    pub polish_accepted: u64,
    pub congested: u64,
    pub congested_cells: u64,
    pub congested_pressure: u64,
    /// Times a locked chain jumped back to its own best rather than carrying on downhill.
    pub restarts: u64,
    /// Chains that gave up before the budget ran out, having exhausted their restarts.
    pub stopped_early: u64,
}

impl Stats {
    fn merge(&mut self, other: &Stats) {
        for index in 0..MOVES {
            self.tried[index] += other.tried[index];
            self.unroutable[index] += other.unroutable[index];
            self.accepted[index] += other.accepted[index];
        }
        self.polish_tried += other.polish_tried;
        self.polish_unroutable += other.polish_unroutable;
        self.polish_accepted += other.polish_accepted;
        self.congested += other.congested;
        self.congested_cells += other.congested_cells;
        self.congested_pressure += other.congested_pressure;
        self.restarts += other.restarts;
        self.stopped_early += other.stopped_early;
    }

    /// One line per move kind: tried, how many failed to route, how many were accepted.
    pub fn report(&self) -> Vec<String> {
        let percent = |part: u64, whole: u64| match whole {
            0 => 0.0,
            _ => part as f64 / whole as f64 * 100.0,
        };
        let mut lines: Vec<String> = (0..MOVES)
            .filter(|&index| self.tried[index] > 0)
            .map(|index| {
                format!(
                    "  {:<12} {:>8} tried  {:>5.1}% unroutable  {:>5.1}% accepted",
                    MOVE_NAMES[index],
                    self.tried[index],
                    percent(self.unroutable[index], self.tried[index]),
                    percent(self.accepted[index], self.tried[index]),
                )
            })
            .collect();
        if self.polish_tried > 0 {
            lines.push(format!(
                "  {:<12} {:>8} tried  {:>5.1}% unroutable  {:>5.1}% accepted",
                "polish",
                self.polish_tried,
                percent(self.polish_unroutable, self.polish_tried),
                percent(self.polish_accepted, self.polish_tried),
            ));
        }
        if self.congested > 0 {
            lines.push(format!(
                "  {:<12} {} placement(s) congested, avg {:.1} cells / {:.1} pipe-pressure",
                "tree routing",
                self.congested,
                self.congested_cells as f64 / self.congested as f64,
                self.congested_pressure as f64 / self.congested as f64,
            ));
        }
        if self.restarts > 0 || self.stopped_early > 0 {
            lines.push(format!(
                "  {:<12} {} restart(s) from best, {} chain(s) stopped early",
                "locked", self.restarts, self.stopped_early
            ));
        }
        lines
    }
}

pub(crate) fn cost(max_dim: i32, route_cells: usize) -> i64 {
    max_dim as i64 * 100_000 + route_cells as i64
}

/// Spread the island streams with the golden-ratio odd constant so neighbouring islands do not
/// walk correlated sequences.
fn stream(seed: u64, island: usize) -> Rng {
    Rng::new(seed ^ (island as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15))
}

/// What one island brings home.
struct Outcome {
    candidates: Vec<Candidate>,
    best: Option<(i64, Floorplan)>,
    stats: Stats,
}

/// Anneal from `start` until the budget runs out. Returns the accepted-best candidates, best
/// first, at most `keep` distinct max-dims — every one routed, bound-checked, and (when cases are
/// given) passing every case — plus the move accounting.
///
/// Both stages run as an **island model**: `options.jobs` independent chains from the same start,
/// each with its own RNG stream and its own temperature scale, merged at the end. Every evaluation
/// is a pure function of `(library, design, state)`, so the chains share nothing.
pub fn anneal(
    library: &Library,
    design: &Design,
    start: Floorplan,
    cases: &[TestCase],
    options: &Options,
) -> Result<(Vec<Candidate>, Stats), String> {
    let seeded_state = start.realize(library, design);
    validate::route(library, design, &seeded_state, NEGOTIATION_ROUNDS).ok_or(
        "the seed floorplan stopped routing — this is a bug, the seed was routed once already",
    )?;
    let mut results: Vec<Candidate> = Vec::new();
    admit(&mut results, library, design, &seeded_state, cases, options);
    if results.is_empty() {
        return Err(match cases.is_empty() {
            true => "the seed did not survive admission — bug".into(),
            false => "the seed routes but fails the test cases — the room logic itself is wrong, \
                      packing cannot fix that. Run the variants through `lm test` first."
                .into(),
        });
    }

    let jobs = options.jobs.max(1);
    let outcomes: Vec<Outcome> = (0..jobs)
        .into_par_iter()
        .map(|island| chain(library, design, &start, cases, options, island))
        .collect();

    let mut stats = Stats::default();
    let mut best: Option<(i64, Floorplan)> = None;
    for outcome in outcomes {
        stats.merge(&outcome.stats);
        results.extend(outcome.candidates);
        if let Some((score, plan)) = outcome.best
            && best.as_ref().is_none_or(|(prior, _)| score < *prior)
        {
            best = Some((score, plan));
        }
    }

    if options.polish > 0.0
        && let Some((_, plan)) = &best
    {
        let from = plan.realize(library, design);
        let polished: Vec<(Vec<Candidate>, Stats)> = (0..jobs)
            .into_par_iter()
            .map(|island| polish(library, design, &from, cases, options, island))
            .collect();
        for (candidates, chain_stats) in polished {
            stats.merge(&chain_stats);
            results.extend(candidates);
        }
    }

    Ok((rank_candidates(results, options.keep), stats))
}

/// One island of stage 1: a full SA run over the tree, with its own RNG stream and temperature.
fn chain(
    library: &Library,
    design: &Design,
    start: &Floorplan,
    cases: &[TestCase],
    options: &Options,
    island: usize,
) -> Outcome {
    let began = Instant::now();
    let mut rng = stream(options.seed, island);
    // Islands 0..3 run cool (greedy descent), the rest progressively hotter (escape artists).
    let slack = 2.0 + 2.0 * (island % 5) as f64;
    let mut stats = Stats::default();
    let mut results: Vec<Candidate> = Vec::new();

    let mut current = start.clone();
    let Some(synthesis) =
        validate::route(library, design, &current.realize(library, design), NEGOTIATION_ROUNDS)
    else {
        return Outcome { candidates: results, best: None, stats };
    };
    let mut current_cost = cost(validate::max_dim(&synthesis), validate::route_cells(&synthesis));
    let mut best: Option<(i64, Floorplan)> = Some((current_cost, current.clone()));

    let mut iterations = 0u64;
    let mut since_best = 0u64;
    let mut fruitless = 0u32;

    while began.elapsed().as_secs_f64() < options.seconds {
        let progress = began.elapsed().as_secs_f64() / options.seconds;
        let temperature = (slack * (1.0 - progress) + 0.5) * 100_000.0;

        let mut candidate = current.clone();
        let kind = mutate_plan(design, &mut candidate, &mut rng);
        stats.tried[kind] += 1;
        if candidate == current {
            continue;
        }
        // Patience measures explored neighbours, not capped halo and same-variant no-ops. Counting
        // the latter lets a tight plan burn through every restart without routing anything.
        iterations += 1;
        since_best += 1;
        let state = candidate.realize(library, design);
        let routed = match validate::route_attempt(library, design, &state, SEARCH_ROUNDS) {
            Ok(synthesis) => Some(synthesis),
            Err(validate::RouteFailure::Congested(congestion)) => {
                stats.congested += 1;
                stats.congested_cells += congestion.contested_cells as u64;
                stats.congested_pressure += congestion.pipe_pressure.values().sum::<usize>() as u64;
                None
            }
            Err(validate::RouteFailure::Rejected) => None,
        };
        if let Some(synthesis) = routed {
            let next_cost = cost(validate::max_dim(&synthesis), validate::route_cells(&synthesis));
            if accept(next_cost - current_cost, temperature, &mut rng) {
                stats.accepted[kind] += 1;
                current = candidate;
                current_cost = next_cost;
                if best.as_ref().is_none_or(|(prior, _)| next_cost < *prior) {
                    best = Some((next_cost, current.clone()));
                    admit(&mut results, library, design, &state, cases, options);
                    since_best = 0;
                    fruitless = 0;
                }
            }
        } else {
            stats.unroutable[kind] += 1;
        }

        // Locked? Patience scales with how long the chain has already run, so a short budget is not
        // cut short and a long one does not spin for minutes on a dead basin.
        if since_best <= (iterations / 4).max(MIN_PATIENCE) {
            continue;
        }
        fruitless += 1;
        since_best = 0;
        if fruitless > RESTARTS {
            // Every restart from the best came back with nothing. More time here buys nothing;
            // stopping frees the core for the other islands and the polish stage.
            stats.stopped_early += 1;
            break;
        }
        // Otherwise jump back to the best this chain has seen and try again from there. SA is free
        // to wander uphill, and after a long stall `current` is usually somewhere much worse than
        // `best` — restarting from the best is what "keep the best" has to mean for the search, not
        // just for the report.
        stats.restarts += 1;
        if let Some((score, plan)) = &best {
            current = plan.clone();
            current_cost = *score;
        }
    }
    Outcome { candidates: results, best, stats }
}

/// One island of stage 2: free-coordinate relief on an already-compact placement.
fn polish(
    library: &Library,
    design: &Design,
    start: &State,
    cases: &[TestCase],
    options: &Options,
    island: usize,
) -> (Vec<Candidate>, Stats) {
    let began = Instant::now();
    let mut rng = stream(options.seed ^ 0xA5A5_A5A5, island);
    let slack = 0.5 + 0.5 * (island % 4) as f64;
    let mut stats = Stats::default();
    let mut results: Vec<Candidate> = Vec::new();

    let mut current = start.clone();
    let Some(synthesis) = validate::route(library, design, &current, NEGOTIATION_ROUNDS) else {
        return (results, stats);
    };
    let mut current_cost = cost(validate::max_dim(&synthesis), validate::route_cells(&synthesis));
    let mut best = (current_cost, current.clone());

    let mut iterations = 0u64;
    let mut since_best = 0u64;
    let mut fruitless = 0u32;

    while began.elapsed().as_secs_f64() < options.polish {
        let progress = began.elapsed().as_secs_f64() / options.polish;
        let temperature = (slack * (1.0 - progress) + 0.25) * 100_000.0;

        iterations += 1;
        since_best += 1;
        let candidate = nudge(design, &current, &mut rng);
        stats.polish_tried += 1;
        match validate::route(library, design, &candidate, SEARCH_ROUNDS) {
            None => stats.polish_unroutable += 1,
            Some(synthesis) => {
                let next_cost =
                    cost(validate::max_dim(&synthesis), validate::route_cells(&synthesis));
                if accept(next_cost - current_cost, temperature, &mut rng) {
                    stats.polish_accepted += 1;
                    current = candidate;
                    current_cost = next_cost;
                    if next_cost < best.0 {
                        best = (next_cost, current.clone());
                        admit(&mut results, library, design, &current, cases, options);
                        since_best = 0;
                        fruitless = 0;
                    }
                }
            }
        }

        // Same lock handling as the tree stage: jump back to the best, and give up once restarting
        // has stopped paying.
        if since_best <= (iterations / 4).max(MIN_PATIENCE) {
            continue;
        }
        fruitless += 1;
        since_best = 0;
        if fruitless > RESTARTS {
            stats.stopped_early += 1;
            break;
        }
        stats.restarts += 1;
        current = best.1.clone();
        current_cost = best.0;
    }
    (results, stats)
}

fn accept(delta: i64, temperature: f64, rng: &mut Rng) -> bool {
    delta <= 0 || rng.unit() < (-(delta as f64) / temperature).exp()
}

/// Judge a routed state and, if it holds up, insert it into the results, best first.
fn admit(
    results: &mut Vec<Candidate>,
    library: &Library,
    design: &Design,
    state: &State,
    cases: &[TestCase],
    options: &Options,
) {
    let Some(synthesis) = validate::route(library, design, state, NEGOTIATION_ROUNDS) else {
        return;
    };
    let Some(candidate) =
        candidate_from_synthesis(design, state, &synthesis, cases, options.max_ticks)
    else {
        return;
    };
    results.retain(|c| {
        c.max_dim != candidate.max_dim
            || cost(c.max_dim, c.route_cells) <= cost(candidate.max_dim, candidate.route_cells)
    });
    if results.iter().any(|c| c.max_dim == candidate.max_dim) {
        return;
    }
    results.push(candidate);
    results.sort_by_key(|c| cost(c.max_dim, c.route_cells));
    results.truncate(options.keep);
}

/// Turn an already fully routed and binding-checked state into an admitted candidate without
/// routing it again. Postprocessors use this to preserve a successful synthesis through judging.
pub(crate) fn candidate_from_synthesis(
    design: &Design,
    state: &State,
    synthesis: &littleman::Synthesis,
    cases: &[TestCase],
    max_ticks: u64,
) -> Option<Candidate> {
    let judged = if cases.is_empty() {
        None
    } else {
        Some(validate::judge_passing(synthesis, cases, max_ticks)?)
    };
    // Bound headroom leads the report: a designer who wrote a `max` wants to know how close the
    // winning layout came to it. Designs without one add no lines and read exactly as before.
    let mut report = validate::bound_report(design, synthesis);
    report.extend(synthesis.report.iter().cloned());
    Some(Candidate {
        state: state.clone(),
        source: synthesis.source.clone(),
        max_dim: validate::max_dim(synthesis),
        route_cells: validate::route_cells(synthesis),
        judged,
        report,
        warnings: synthesis.warnings.clone(),
    })
}

/// Normal final ranking: cost first, one candidate per max-dim, bounded by `keep`.
pub(crate) fn rank_candidates(mut candidates: Vec<Candidate>, keep: usize) -> Vec<Candidate> {
    candidates.sort_by_key(|candidate| {
        (cost(candidate.max_dim, candidate.route_cells), candidate.max_dim)
    });
    let mut kept = Vec::new();
    for candidate in candidates {
        if kept.iter().all(|prior: &Candidate| prior.max_dim != candidate.max_dim) {
            kept.push(candidate);
        }
    }
    kept.truncate(keep);
    kept
}

// ------------------------------------------------------------------------------ stage 1: the tree

/// Perturb the tree in place; returns the move kind, for the accounting.
fn mutate_plan(design: &Design, plan: &mut Floorplan, rng: &mut Rng) -> usize {
    let count = plan.rooms();
    let index = rng.below(count);
    match rng.next() % 100 {
        0..30 => {
            plan.relocate(index, rng);
            0
        }
        30..50 => {
            let other = (index + 1 + rng.below(count.max(2) - 1)) % count;
            plan.swap(index, other);
            1
        }
        50..65 => {
            // Variant substitution is free here: the tree re-packs around the new size, which is
            // what the free-coordinate placer needed a whole greedy re-placement pass to fake.
            let allowed = &design.instances[index].allowed;
            plan.variant[index] = allowed[rng.below(allowed.len())];
            2
        }
        65..90 => {
            // Tighten by preference — taking slack back is the direction that wins, and the
            // routing gate is what stops it going too far.
            let side = rng.below(DELTAS.len());
            let tighten = rng.chance(70);
            plan.adjust_halo(index, side, if tighten { -1 } else { 1 });
            if tighten { 3 } else { 4 }
        }
        _ => {
            let step = if rng.chance(70) { -1 } else { 1 };
            for instance in 0..plan.rooms() {
                for side in 0..DELTAS.len() {
                    plan.adjust_halo(instance, side, step);
                }
            }
            5
        }
    }
}

// ----------------------------------------------------------------------- stage 2: the coordinates

/// The free-coordinate move set: translate, swap origins, pull toward the centroid. No variant
/// substitution — changing a room's size here would need a greedy re-placement to stay legal, and
/// stage 1 already chose the variants against a representation that absorbs the size change.
fn nudge(design: &Design, state: &State, rng: &mut Rng) -> State {
    let mut next = state.clone();
    let count = design.instances.len();
    let index = rng.below(count);
    match rng.next() % 100 {
        0..70 => {
            // Dense placements most often need one cell of relief on one axis. Requiring both
            // coordinates to change made even the smallest translation diagonal, needlessly
            // crossing two sets of room/channel constraints at once. Keep occasional larger and
            // diagonal jumps so polish can still leave a local basin.
            let spread = if rng.chance(85) { 1 } else { 4 };
            if rng.chance(80) {
                let delta = rng.offset(spread);
                if rng.chance(50) {
                    next.pos[index].0 += delta;
                } else {
                    next.pos[index].1 += delta;
                }
            } else {
                next.pos[index].0 += rng.offset(spread);
                next.pos[index].1 += rng.offset(spread);
            }
        }
        70..75 if count > 1 => {
            let other = (index + 1 + rng.below(count - 1)) % count;
            next.pos.swap(index, other);
        }
        _ => {
            let (mut cx, mut cy) = (0i64, 0i64);
            for &(x, y) in &next.pos {
                cx += x as i64;
                cy += y as i64;
            }
            let (cx, cy) = ((cx / count as i64) as i32, (cy / count as i64) as i32);
            let (x, y) = next.pos[index];
            next.pos[index] = (x + (cx - x).signum(), y + (cy - y).signum());
        }
    }
    next
}
