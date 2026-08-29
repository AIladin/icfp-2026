//! The generated starting floorplan. A `.eman.toml` carries no layout, so the seed builds one from
//! pin geometry rather than hope:
//!
//! 1. **Layers** — either the planar hint's certified crossing-free drawing, ranked onto a lattice,
//!    or longest-path layering over the pipe DAG with barycenter ordering inside each layer
//!    (Sugiyama's crossing reduction), which is the shape these dataflow programs actually have.
//! 2. **A direction per layer boundary** — each layer hands off either SOUTH or EAST, and a layer
//!    spreads across the direction it hands off in. Every combination is enumerated and scored by
//!    how many pins end up facing the peer they are wired to; the best two dozen are routed.
//! 3. **Variant choice** — per plan, the allowed variant whose pin walls best agree with it.
//! 4. **A B\*-tree over the lattice**, then a greedy strip of every cell of slack that routes
//!    without.
//!
//! Step 2 is not optional and one global axis will not do. On the sudoku pilot `split` fans south
//! into a row of checkers while `decode` fans east into a column of cells, because that is where
//! their pins are; force either boundary the other way and the pipes have to cross, which
//! single-layer routing cannot do at *any* spacing. A design's shape is a fact about its rooms.

mod hint;
mod layered;

use littleman::ephemeral::xorshift;
use rayon::prelude::*;

use crate::PackError;
use crate::design::Design;
use crate::floorplan::Floorplan;
use crate::library::Library;
use crate::validate;

/// Negotiation rounds while probing seed halos. The full pool, not the search's early cut-off: a
/// seed is tried a couple of dozen times, not a million, and giving up on it early is how you
/// conclude a routable design is unroutable.
pub const PROBE_ROUNDS: usize = 10;

/// Rounds while stripping slack. Lower than a probe on purpose: this runs hundreds of times, and
/// giving up early here only means keeping a cell of padding we could have had.
const STRIP_ROUNDS: usize = 8;

/// Extra spacing added to every lattice row and column, tried in this order. Tight first, because
/// when a design does route tightly straight away the search starts from a much better place; the
/// loose ones are the safety net, and the greedy strip takes most of the slack back anyway.
const GAPS: [i32; 3] = [2, 6, 12];

/// How many direction plans to actually route, best pin-agreement first. Generous, because pin
/// agreement ranks the *boundaries that carry pins* and leaves the rest tied — the plans below the
/// top few differ only in the boundaries the score could not distinguish, which is precisely where
/// routing still can.
const PLANS: usize = 24;

/// Variant combinations sampled per lattice — or the whole space, when it is smaller than this.
const COMBINATIONS: usize = 16;

/// Total arrangements routed before the seeder gives up. They run across every core and the sweep
/// stops at the first that routes, so this is the *worst* case — a design that seeds easily pays
/// for a handful of them.
const SEED_PROBES: usize = 512;

/// Instance name -> abstract grid point from `py/eman_hint.py` — a certified crossing-free planar
/// drawing of the room graph (NetworkX Chrobak–Payne). Y grows upward there (math orientation);
/// this module flips it.
pub type Hint = std::collections::BTreeMap<String, (i32, i32)>;

pub fn seed(
    library: &Library,
    design: &Design,
    rng_seed: u64,
    hint: Option<&Hint>,
) -> Result<Floorplan, PackError> {
    let mut rng = rng_seed | 1;
    if let Some(hint) = hint {
        match hint::from_hint(library, design, hint, &mut rng) {
            Ok(plan) => return Ok(plan),
            Err(error) => eprintln!(
                "WARN the planar hint did not produce a routable arrangement ({error}); falling \
                 back to layered seeding"
            ),
        }
    }
    layered::layered_seed(library, design, &mut rng)
}

/// One arrangement of rooms on the (column, row) lattice, before variants and spacing are chosen.
struct Lattice {
    what: String,
    cells: Vec<(usize, usize)>,
    /// The pin-agreement variant pick for this lattice — combination #0 of the sample.
    base: Vec<usize>,
    /// Position in the pin-agreement ranking; feeds the probe's shell.
    rank: usize,
}

/// One thing to route: a lattice, a variant per instance, and a spacing.
struct Probe<'a> {
    cells: &'a [(usize, usize)],
    variants: Vec<usize>,
    gap: i32,
    /// How far from the best-guess corner this probe is — the sum of its plan, combination and gap
    /// ranks. Probes are tried in shells of increasing distance.
    shell: usize,
    what: String,
}

