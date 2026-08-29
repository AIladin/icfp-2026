//! Placement state -> the grid the router sees: room blocks stamped on a canvas, plus a
//! programmatically built `Marker` per pipe end. No marker letters are ever written into the grid,
//! which is what frees the design from the letter namespace.

use littleman::Marker;
use littleman::grid::Grid;
use littleman::model::{Cell, DELTAS};

use crate::design::Design;
use crate::library::{Library, Variant};

/// One placement candidate: per instance, a box origin and a chosen variant index.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct State {
    pub pos: Vec<Cell>,
    pub variant: Vec<usize>,
}

pub fn variant_of<'a>(
    library: &'a Library,
    design: &Design,
    state: &State,
    index: usize,
) -> &'a Variant {
    let instance = &design.instances[index];
    &library.types[&instance.type_name].variants[state.variant[index]]
}

/// Cheap geometric pre-filter: boxes must not overlap, and every pipe end needs its marker cell
/// and the cell straight out from it clear of every box. The router re-checks all of it — this
/// only exists so obviously-dead placements never pay for a route.
pub fn feasible(library: &Library, design: &Design, state: &State) -> bool {
    let boxes: Vec<(Cell, Cell)> = (0..design.instances.len())
        .map(|i| {
            let v = variant_of(library, design, state, i);
            let (x, y) = state.pos[i];
            ((x, y), (x + v.width - 1, y + v.height - 1))
        })
        .collect();
    for (i, a) in boxes.iter().enumerate() {
        for b in boxes.iter().skip(i + 1) {
            if a.0.0 <= b.1.0 && b.0.0 <= a.1.0 && a.0.1 <= b.1.1 && b.0.1 <= a.1.1 {
                return false;
            }
        }
    }
    let in_any = |cell: Cell| {
        boxes
            .iter()
            .any(|(lo, hi)| lo.0 <= cell.0 && cell.0 <= hi.0 && lo.1 <= cell.1 && cell.1 <= hi.1)
    };
    for pipe in &design.pipes {
        for (end, outgoing) in [(&pipe.from, true), (&pipe.to, false)] {
            let (instance, port) = end;
            let pin = &variant_of(library, design, state, *instance).pins[port];
            let (x, y) = state.pos[*instance];
            let marker = (x + pin.offset.0, y + pin.offset.1);
            let away = if outgoing { pin.direction } else { (pin.direction + 2) % 4 };
            let (dx, dy) = DELTAS[away as usize];
            if in_any(marker) || in_any((marker.0 + dx, marker.1 + dy)) {
                return false;
            }
        }
    }
    true
}

/// The grid text and markers for a state, normalised so everything is at non-negative coordinates.
///
/// The third value is that normalisation: the state-space cell that became `(0, 0)`. Callers that
/// map a state-space coordinate onto the assembled grid **must** subtract it. It is returned rather
/// than assumed to be the origin because it usually is not — a room at `pos` with a pin on its west
/// wall puts a marker at `pos.0 - 1`, and any room can be the leftmost one.
pub fn assemble(library: &Library, design: &Design, state: &State) -> (String, Vec<Marker>, Cell) {
    let mut min: Cell = (i32::MAX, i32::MAX);
    let mut max: Cell = (i32::MIN, i32::MIN);
    let mut markers_raw: Vec<(Cell, String, u32, u8, bool)> = Vec::new();
    for (i, &(x, y)) in state.pos.iter().enumerate() {
        let v = variant_of(library, design, state, i);
        min = (min.0.min(x), min.1.min(y));
        max = (max.0.max(x + v.width - 1), max.1.max(y + v.height - 1));
    }
    for pipe in &design.pipes {
        for (end, outgoing) in [(&pipe.from, true), (&pipe.to, false)] {
            let (instance, port) = end;
            let pin = &variant_of(library, design, state, *instance).pins[port];
            let (x, y) = state.pos[*instance];
            let cell = (x + pin.offset.0, y + pin.offset.1);
            min = (min.0.min(cell.0), min.1.min(cell.1));
            max = (max.0.max(cell.0), max.1.max(cell.1));
            markers_raw.push((cell, pipe.id.clone(), *instance as u32, pin.direction, outgoing));
        }
    }

    let width = (max.0 - min.0 + 1) as usize;
    let height = (max.1 - min.1 + 1) as usize;
    let mut rows = vec![vec![b' '; width]; height];
    for (i, &(x, y)) in state.pos.iter().enumerate() {
        let v = variant_of(library, design, state, i);
        for (dy, row) in v.rows.iter().enumerate() {
            for (dx, &char) in row.iter().enumerate() {
                rows[(y - min.1) as usize + dy][(x - min.0) as usize + dx] = char;
            }
        }
    }
    let text: String = rows
        .iter()
        .map(|row| String::from_utf8_lossy(row).trim_end().to_string())
        .collect::<Vec<_>>()
        .join("\n");

    let markers = markers_raw
        .into_iter()
        .map(|(cell, label, room, direction, outgoing)| Marker {
            cell: (cell.0 - min.0, cell.1 - min.1),
            label,
            room,
            direction,
            outgoing,
            legacy: false,
        })
        .collect();
    (text, markers, min)
}

/// Parse the assembled text back to a `Grid` — what `synthesise_markers` takes.
pub fn as_grid(text: &str) -> Grid {
    Grid::parse(text)
}
