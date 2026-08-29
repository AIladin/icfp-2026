use littleman::model::{Cell, EAST, NORTH, SOUTH, WEST};

use crate::PackError;
use crate::design::Design;
use crate::floorplan::Floorplan;
use crate::library::{Library, Variant, wall_of};

use super::{COMBINATIONS, GAPS, Hint, Probe, combinations, sweep};

pub(super) fn from_hint(
    library: &Library,
    design: &Design,
    hint: &Hint,
    rng: &mut u64,
) -> Result<Floorplan, PackError> {
    let max_y = hint.values().map(|&(_, y)| y).max().unwrap_or(0);
    let mut points = Vec::with_capacity(design.instances.len());
    for instance in &design.instances {
        let Some(&(x, y)) = hint.get(&instance.name) else {
            return Err(PackError(format!("the hint has no position for '{}'", instance.name)));
        };
        points.push((x, max_y - y));
    }
    let base = variants_toward_peers(library, design, &points);
    let cells = rank_cells(&points);
    let flipped: Vec<(usize, usize)> = cells.iter().map(|&(a, b)| (b, a)).collect();
    let combos = combinations(design, &base, COMBINATIONS, *rng);

    let mut probes = Vec::new();
    for (axis, lattice) in [("upright", &cells), ("transposed", &flipped)] {
        for (rank, variants) in combos.iter().enumerate() {
            for (spacing, gap) in GAPS.iter().enumerate() {
                probes.push(Probe {
                    cells: lattice,
                    variants: variants.clone(),
                    gap: *gap,
                    shell: (axis == "transposed") as usize * 2 + rank + spacing,
                    what: format!("hint {axis}, variants #{rank}, gap {gap}"),
                });
            }
        }
    }
    sweep(library, design, probes).map_err(PackError)
}

/// Rank abstract points onto the lattice: distinct xs become columns west to east, distinct ys
/// become rows north to south. Ranking rather than scaling is what keeps the drawing's *topology*
/// while throwing away its arbitrary spacing.
fn rank_cells(points: &[Cell]) -> Vec<(usize, usize)> {
    let rank = |values: Vec<i32>| {
        let mut sorted = values.clone();
        sorted.sort_unstable();
        sorted.dedup();
        values
            .iter()
            .map(|value| sorted.binary_search(value).expect("ranked"))
            .collect::<Vec<usize>>()
    };
    let columns = rank(points.iter().map(|p| p.0).collect());
    let rows = rank(points.iter().map(|p| p.1).collect());
    columns.into_iter().zip(rows).collect()
}

/// The allowed variant whose pin walls best face the hint-space direction of each peer.
fn variants_toward_peers(library: &Library, design: &Design, points: &[Cell]) -> Vec<usize> {
    (0..design.instances.len())
        .map(|index| {
            let instance = &design.instances[index];
            let room = &library.types[&instance.type_name];
            *instance
                .allowed
                .iter()
                .max_by_key(|&&candidate| {
                    let variant = &room.variants[candidate];
                    let mut score = 0i32;
                    for pipe in &design.pipes {
                        let (end, other) = if pipe.from.0 == index {
                            (&pipe.from, pipe.to.0)
                        } else if pipe.to.0 == index {
                            (&pipe.to, pipe.from.0)
                        } else {
                            continue;
                        };
                        let (dx, dy) =
                            (points[other].0 - points[index].0, points[other].1 - points[index].1);
                        let side = wall(variant, &variant.pins[&end.1]);
                        let major = if dx.abs() >= dy.abs() {
                            if dx > 0 { EAST } else { WEST }
                        } else if dy > 0 {
                            SOUTH
                        } else {
                            NORTH
                        };
                        let minor = if dx.abs() >= dy.abs() {
                            if dy > 0 { SOUTH } else { NORTH }
                        } else if dx > 0 {
                            EAST
                        } else {
                            WEST
                        };
                        if side == major {
                            score += 2;
                        } else if side == minor && (dx != 0 && dy != 0) {
                            score += 1;
                        }
                    }
                    score
                })
                .expect("allowed is non-empty")
        })
        .collect()
}

fn wall(variant: &Variant, pin: &crate::library::Pin) -> u8 {
    wall_of(pin, variant.width)
}