/// Route a batch of probes in parallel and keep the best that survives, or say why none did.
///
/// The old seeder walked one lattice at a time, sequentially, trying the greedy variant choice and
/// then a single random perturbation of it. That samples a handful of points around one corner of
/// a space that is `prod(variants per instance)` big — 3888 on the sudoku pilot — and it fails
/// *hard*: a design whose only routable variant combination was never drawn is reported as
/// unroutable, and the annealer that would have found it never runs. Adding variants to the library
/// makes that strictly worse, because the space grows and the sample count does not.
///
/// So: sample across the whole space, evaluate in parallel, and walk outward in shells so the
/// best guess is still tried first and a design that seeds easily still seeds in a second.
///
/// Set `LMP_DUMP_SEED=<prefix>` to write every arrangement tried as a grid, and to log each probe
/// with what went wrong. A seeder that cannot route is close to impossible to reason about from the
/// error text alone — the arrangement itself shows immediately whether the rooms are laid out the
/// way the pins want, and reading one of these is what found the coordinate-space bug in the
/// binding gate.
fn sweep(
    library: &Library,
    design: &Design,
    mut probes: Vec<Probe<'_>>,
) -> Result<Floorplan, String> {
    probes.sort_by_key(|probe| probe.shell);
    probes.truncate(SEED_PROBES);
    let dump = std::env::var("LMP_DUMP_SEED").ok();

    // `find_map_first` is the whole scheduler: it runs the probes across every core, returns the
    // *earliest in order* that routes rather than whichever thread happened to finish first — so
    // the result does not depend on timing — and stops the rest once it has one. Shell order is
    // already best-guess-first, so an easy design still seeds in a fraction of a second and only a
    // hard one pays for the breadth.
    let winner = probes.par_iter().enumerate().find_map_first(|(index, probe)| {
        let plan = Floorplan::grid(library, design, probe.cells, probe.variants.clone(), probe.gap);
        let state = plan.realize(library, design);
        if let Some(path) = &dump {
            let (text, _, _) = crate::assemble::assemble(library, design, &state);
            let _ = std::fs::write(format!("{path}.{index:04}.txt"), text);
        }
        validate::route(library, design, &state, PROBE_ROUNDS).map(|_| (index, plan))
    });

    if let Some((index, plan)) = winner {
        eprintln!("seed: {} routed ({} arrangements offered)", probes[index].what, probes.len());
        return Ok(strip(library, design, plan));
    }

    // Nothing routed. Diagnose the loosest arrangement we tried: if a design will not wire up with
    // every room held apart, no amount of packing was ever going to save it, and that is the
    // message worth printing.
    let Some(widest) = probes.iter().max_by_key(|probe| probe.gap) else {
        return Err("no arrangement was feasible".into());
    };
    let plan = Floorplan::grid(library, design, widest.cells, widest.variants.clone(), widest.gap);
    let state = plan.realize(library, design);
    Err(match validate::binding_error(library, design, &state, PROBE_ROUNDS) {
        Some(error) => format!("{} (the widest tried): {error}", widest.what),
        None => format!("{} failed for no reason the analyser could name", widest.what),
    })
}

