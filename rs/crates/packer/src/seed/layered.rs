use littleman::model::{EAST, SOUTH};

use crate::PackError;
use crate::design::Design;
use crate::floorplan::Floorplan;
use crate::library::{Library, Pin, Variant, wall_of};

use super::{COMBINATIONS, GAPS, Lattice, PLANS, Probe, combinations, sweep};

pub(super) fn layered_seed(
    library: &Library,
    design: &Design,
    rng: &mut u64,
) -> Result<Floorplan, PackError> {
    let layers = layers_of(library, design);
    if std::env::var("LMP_DUMP_SEED").is_ok() {
        for (depth, layer) in layers.iter().enumerate() {
            let names: Vec<&str> =
                layer.iter().map(|&i| design.instances[i].name.as_str()).collect();
            eprintln!("  layer {depth}: {}", names.join(", "));
        }
    }
    let mut plans: Vec<(i32, Vec<u8>)> = direction_plans(layers.len())
        .into_iter()
        .map(|directions| (variants_for(library, design, &layers, &directions).1, directions))
        .collect();
    plans.sort_by(|a, b| b.0.cmp(&a.0).then_with(|| a.1.cmp(&b.1)));

    // One lattice per direction plan, plus a last-resort diagonal: one room per lattice row *and*
    // column, so every room has a channel running the full width and height of the design past it.
    let order: Vec<usize> = layers.iter().flatten().copied().collect();
    let mut diagonal = vec![(0, 0); design.instances.len()];
    for (step, &instance) in order.iter().enumerate() {
        diagonal[instance] = (step, step);
    }

    let mut lattices: Vec<Lattice> = plans
        .iter()
        .take(PLANS)
        .enumerate()
        .map(|(rank, (score, directions))| Lattice {
            what: format!("plan {directions:?} (pin agreement {score})"),
            cells: lattice_for(&layers, directions, design.instances.len()),
            base: variants_for(library, design, &layers, directions).0,
            rank,
        })
        .collect();
    lattices.push(Lattice {
        what: "diagonal (one room per row and column)".to_string(),
        cells: diagonal,
        base: variants_for(library, design, &layers, &plans[0].1).0,
        rank: PLANS,
    });

    let mut probes = Vec::new();
    for lattice in &lattices {
        let combos = combinations(design, &lattice.base, COMBINATIONS, *rng);
        for (index, variants) in combos.iter().enumerate() {
            for (spacing, gap) in GAPS.iter().enumerate() {
                probes.push(Probe {
                    cells: &lattice.cells,
                    variants: variants.clone(),
                    gap: *gap,
                    shell: lattice.rank + index + spacing,
                    what: format!("{}, variants #{index}, gap {gap}", lattice.what),
                });
            }
        }
    }
    sweep(library, design, probes).map_err(|last| {
        PackError(format!(
            "no seed arrangement routed — the netlist may not be single-layer routable with these \
             variants. Last failure:\n{last}"
        ))
    })
}

/// Every combination of per-boundary growth directions. A design is rarely a single axis.
fn direction_plans(layers: usize) -> Vec<Vec<u8>> {
    let boundaries = layers.saturating_sub(1);
    let bits = boundaries.min(8);
    (0..1usize << bits)
        .map(|mask| {
            (0..boundaries)
                .map(|b| if mask >> b.min(bits - 1) & 1 == 1 { EAST } else { SOUTH })
                .collect()
        })
        .collect()
}

/// Lay the layers out as a staircase on the lattice.
fn lattice_for(layers: &[Vec<usize>], directions: &[u8], count: usize) -> Vec<(usize, usize)> {
    let mut cells = vec![(0, 0); count];
    let (mut column, mut row) = (0usize, 0usize);
    for (depth, layer) in layers.iter().enumerate() {
        let grow = *directions.get(depth).or(directions.last()).unwrap_or(&SOUTH);
        for (across, &instance) in layer.iter().enumerate() {
            cells[instance] =
                if grow == SOUTH { (column + across, row) } else { (column, row + across) };
        }
        if grow == SOUTH {
            row += 1;
        } else {
            column += 1;
        }
    }
    cells
}

