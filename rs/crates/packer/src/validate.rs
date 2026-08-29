//! The gates a candidate must pass, in cost order: route + load (done by `synthesise_markers`),
//! the binding check, and — for results — the full case run.

use std::collections::BTreeMap;

use littleman::model::Cell;
use littleman::{
    NegotiatedCongestion, NegotiatedFailure, Synthesis, TestCase, ephemeral, run_case,
    synthesise_markers_negotiated, synthesise_markers_negotiated_attempt,
};

use crate::assemble::{self, State};
use crate::design::{Design, PipeSpec};
use crate::library::Library;

/// Route the state and load the result, negotiating congestion for at most `rounds` rip-up passes.
/// `None` means "not a program" — unroutable, unloadable, or mis-bound — and the caller treats it
/// as an infeasible move, not an error.
///
/// The packer deliberately does **not** use the specified retry pool: permuting pipe order cannot
/// clear a contested corridor, which is the failure a from-scratch placement hits constantly.
pub enum RouteFailure {
    Congested(NegotiatedCongestion),
    Rejected,
}

pub fn route(
    library: &Library,
    design: &Design,
    state: &State,
    rounds: usize,
) -> Option<Synthesis> {
    route_attempt(library, design, state, rounds).ok()
}

/// Route while preserving negotiated congestion for search diagnostics. Geometric, no-path,
/// length and binding failures have no useful overlapping-route pressure and remain rejections.
pub fn route_attempt(
    library: &Library,
    design: &Design,
    state: &State,
    rounds: usize,
) -> Result<Synthesis, RouteFailure> {
    if !assemble::feasible(library, design, state) {
        return Err(RouteFailure::Rejected);
    }
    let (text, markers, origin) = assemble::assemble(library, design, state);
    let min_lengths: BTreeMap<String, usize> =
        design.pipes.iter().map(|pipe| (pipe.id.clone(), pipe.min)).collect();
    let grid = assemble::as_grid(&text);
    let synthesis = match synthesise_markers_negotiated_attempt(
        &grid,
        &markers,
        &std::collections::BTreeSet::new(),
        &min_lengths,
        rounds,
    ) {
        Ok(synthesis) => synthesis,
        Err(NegotiatedFailure::Congested(congestion)) => {
            return Err(RouteFailure::Congested(congestion));
        }
        Err(NegotiatedFailure::Failed(_)) => return Err(RouteFailure::Rejected),
    };
    if length_error(design, &synthesis).is_some()
        || binding_check(library, design, state, &synthesis, &markers, origin).is_err()
    {
        return Err(RouteFailure::Rejected);
    }
    Ok(synthesis)
}

/// Why the binding gate rejected a routed candidate — surfaced for the final report, swallowed
/// during the search.
pub fn binding_error(
    library: &Library,
    design: &Design,
    state: &State,
    rounds: usize,
) -> Option<String> {
    let (text, markers, origin) = assemble::assemble(library, design, state);
    let min_lengths: BTreeMap<String, usize> =
        design.pipes.iter().map(|pipe| (pipe.id.clone(), pipe.min)).collect();
    let grid = assemble::as_grid(&text);
    match synthesise_markers_negotiated(
        &grid,
        &markers,
        &std::collections::BTreeSet::new(),
        &min_lengths,
        rounds,
    ) {
        Err(error) => Some(error.to_string()),
        Ok(synthesis) => length_error(design, &synthesis)
            .or_else(|| binding_check(library, design, state, &synthesis, &markers, origin).err()),
    }
}

/// The upper bound `min_lengths` cannot express. The router lengthens a route to reach `min` and
/// fails loudly when it cannot, but nothing stops it routing *long* — so a design that needs
/// `len(a) <= len(b) + gap` (the `snake` display applies ADDR before DATA within a tick) gets a
/// silently wrong program. `route` treats a violation as an infeasible candidate, the same as an
/// unroutable one, so the search keeps looking for a placement that fits.
///
/// Length is counted in routed pipe cells — the same unit as `min` and as `--pipe-length`.
pub fn length_error(design: &Design, synthesis: &Synthesis) -> Option<String> {
    if design.pipes.iter().all(|pipe| pipe.max.is_none()) {
        return None;
    }
    over_long(&design.pipes, &routed_lengths(synthesis))
}

