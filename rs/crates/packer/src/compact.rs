//! Bounded greedy room-band compaction after annealing and coordinate polish.
//!
//! This postprocessor never replaces its input. It emits fully routed, binding-checked and judged
//! alternatives; final ranking keeps the original winner in the pool alongside them.

use std::time::Instant;

use littleman::TestCase;
use littleman::ephemeral::NEGOTIATION_ROUNDS;

use crate::anneal::{self, Candidate};
use crate::assemble::{self, State};
use crate::design::Design;
use crate::library::Library;
use crate::validate;

const MAX_PASSES: usize = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StopReason {
    NoCuts,
    Exhausted,
    TimeLimit,
    PassLimit,
}

impl StopReason {
    fn label(self) -> &'static str {
        match self {
            Self::NoCuts => "no meaningful band cut",
            Self::Exhausted => "no improving cut",
            Self::TimeLimit => "soft time limit (checked between route/judge calls)",
            Self::PassLimit => "pass limit",
        }
    }
}

pub struct Stats {
    pub cuts_attempted: u64,
    pub routed: u64,
    pub unroutable: u64,
    pub case_valid: u64,
    pub accepted_passes: u64,
    pub before_dim: i32,
    pub after_dim: i32,
    pub elapsed: f64,
    pub stop: StopReason,
}

impl Stats {
    pub fn report(&self) -> String {
        format!(
            "compaction: {} cuts, {} routed / {} unroutable, {} case-valid, {} accepted pass(es), \
             max-dim {} -> {}, {:.2}s, stopped: {}",
            self.cuts_attempted,
            self.routed,
            self.unroutable,
            self.case_valid,
            self.accepted_passes,
            self.before_dim,
            self.after_dim,
            self.elapsed,
            self.stop.label(),
        )
    }
}

/// Greedily compact the rank-0 candidate under a hard wall-clock and pass bound.
///
/// Every returned candidate is an alternative. The caller retains `start` and performs the normal
/// final ranking over the union.
pub fn compact(
    library: &Library,
    design: &Design,
    start: &Candidate,
    cases: &[TestCase],
    max_ticks: u64,
    seconds: f64,
) -> (Vec<Candidate>, Stats) {
    let began = Instant::now();
    let mut current = start.clone();
    let mut alternatives = Vec::new();
    let mut stats = Stats {
        cuts_attempted: 0,
        routed: 0,
        unroutable: 0,
        case_valid: 0,
        accepted_passes: 0,
        before_dim: start.max_dim,
        after_dim: start.max_dim,
        elapsed: 0.0,
        stop: StopReason::PassLimit,
    };

    for _ in 0..MAX_PASSES {
        let moves = band_moves(&current.state);
        if moves.is_empty() {
            stats.stop = StopReason::NoCuts;
            break;
        }
        let mut best: Option<Candidate> = None;
        let mut timed_out = false;
        for state in moves {
            if began.elapsed().as_secs_f64() >= seconds {
                timed_out = true;
                break;
            }
            stats.cuts_attempted += 1;
            if rooms_overlap(library, design, &state) {
                stats.unroutable += 1;
                continue;
            }
            let Some(synthesis) = validate::route(library, design, &state, NEGOTIATION_ROUNDS)
            else {
                stats.unroutable += 1;
                continue;
            };
            stats.routed += 1;
            let next_cost =
                anneal::cost(validate::max_dim(&synthesis), validate::route_cells(&synthesis));
            if next_cost >= candidate_cost(&current) {
                continue;
            }
            if began.elapsed().as_secs_f64() >= seconds {
                timed_out = true;
                break;
            }
            let Some(candidate) =
                anneal::candidate_from_synthesis(design, &state, &synthesis, cases, max_ticks)
            else {
                if began.elapsed().as_secs_f64() >= seconds {
                    timed_out = true;
                    break;
                }
                continue;
            };
            stats.case_valid += 1;
            if best.as_ref().is_none_or(|prior| next_cost < candidate_cost(prior)) {
                best = Some(candidate);
            }
            if began.elapsed().as_secs_f64() >= seconds {
                timed_out = true;
                break;
            }
        }

        // Routing and judging are indivisible, so the wall-clock bound is deliberately soft. A
        // final expensive call may cross it; recompute here so the stop reason remains truthful.
        timed_out |= began.elapsed().as_secs_f64() >= seconds;
        if let Some(candidate) = best {
            current = candidate.clone();
            stats.after_dim = current.max_dim;
            stats.accepted_passes += 1;
            alternatives.push(candidate);
        } else if !timed_out {
            stats.stop = StopReason::Exhausted;
            break;
        }
        if timed_out {
            stats.stop = StopReason::TimeLimit;
            break;
        }
    }
    stats.elapsed = began.elapsed().as_secs_f64();
    (alternatives, stats)
}

fn candidate_cost(candidate: &Candidate) -> i64 {
    anneal::cost(candidate.max_dim, candidate.route_cells)
}

fn band_moves(state: &State) -> Vec<State> {
    let mut moves = Vec::new();
    for axis in 0..2 {
        let mut cuts: Vec<i32> = state
            .pos
            .iter()
            .map(|position| if axis == 0 { position.0 } else { position.1 })
            .collect();
        cuts.sort_unstable();
        cuts.dedup();
        for cut in cuts.into_iter().skip(1) {
            let mut candidate = state.clone();
            for position in &mut candidate.pos {
                let coordinate = if axis == 0 { &mut position.0 } else { &mut position.1 };
                if *coordinate >= cut {
                    *coordinate -= 1;
                }
            }
            moves.push(candidate);
        }
    }
    moves
}

fn rooms_overlap(library: &Library, design: &Design, state: &State) -> bool {
    let boxes: Vec<_> = (0..design.instances.len())
        .map(|index| {
            let variant = assemble::variant_of(library, design, state, index);
            let low = state.pos[index];
            let high = (low.0 + variant.width - 1, low.1 + variant.height - 1);
            (low, high)
        })
        .collect();
    boxes.iter().enumerate().any(|(index, first)| {
        boxes.iter().skip(index + 1).any(|second| {
            first.0.0 <= second.1.0
                && second.0.0 <= first.1.0
                && first.0.1 <= second.1.1
                && second.0.1 <= first.1.1
        })
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn translates_the_far_side_of_each_coordinate_cut() {
        let state = State { pos: vec![(0, 0), (5, 2), (9, 2)], variant: vec![0, 0, 0] };
        let moves = band_moves(&state);
        assert!(moves.iter().any(|state| state.pos == [(0, 0), (4, 2), (8, 2)]));
        assert!(moves.iter().any(|state| state.pos == [(0, 0), (5, 2), (8, 2)]));
    }

    #[test]
    fn one_room_has_no_meaningful_cut() {
        let state = State { pos: vec![(4, 7)], variant: vec![0] };
        assert!(band_moves(&state).is_empty());
    }
}