/// Longest-path layering: an instance sits one layer below its deepest predecessor.
fn layers_of(library: &Library, design: &Design) -> Vec<Vec<usize>> {
    let count = design.instances.len();
    let mut depth = vec![0usize; count];
    for _ in 0..count {
        let mut changed = false;
        for pipe in &design.pipes {
            let want = depth[pipe.from.0] + 1;
            if depth[pipe.to.0] < want && want < count {
                depth[pipe.to.0] = want;
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }
    for (index, instance) in design.instances.iter().enumerate() {
        if library.types[&instance.type_name].variants.iter().any(|v| v.is_input) {
            depth[index] = 0;
        }
    }
    let deepest = depth.iter().copied().max().unwrap_or(0);
    let mut layers: Vec<Vec<usize>> = vec![Vec::new(); deepest + 1];
    for (index, &d) in depth.iter().enumerate() {
        layers[d].push(index);
    }
    layers.retain(|layer| !layer.is_empty());
    for _ in 0..3 {
        barycenter_pass(design, &mut layers, false);
        barycenter_pass(design, &mut layers, true);
    }
    layers
}

fn barycenter_pass(design: &Design, layers: &mut [Vec<usize>], upward: bool) {
    let count = layers.len();
    let range: Vec<usize> =
        if upward { (0..count.saturating_sub(1)).rev().collect() } else { (1..count).collect() };
    for at in range {
        let reference = if upward { at + 1 } else { at - 1 };
        let position = |instance: usize| -> Option<f64> {
            layers[reference].iter().position(|&i| i == instance).map(|p| p as f64)
        };
        let mut keyed: Vec<(f64, usize)> = layers[at]
            .iter()
            .map(|&instance| {
                let mut total = 0.0;
                let mut links = 0.0;
                for pipe in &design.pipes {
                    let other = if pipe.from.0 == instance {
                        pipe.to.0
                    } else if pipe.to.0 == instance {
                        pipe.from.0
                    } else {
                        continue;
                    };
                    if let Some(p) = position(other) {
                        total += p;
                        links += 1.0;
                    }
                }
                let key = if links > 0.0 {
                    total / links
                } else {
                    layers[at].iter().position(|&i| i == instance).unwrap_or(0) as f64
                };
                (key, instance)
            })
            .collect();
        keyed.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
        layers[at] = keyed.into_iter().map(|(_, instance)| instance).collect();
    }
}

fn wall(variant: &Variant, pin: &Pin) -> u8 {
    wall_of(pin, variant.width)
}

/// Choose variants by pin agreement for a direction plan, and return the total score.
fn variants_for(
    library: &Library,
    design: &Design,
    layers: &[Vec<usize>],
    directions: &[u8],
) -> (Vec<usize>, i32) {
    let layer_of = |instance: usize| layers.iter().position(|l| l.contains(&instance)).unwrap_or(0);
    let mut total = 0;
    let chosen = (0..design.instances.len())
        .map(|index| {
            let instance = &design.instances[index];
            let room = &library.types[&instance.type_name];
            let my_layer = layer_of(index);
            let score_of = |candidate: usize| {
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
                    let peer_layer = layer_of(other);
                    let side = wall(variant, &variant.pins[&end.1]);
                    let boundary = my_layer.min(peer_layer).min(directions.len().max(1) - 1);
                    let grow = directions.get(boundary).copied().unwrap_or(SOUTH);
                    match peer_layer.cmp(&my_layer) {
                        std::cmp::Ordering::Greater if side == grow => score += 1,
                        std::cmp::Ordering::Less if side == (grow + 2) % 4 => score += 1,
                        std::cmp::Ordering::Equal
                            if side == (grow + 1) % 4 || side == (grow + 3) % 4 =>
                        {
                            score += 1
                        }
                        _ => {}
                    }
                }
                score
            };
            let best = *instance
                .allowed
                .iter()
                .max_by_key(|&&candidate| score_of(candidate))
                .expect("allowed is non-empty");
            total += score_of(best);
            best
        })
        .collect();
    (chosen, total)
}