/// One line per max-bounded pipe: what it routed to and how much headroom is left. Empty for a
/// design that declares no bound, so an existing design's report is unchanged.
pub fn bound_report(design: &Design, synthesis: &Synthesis) -> Vec<String> {
    let routed = routed_lengths(synthesis);
    design
        .pipes
        .iter()
        .filter_map(|pipe| {
            let (max, &length) = (pipe.max?, routed.get(pipe.id.as_str())?);
            Some(format!(
                "bound: pipe '{}' routed to {length} cells (min {}, max {max}, {} to spare)",
                pipe.id,
                pipe.min,
                max.saturating_sub(length)
            ))
        })
        .collect()
}

fn routed_lengths(synthesis: &Synthesis) -> BTreeMap<&str, usize> {
    synthesis
        .labels
        .iter()
        .map(|(index, label)| (label.as_str(), synthesis.program.pipes[*index].cells.len()))
        .collect()
}

/// The comparison itself, over plain lengths so it can be tested without routing anything.
fn over_long(pipes: &[PipeSpec], routed: &BTreeMap<&str, usize>) -> Option<String> {
    for pipe in pipes {
        let (Some(max), Some(&length)) = (pipe.max, routed.get(pipe.id.as_str())) else {
            continue;
        };
        if length > max {
            return Some(format!(
                "pipe '{}' routed to {length} cells, above its declared max = {max} (min = {}) — \
                 the placement forces a detour this design cannot absorb. Move the two rooms \
                 closer, or raise the bound if the timing really does allow it.",
                pipe.id, pipe.min
            ));
        }
    }
    None
}

/// Every `s`/`r`/`q` must resolve — in the *loaded* program, by the loader's own table — to the
/// pipe its variant's intent names. This is the structural mitigation for the class of failure
/// where a layout change silently re-points a send (`docs/vault/heap/The server can build a
/// different pipe graph.md`): a candidate that disagrees with the intent is not a worse candidate,
/// it is a different program, and it dies here.
fn binding_check(
    library: &Library,
    design: &Design,
    state: &State,
    synthesis: &Synthesis,
    markers: &[littleman::Marker],
    origin: Cell,
) -> Result<(), String> {
    let program = &synthesis.program;
    let by_label: BTreeMap<&str, &PipeSpec> =
        design.pipes.iter().map(|pipe| (pipe.id.as_str(), pipe)).collect();

    // Two shifts separate a state-space cell from a program cell, and both matter. `origin` is the
    // normalisation `assemble` applied; `shift` is any further trim the loader did. Dropping the
    // first is a silent, layout-dependent bug: it is zero exactly when the leftmost, topmost thing
    // in the design is a pin marker, and wrong otherwise.
    let (first_index, first_label) =
        synthesis.labels.iter().next().ok_or("no pipes were loaded at all")?;
    let from_marker = markers
        .iter()
        .find(|m| m.outgoing && &m.label == first_label)
        .ok_or("loaded a pipe with no matching FROM marker")?;
    let source = program.pipes[*first_index].source();
    let shift: Cell = (source.0 - from_marker.cell.0, source.1 - from_marker.cell.1);

    let pipe_of_label: BTreeMap<&str, usize> =
        synthesis.labels.iter().map(|(index, label)| (label.as_str(), *index)).collect();

    for (instance_index, instance) in design.instances.iter().enumerate() {
        let variant = assemble::variant_of(library, design, state, instance_index);
        let (ox, oy) = state.pos[instance_index];
        for (cell, char, port) in &variant.intent {
            let at = (ox - origin.0 + cell.0 + shift.0, oy - origin.1 + cell.1 + shift.1);
            let outgoing = *char == b's';
            let end = (instance_index, port.clone());
            let expected = design
                .pipes
                .iter()
                .find(|pipe| if outgoing { pipe.from == end } else { pipe.to == end })
                .ok_or_else(|| {
                    format!("instance '{}' port '{port}' is not wired", instance.name)
                })?;
            let expected_index = *pipe_of_label.get(expected.id.as_str()).ok_or_else(|| {
                format!("pipe '{}' was routed but not matched in the loaded program", expected.id)
            })?;
            let loaded = ephemeral::nearest(program, at, outgoing);
            if loaded != Some(expected_index) {
                let got = loaded
                    .and_then(|index| synthesis.labels.get(&index).cloned())
                    .unwrap_or_else(|| "NO PIPE".to_string());
                return Err(format!(
                    "binding mismatch in instance '{}' ({}/{}): '{}' at ({},{}) must reach port \
                     '{port}' = pipe '{}', but the loaded program binds it to '{got}'",
                    instance.name,
                    instance.type_name,
                    variant.name,
                    *char as char,
                    cell.0,
                    cell.1,
                    expected.id,
                ));
            }
            let _ = by_label;
        }
    }
    // A tie today is a re-point tomorrow: refuse candidates the analyser flags as ambiguous.
    if let Some(warning) = synthesis.warnings.iter().find(|w| w.contains("AMBIGUOUS")) {
        return Err(format!("nearest-pipe tie: {warning}"));
    }
    Ok(())
}