/// Variant combinations to try, best guess first, then a spread across the whole space.
///
/// `base` is the pin-agreement pick. After that comes a Latin sweep — combination `k` gives
/// instance `i` its `(k + i)`-th allowed variant — which guarantees that within `max variants`
/// samples *every variant of every instance* has been tried at least once, unlike random draws.
/// Beyond that it is seeded pseudo-random over the product space. If the whole space fits in the
/// budget it is enumerated instead, and "sampled" becomes "exhaustive".
fn combinations(design: &Design, base: &[usize], count: usize, seed: u64) -> Vec<Vec<usize>> {
    let allowed: Vec<&Vec<usize>> = design.instances.iter().map(|i| &i.allowed).collect();
    let space: u64 = allowed
        .iter()
        .try_fold(1u64, |total, set| total.checked_mul(set.len() as u64))
        .unwrap_or(u64::MAX);

    let mut out = vec![base.to_vec()];
    if space <= count as u64 {
        // Small enough to be exhaustive: mixed-radix count over the product space.
        for index in 0..space {
            let combination = indexed_combination(&allowed, index);
            if !out.contains(&combination) {
                out.push(combination);
            }
        }
    } else {
        let widest = allowed.iter().map(|set| set.len()).max().unwrap_or(1);
        for step in 0..widest {
            let combination = allowed
                .iter()
                .enumerate()
                .map(|(index, set)| set[(step + index) % set.len()])
                .collect();
            if !out.contains(&combination) {
                out.push(combination);
            }
        }
        let mut state = seed | 1;
        for _ in 0..count.saturating_mul(32) {
            if out.len() >= count {
                break;
            }
            let combination = allowed
                .iter()
                .map(|set| {
                    state = xorshift(state);
                    set[(state % set.len() as u64) as usize]
                })
                .collect();
            if !out.contains(&combination) {
                out.push(combination);
            }
        }
        // A projected PRNG stream is not a proof of coverage. Fill any duplicate-heavy remainder
        // by deterministic mixed-radix enumeration; `space > count` guarantees enough tuples.
        let mut index = 0;
        while out.len() < count {
            let combination = indexed_combination(&allowed, index);
            if !out.contains(&combination) {
                out.push(combination);
            }
            index += 1;
        }
    }
    out.truncate(count);
    out
}

fn indexed_combination(allowed: &[&Vec<usize>], mut index: u64) -> Vec<usize> {
    allowed
        .iter()
        .map(|set| {
            let pick = set[(index % set.len() as u64) as usize];
            index /= set.len() as u64;
            pick
        })
        .collect()
}

/// Greedy descent on slack: strip every halo the design routes without. Pure tightening is a
/// direction, not a search, and one route call per step beats waiting for the annealer to find the
/// same cells by accident — the lattice hands over hundreds of cells of padding it only needed in
/// order to line the rows up, and a diagonal seed hands over thousands.
///
/// Coarse to fine, because linear descent from a spread-out seed would be thousands of route
/// calls: each pass takes `step` cells at a time, and the last pass is the one-cell polish.
fn strip(library: &Library, design: &Design, mut plan: Floorplan) -> Floorplan {
    let routes = |plan: &Floorplan| {
        let state = plan.realize(library, design);
        validate::route(library, design, &state, STRIP_ROUNDS).is_some()
    };
    let before = plan.slack();
    for step in [16, 8, 4, 2, 1] {
        // Whole-design passes first: they take cells off everywhere for one route call.
        loop {
            let mut tighter = plan.clone();
            if tighter.shrink_all(step) == 0 || !routes(&tighter) {
                break;
            }
            plan = tighter;
        }
        // Then per room, per side, for the slack that is not uniform.
        for instance in 0..plan.rooms() {
            for side in 0..4 {
                while plan.halo[instance][side] >= step {
                    let mut tighter = plan.clone();
                    tighter.halo[instance][side] -= step;
                    if !routes(&tighter) {
                        break;
                    }
                    plan = tighter;
                }
            }
        }
    }
    eprintln!("seed: stripped slack {before} -> {}", plan.slack());
    plan
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::design::Instance;

    fn design(allowed: &[Vec<usize>]) -> Design {
        Design {
            problem: None,
            instances: allowed
                .iter()
                .enumerate()
                .map(|(index, variants)| Instance {
                    name: format!("room{index}"),
                    type_name: "unused".into(),
                    allowed: variants.clone(),
                })
                .collect(),
            pipes: Vec::new(),
        }
    }

    #[test]
    fn small_variant_space_is_really_exhaustive_when_base_is_not_first() {
        let design = design(&[vec![0, 1], vec![0, 1]]);
        let combinations = combinations(&design, &[1, 1], 4, 1);
        assert_eq!(combinations.len(), 4);
        for expected in [vec![0, 0], vec![1, 0], vec![0, 1], vec![1, 1]] {
            assert!(combinations.contains(&expected), "missing {expected:?}");
        }
    }

    #[test]
    fn sampled_variant_combinations_are_unique() {
        let design = design(&[vec![0, 1, 2], vec![0, 1, 2], vec![0, 1, 2]]);
        let combinations = combinations(&design, &[2, 2, 2], 16, 7);
        assert_eq!(combinations.len(), 16);
        for (index, combination) in combinations.iter().enumerate() {
            assert!(!combinations[..index].contains(combination));
        }
    }
}