#[derive(Clone)]
pub struct Judged {
    pub passed: usize,
    pub total: usize,
    pub avg_ticks: f64,
}

/// Run every case. The packer's cost never sees ticks; this exists so a result can be *reported*
/// with them, and so a candidate that breaks behaviour never becomes a result.
pub fn judge(synthesis: &Synthesis, cases: &[TestCase], max_ticks: u64) -> Judged {
    let mut passed = 0;
    let mut ticks = 0u64;
    for case in cases {
        let result = run_case(&synthesis.program, case, max_ticks);
        if result.passed {
            passed += 1;
        }
        ticks += result.ticks;
    }
    let avg_ticks = if cases.is_empty() { 0.0 } else { ticks as f64 / cases.len() as f64 };
    Judged { passed, total: cases.len(), avg_ticks }
}

/// Admission-only judge: stop at the first failed case, otherwise return exactly the same summary
/// as [`judge`]. A rejected search candidate has no useful average tick count.
pub fn judge_passing(synthesis: &Synthesis, cases: &[TestCase], max_ticks: u64) -> Option<Judged> {
    let mut ticks = 0u64;
    for case in cases {
        let result = run_case(&synthesis.program, case, max_ticks);
        if !result.passed {
            return None;
        }
        ticks += result.ticks;
    }
    let total = cases.len();
    let avg_ticks = if total == 0 { 0.0 } else { ticks as f64 / total as f64 };
    Some(Judged { passed: total, total, avg_ticks })
}

/// `max(width, height)` of the routed program — THE cost, per the locked plan.
pub fn max_dim(synthesis: &Synthesis) -> i32 {
    let (width, height) = synthesis.program.grid.footprint();
    width.max(height)
}

/// Total routed pipe cells: not part of the cost, only a deterministic tiebreak so the annealer
/// has a gradient inside a max-dim plateau (and shorter pipes are cheaper ticks, for free).
pub fn route_cells(synthesis: &Synthesis) -> usize {
    synthesis.program.pipes.iter().map(|pipe| pipe.cells.len()).sum()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pipe(id: &str, min: usize, max: Option<usize>) -> PipeSpec {
        PipeSpec { id: id.into(), from: (0, "out".into()), to: (1, "feed".into()), min, max }
    }

    fn routed(pairs: &[(&'static str, usize)]) -> BTreeMap<&'static str, usize> {
        pairs.iter().copied().collect()
    }

    #[test]
    fn unbounded_pipes_never_complain() {
        let pipes = [pipe("a>b", 2, None)];
        assert_eq!(over_long(&pipes, &routed(&[("a>b", 400)])), None);
    }

    #[test]
    fn a_route_at_the_bound_is_fine() {
        let pipes = [pipe("a>b", 4, Some(9))];
        assert_eq!(over_long(&pipes, &routed(&[("a>b", 9)])), None);
    }

    #[test]
    fn an_over_long_route_names_the_pipe_and_both_lengths() {
        let pipes = [pipe("head.addr>disp.addr", 4, Some(88))];
        let error = over_long(&pipes, &routed(&[("head.addr>disp.addr", 144)]))
            .expect("144 cells is over the bound");
        assert!(error.contains("head.addr>disp.addr"), "{error}");
        assert!(error.contains("144"), "names the length achieved: {error}");
        assert!(error.contains("max = 88"), "names the bound: {error}");
    }

    /// A pipe the router did not label is the binding gate's problem, not the length gate's.
    #[test]
    fn an_unrouted_pipe_is_not_a_length_failure() {
        let pipes = [pipe("a>b", 2, Some(3))];
        assert_eq!(over_long(&pipes, &routed(&[])), None);
    }
}
