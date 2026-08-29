//! Ephemeral pipes: run a room design before anybody routes or packs it.
//!
//! A port of `py/libs/runner/src/littleman/ephemeral.py`, function for function, and it must stay
//! that way — the two routers have to synthesise **the same pipe graph** for the same design or
//! `lm` and `lmr` disagree about what a handoff means. The retry order is therefore specified
//! rather than shuffled; see [`orderings`] and
//! `docs/vault/heap/The retry order is a specification, not a shuffle.md`.
//!
//! The handover convention is `docs/vault/heap/Room handoff markers.md` — the designer ships one
//! block per room and marks each pipe attachment on the cell **immediately outside** the wall.
//! This module pairs the markers, routes each pair through free space, writes legal pipe glyphs
//! onto the grid, and hands the result to the ordinary [`crate::load_program`]. There is
//! deliberately no second execution path.
//!
//! **A pass proves the LOGIC, not the LAYOUT.**

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};

use crate::errors::LoadError;
use crate::grid::Grid;
use crate::load::{border_room, find_rooms, in_room, load_program};
use crate::model::{Cell, DELTAS, Program, Room, RoomKind};

/// Blank frame added round the design so pipes have somewhere to run.
pub const MARGIN: i32 = 6;
/// How many DFS steps a single route may take before we give up rather than hang.
pub const ROUTE_BUDGET: i32 = 200_000;
/// Rotations of the tight order tried before the shuffles. See [`orderings`].
pub const ROTATIONS: usize = 24;
/// Reproducible shuffles tried after the rotations. See [`orderings`].
pub const SHUFFLES: usize = 24;
/// The seed that makes the shuffles repeat — and makes Python and Rust produce the same ones.
pub const SEED: u64 = 20_260_725;

/// `v` is a pipe arrowhead and `V` is its instruction twin: neither can name a pipe or label one.
/// This is the complete reserved set — every other pipe glyph (`-` `|` `>` `<` `^`) is not a letter.
///
/// `Y` is deliberately **not** here even though it is an instruction: the reserved set is the
/// glyphs the *router writes*, and the router only ever writes pipe glyphs.
pub const RESERVED_LETTERS: [u8; 2] = *b"vV";

const SIDES: [&str; 4] = ["east", "south", "west", "north"];
const ARROW: [u8; 4] = *b">v<^";

pub type Route = Vec<Cell>;

/// The handoff markers cannot be turned into pipes. Mirrors Python's `EphemeralError`.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("{0}")]
pub struct EphemeralError(pub String);

type Result<T> = std::result::Result<T, EphemeralError>;

fn fail<T>(message: impl Into<String>) -> Result<T> {
    Err(EphemeralError(message.into()))
}

/// One pipe end: where it attaches, to which room, and which way the flow goes there.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Marker {
    pub cell: Cell,
    pub label: String,
    pub room: u32,
    /// Flow direction at this cell: away from the wall for a FROM end, into it for a TO end.
    pub direction: u8,
    pub outgoing: bool,
    /// True for the labelled `b`/`B` form, false for a bare letter pair.
    pub legacy: bool,
}

impl Marker {
    /// The character the designer actually typed, so an error points at their own grid.
    fn glyph(&self) -> String {
        if self.legacy {
            return if self.outgoing { "b".into() } else { "B".into() };
        }
        if self.outgoing { self.label.clone() } else { self.label.to_uppercase() }
    }

    fn where_(&self) -> String {
        format!("'{}' at ({},{}) on room {}", self.glyph(), self.cell.0, self.cell.1, self.room)
    }
}

/// One pipe waiting to be routed, with both ends already placed on the padded canvas.
///
/// `exit_cell` is the cell straight out from the FROM marker's wall. The pipe's first step is
/// forced there — an arrowhead leaving a room points away from it — so that cell belongs to this
/// pipe and nothing else may take it. `entry_cell` is the mirror at the TO end: not forced, since a
/// pipe may bend into its last cell from either side, but reserving it too keeps a sprawl open.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Pair {
    pub label: String,
    pub start: Marker,
    pub end: Marker,
    pub head: Cell,
    pub tail: Cell,
    pub exit_cell: Cell,
    pub entry_cell: Cell,
    pub want: usize,
}

/// One pipe failed under one ordering — raw material for a diagnostic, not a user-facing error.
struct Blocked {
    pair: Pair,
    reason: Reason,
    cells: Vec<Cell>,
    detail: usize,
    /// Filled in by the caller, which knows what had already been routed when this one failed.
    owner: HashMap<Cell, String>,
    routed: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Reason {
    Exit,
    Unreachable,
    Short,
    Length,
    Budget,
}

impl Blocked {
    fn new(pair: &Pair, reason: Reason, cells: Vec<Cell>, detail: usize) -> Box<Self> {
        Box::new(Self {
            pair: pair.clone(),
            reason,
            cells,
            detail,
            owner: HashMap::new(),
            routed: Vec::new(),
        })
    }
}

/// A loadable program plus everything the designer has to be told about it.
pub struct Synthesis {
    pub source: String,
    pub program: Program,
    /// Pipe index -> the marker label it was synthesised from.
    pub labels: BTreeMap<usize, String>,
    pub warnings: Vec<String>,
    pub report: Vec<String>,
}

/// Structured residue from negotiated routing that exhausted its rounds. The ordinary synthesis
/// API still returns its established text error; search callers can use this pressure map to
/// distinguish congestion from geometric and no-path failures.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NegotiatedCongestion {
    pub contested_cells: usize,
    /// Pipe label -> number of contested cells occupied by that pipe.
    pub pipe_pressure: BTreeMap<String, usize>,
}

pub enum NegotiatedFailure {
    Congested(NegotiatedCongestion),
    Failed(EphemeralError),
}

/// Turn the handoff markers into real pipes, load the result, and analyse its resolution.
///
/// `min_lengths` maps a label to the minimum number of cells that pipe must have (a delay line
/// needs capacity; everything else needs 2). A route is lengthened to meet it, or the whole thing
/// fails — an ephemeral run with the wrong latency is worse than no run.
pub fn synthesise(source: &str, min_lengths: &BTreeMap<String, usize>) -> Result<Synthesis> {
    let grid = Grid::parse(source);
    let rooms = find_rooms(&grid).map_err(|error: LoadError| EphemeralError(error.0))?;
    reject_reserved(&grid, &rooms)?;
    let (markers, label_cells) = find_markers(&grid, &rooms)?;
    if markers.is_empty() {
        return fail(
            "no handoff markers outside a room wall — this program has nothing to synthesise \
             (run it without --ephemeral-pipes)",
        );
    }
    synthesise_markers(&grid, &markers, &label_cells, min_lengths)
}

/// The router behind [`synthesise`], entered after marker discovery.
///
/// Callers that already know where every pipe attaches (the packer) construct [`Marker`]s
/// directly and skip the grid scan. On this path a `Marker.label` is any string — the letter
/// namespace only constrains markers that have to be *drawn*, so programmatic callers have no
/// pipe-count limit. `min_lengths` is keyed by those same labels.
pub fn synthesise_markers(
    grid: &Grid,
    markers: &[Marker],
    label_cells: &BTreeSet<Cell>,
    min_lengths: &BTreeMap<String, usize>,
) -> Result<Synthesis> {
    synthesise_markers_capped(grid, markers, label_cells, min_lengths, usize::MAX)
}

/// [`synthesise_markers`] with the retry pool capped at `max_orders` pipe orderings per
/// reservation mode. A search loop probing hundreds of placements wants a dead arrangement to
/// fail in milliseconds; the full pool is for arrangements worth fighting for. The marker-driven
/// [`synthesise`] path always runs uncapped — the cap is not part of the cross-language contract.
pub fn synthesise_markers_capped(
    grid: &Grid,
    markers: &[Marker],
    label_cells: &BTreeSet<Cell>,
    min_lengths: &BTreeMap<String, usize>,
    max_orders: usize,
) -> Result<Synthesis> {
    synthesise_markers_with(grid, markers, label_cells, min_lengths, Router::Specified(max_orders))
}

/// [`synthesise_markers`] routed by negotiated congestion instead of the specified retry pool.
/// See [`Router::Negotiated`]; `rounds` bounds the rip-up-and-reroute loop.
pub fn synthesise_markers_negotiated(
    grid: &Grid,
    markers: &[Marker],
    label_cells: &BTreeSet<Cell>,
    min_lengths: &BTreeMap<String, usize>,
    rounds: usize,
) -> Result<Synthesis> {
    synthesise_markers_with(grid, markers, label_cells, min_lengths, Router::Negotiated(rounds))
}

/// Negotiated synthesis with congestion kept as data for placement search. Structural, no-path,
/// lengthening, loading and analysis failures remain ordinary errors: only a complete set of
/// overlapping routes supplies useful pressure information.
pub fn synthesise_markers_negotiated_attempt(
    grid: &Grid,
    markers: &[Marker],
    label_cells: &BTreeSet<Cell>,
    min_lengths: &BTreeMap<String, usize>,
    rounds: usize,
) -> std::result::Result<Synthesis, NegotiatedFailure> {
    let (canvas, free, pairs) = prepare_markers(grid, markers, label_cells, min_lengths)
        .map_err(NegotiatedFailure::Failed)?;
    match route_all_negotiated_attempt(&canvas, &free, &pairs, rounds) {
        Err(error) => Err(NegotiatedFailure::Failed(error)),
        Ok(NegotiatedRoutes::Congested(routes)) => {
            Err(NegotiatedFailure::Congested(congestion_of(&pairs, &routes)))
        }
        Ok(NegotiatedRoutes::Routed(cells, routes)) => {
            finish_synthesis(cells, routes).map_err(NegotiatedFailure::Failed)
        }
    }
}

/// Which search draws the pipes. Everything either side of it — the canvas, the exit-cell rule,
/// the glyphs, the load and the binding analysis — is shared.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Router {
    /// The retry pool of [`orderings`], capped at N orders per reservation mode. **This is the
    /// cross-language contract**: `lm` and `lmr` must draw the same pipes for the same design.
    Specified(usize),
    /// Negotiated congestion (PathFinder), bounded at N rip-up-and-reroute rounds. Deliberately
    /// **not** part of the contract — it exists for `lmp`, which asks "is this placement routable?"
    /// thousands of times and gets no useful answer from permuting pipe order.
    Negotiated(usize),
}

fn synthesise_markers_with(
    grid: &Grid,
    markers: &[Marker],
    label_cells: &BTreeSet<Cell>,
    min_lengths: &BTreeMap<String, usize>,
    router: Router,
) -> Result<Synthesis> {
    let (canvas, free, pairs) = prepare_markers(grid, markers, label_cells, min_lengths)?;
    let (cells, routes) = match router {
        Router::Specified(max_orders) => route_all(&canvas, &free, &pairs, max_orders)?,
        Router::Negotiated(rounds) => route_all_negotiated(&canvas, &free, &pairs, rounds)?,
    };
    finish_synthesis(cells, routes)
}

#[allow(clippy::type_complexity)]
fn prepare_markers(
    grid: &Grid,
    markers: &[Marker],
    label_cells: &BTreeSet<Cell>,
    min_lengths: &BTreeMap<String, usize>,
) -> Result<(Vec<Vec<u8>>, HashSet<Cell>, Vec<Pair>)> {
    let canvas = canvas_of(grid, markers, label_cells);
    let mut free: HashSet<Cell> = HashSet::new();
    for (y, row) in canvas.iter().enumerate() {
        for (x, &char) in row.iter().enumerate() {
            if char == b' ' {
                free.insert((x as i32, y as i32));
            }
        }
    }
    for marker in markers {
        free.remove(&shift(marker.cell));
    }
    let pairs = plan(&group_pairs(markers)?, min_lengths);
    reject_exit_collisions(&pairs, markers, &free)?;
    Ok((canvas, free, pairs))
}

fn finish_synthesis(cells: Vec<Vec<u8>>, routes: BTreeMap<String, Route>) -> Result<Synthesis> {
    let text = trim(&cells);
    let program = load_program(&text).map_err(|error| EphemeralError(error.0))?;
    let labels = match_labels(&program, &routes, &cells);
    let (warnings, report) = analyse(&program, &labels);
    Ok(Synthesis { source: text, program, labels, warnings, report })
}

// ---------------------------------------------------------------------------------------- markers

fn is_marker_letter(char: u8) -> bool {
    char.is_ascii_alphabetic() && !RESERVED_LETTERS.contains(&char)
}

fn is_label(char: u8) -> bool {
    (char.is_ascii_alphanumeric() && !RESERVED_LETTERS.contains(&char))
        && char != b'b'
        && char != b'B'
}

/// Reading order for a cell: rows before columns, which is what Python's `key=lambda c: c[::-1]`
/// does to an `(x, y)` tuple.
fn reading_order(cell: &Cell) -> (i32, i32) {
    (cell.1, cell.0)
}

fn sorted_cells(cells: impl IntoIterator<Item = Cell>) -> Vec<Cell> {
    let mut out: Vec<Cell> = cells.into_iter().collect();
    out.sort_by_key(reading_order);
    out
}

/// Every marker in the design, in either form, plus the cells that were read as labels.
///
/// Inside a room every letter is an instruction, so only cells outside the walls are looked at.
/// The labelled `b`/`B` form is resolved first because it is the one that consumes a neighbour;
/// whatever is left over on a wall is a bare letter pair.
fn find_markers(grid: &Grid, rooms: &[Room]) -> Result<(Vec<Marker>, BTreeSet<Cell>)> {
    let letters = letter_cells(grid, rooms);
    let attached: BTreeSet<Cell> =
        letters.iter().copied().filter(|&cell| touches_border(rooms, cell)).collect();
    let (mut markers, label_cells) = legacy_markers(grid, rooms, &attached)?;
    let taken: BTreeSet<Cell> =
        markers.iter().map(|m| m.cell).chain(label_cells.keys().copied()).collect();
    for cell in sorted_cells(attached.difference(&taken).copied()) {
        markers.push(pair_marker(rooms, grid.at(cell.0, cell.1), cell)?);
    }
    let label_set: BTreeSet<Cell> = label_cells.keys().copied().collect();
    let loose: BTreeSet<Cell> = letters.difference(&attached).copied().collect();
    reject_loose(grid, &loose, &label_set)?;
    Ok((markers, label_set))
}

/// `v` / `V` in a marker position: name the letter and say it is reserved, never misparse it.
fn reject_reserved(grid: &Grid, rooms: &[Room]) -> Result<()> {
    let mut spots = Vec::new();
    for y in 0..grid.height() {
        for x in 0..grid.width() {
            let char = grid.at(x, y);
            if RESERVED_LETTERS.contains(&char)
                && !in_room(rooms, x, y)
                && touches_border(rooms, (x, y))
            {
                spots.push(((x, y), char));
            }
        }
    }
    let Some(&(upper, _)) = spots.iter().find(|&&(_, char)| char == b'V') else { return Ok(()) };
    let twin = spots.iter().find(|&&(_, char)| char == b'v').map(|&(cell, _)| cell);
    let where_ = match twin {
        Some((x, y)) => format!(", and its 'v' twin is at ({x},{y})"),
        None => String::new(),
    };
    fail(format!(
        "the 'V' at ({},{}) sits against a room wall where a marker goes{where_} — but 'v' and 'V' \
         are RESERVED and can never name or label a pipe: 'v' is the arrowhead glyph the router \
         writes into the grid, so a 'v' marker would be indistinguishable from a drawn pipe. \
         Rename that pipe to any other letter; only v/V are taken.",
        upper.0, upper.1
    ))
}

fn letter_cells(grid: &Grid, rooms: &[Room]) -> BTreeSet<Cell> {
    let mut out = BTreeSet::new();
    for y in 0..grid.height() {
        for x in 0..grid.width() {
            if is_marker_letter(grid.at(x, y)) && !in_room(rooms, x, y) {
                out.insert((x, y));
            }
        }
    }
    out
}

fn touches_border(rooms: &[Room], (x, y): Cell) -> bool {
    DELTAS.iter().any(|&(dx, dy)| border_room(rooms, x + dx, y + dy).is_some())
}

/// A bare letter: lowercase starts the pipe, uppercase ends it, the letter names it.
fn pair_marker(rooms: &[Room], char: u8, cell: Cell) -> Result<Marker> {
    let (room, toward_wall) = attachment(rooms, char, cell)?;
    let outgoing = char.is_ascii_lowercase();
    let direction = if outgoing { (toward_wall + 2) % 4 } else { toward_wall };
    Ok(Marker {
        cell,
        label: (char as char).to_ascii_lowercase().to_string(),
        room,
        direction,
        outgoing,
        legacy: false,
    })
}

/// A letter floating outside every room is either a label or a mistake — never ignored.
fn reject_loose(grid: &Grid, loose: &BTreeSet<Cell>, label_cells: &BTreeSet<Cell>) -> Result<()> {
    // The first one in reading order is the one reported, exactly as the Python loop's first
    // iteration raises.
    if let Some((x, y)) = sorted_cells(loose.difference(label_cells).copied()).into_iter().next() {
        return fail(format!(
            "the letter '{}' at ({x},{y}) is outside every room but touches no room wall — a \
             marker sits on the cell immediately outside the border it attaches to, so move it \
             against the wall or delete it",
            grid.at(x, y) as char
        ));
    }
    Ok(())
}

/// Which room the marker touches, and the direction from the marker to that wall.
fn attachment(rooms: &[Room], char: u8, (x, y): Cell) -> Result<(u32, u8)> {
    let mut touching = Vec::new();
    for (direction, &(dx, dy)) in DELTAS.iter().enumerate() {
        if let Some(room) = border_room(rooms, x + dx, y + dy) {
            touching.push((room, direction as u8));
        }
    }
    if touching.is_empty() {
        return fail(format!(
            "the '{}' marker at ({x},{y}) touches no room wall — a marker goes on the cell \
             immediately outside the border it attaches to",
            char as char
        ));
    }
    if touching.len() > 1 {
        let walls: Vec<String> = touching
            .iter()
            .map(|&(room, d)| format!("room {room} to the {}", SIDES[d as usize]))
            .collect();
        return fail(format!(
            "the '{}' marker at ({x},{y}) touches two room walls ({}) — leave a blank cell between \
             the blocks so the attachment is unambiguous",
            char as char,
            walls.join(", ")
        ));
    }
    Ok(touching[0])
}

/// The labelled `b`/`B` form: a marker that has a label next to it, and the label it ate.
///
/// A bare `b` or `B` is left for the letter-pair pass — it is simply the pipe named `b`.
#[allow(clippy::type_complexity)]
fn legacy_markers(
    grid: &Grid,
    rooms: &[Room],
    attached: &BTreeSet<Cell>,
) -> Result<(Vec<Marker>, BTreeMap<Cell, Cell>)> {
    let mut markers = Vec::new();
    let mut label_cells: BTreeMap<Cell, Cell> = BTreeMap::new();
    for cell in sorted_cells(attached.iter().copied()) {
        let char = grid.at(cell.0, cell.1);
        if char != b'b' && char != b'B' {
            continue;
        }
        let Some(label) = label_of(grid, rooms, cell, char, &mut label_cells, attached)? else {
            continue;
        };
        let (room, toward_wall) = attachment(rooms, char, cell)?;
        let direction = if char == b'B' { toward_wall } else { (toward_wall + 2) % 4 };
        markers.push(Marker { cell, label, room, direction, outgoing: char == b'b', legacy: true });
    }
    Ok((markers, label_cells))
}

fn label_of(
    grid: &Grid,
    rooms: &[Room],
    cell: Cell,
    char: u8,
    label_cells: &mut BTreeMap<Cell, Cell>,
    attached: &BTreeSet<Cell>,
) -> Result<Option<String>> {
    let (x, y) = cell;
    let found: Vec<(Cell, u8)> = DELTAS
        .iter()
        .map(|&(dx, dy)| ((x + dx, y + dy), grid.at(x + dx, y + dy)))
        .filter(|&(at, glyph)| is_label(glyph) && !in_room(rooms, at.0, at.1))
        .collect();
    if found.is_empty() {
        reject_reserved_label(grid, rooms, cell, char)?;
        // No label: this is the letter pair `b`/`B`, handled by the caller's second pass.
        return Ok(None);
    }
    if found.len() > 1 {
        let where_: Vec<String> = found
            .iter()
            .map(|&(at, glyph)| format!("'{}' at ({},{})", glyph as char, at.0, at.1))
            .collect();
        return fail(format!(
            "the '{}' marker at ({x},{y}) has {} labels next to it ({}) — a labelled marker takes \
             exactly one; if those are letter-pair markers, leave a blank cell between them",
            char as char,
            found.len(),
            where_.join(", ")
        ));
    }
    let (at, label) = found[0];
    reject_two_readings(grid, cell, at, label, attached)?;
    if let Some(&owner) = label_cells.get(&at) {
        return fail(format!(
            "the label '{}' at ({},{}) sits next to two markers, ({},{}) and ({x},{y}) — give each \
             marker its own label cell",
            label as char, at.0, at.1, owner.0, owner.1
        ));
    }
    label_cells.insert(at, (x, y));
    Ok(Some((label as char).to_string()))
}

/// `bv` is somebody labelling a pipe `v`. Say the letter is reserved instead of ignoring it.
fn reject_reserved_label(grid: &Grid, rooms: &[Room], (x, y): Cell, char: u8) -> Result<()> {
    for &(dx, dy) in DELTAS.iter() {
        let at = (x + dx, y + dy);
        let glyph = grid.at(at.0, at.1);
        if !RESERVED_LETTERS.contains(&glyph) || in_room(rooms, at.0, at.1) {
            continue;
        }
        return fail(format!(
            "the '{}' at ({},{}) is next to the '{}' marker at ({x},{y}), which reads as a label — \
             but 'v' and 'V' are RESERVED and can never name or label a pipe: 'v' is the arrowhead \
             glyph the router writes into the grid. Label that pipe with a digit ({}1) or any \
             other letter.",
            glyph as char, at.0, at.1, char as char, char as char
        ));
    }
    Ok(())
}

/// Refuse a `b`/`B` whose "label" is itself half of a letter pair — that grid reads two ways.
fn reject_two_readings(
    grid: &Grid,
    marker: Cell,
    at: Cell,
    label: u8,
    attached: &BTreeSet<Cell>,
) -> Result<()> {
    if !label.is_ascii_alphabetic() {
        return Ok(());
    }
    let other_case = if label.is_ascii_lowercase() {
        label.to_ascii_uppercase()
    } else {
        label.to_ascii_lowercase()
    };
    let candidates = sorted_cells(attached.iter().copied().filter(|&cell| cell != at));
    let Some(twin) = candidates.into_iter().find(|&c| grid.at(c.0, c.1) == other_case) else {
        return Ok(());
    };
    let char = grid.at(marker.0, marker.1) as char;
    let twin_glyph = grid.at(twin.0, twin.1) as char;
    let swapped =
        if char.is_lowercase() { char.to_ascii_uppercase() } else { char.to_ascii_lowercase() };
    fail(format!(
        "the '{}' at ({},{}) is one cell from the '{char}' marker at ({},{}), and that reads two \
         ways:\n  (1) labelled form — '{}' is the label of that '{char}', making one pipe \
         {char}{}, and the '{twin_glyph}' at ({},{}) is then an unpaired marker;\n  (2) \
         letter-pair form — '{}' is a marker in its own right, pairing with the '{twin_glyph}' at \
         ({},{}), and the '{char}' is then a bare '{}' pipe needing its own '{swapped}'.\n  fix: \
         put a blank cell between the '{}' and the '{char}', or label the '{char}' pipe with a \
         digit ({char}1), which can never be mistaken for a letter pair",
        label as char,
        at.0,
        at.1,
        marker.0,
        marker.1,
        label as char,
        label as char,
        twin.0,
        twin.1,
        label as char,
        twin.0,
        twin.1,
        char.to_ascii_lowercase(),
        label as char,
    ))
}

fn group_pairs(markers: &[Marker]) -> Result<Vec<(String, Marker, Marker)>> {
    let mut grouped: BTreeMap<String, Vec<&Marker>> = BTreeMap::new();
    for marker in markers {
        grouped.entry(marker.label.clone()).or_default().push(marker);
    }
    let mut pairs = Vec::new();
    for (label, group) in grouped {
        if group.iter().any(|m| m.legacy != group[0].legacy) {
            return fail(format!(
                "pipe '{label}' mixes the labelled 'b'/'B' form with the letter-pair form — write \
                 both ends of one pipe the same way"
            ));
        }
        // Name the ends the way the designer wrote them, so the error points at their own glyphs.
        let (start_glyph, end_glyph) = if group[0].legacy {
            ("b".to_string(), "B".to_string())
        } else {
            (label.clone(), label.to_uppercase())
        };
        let starts: Vec<&&Marker> = group.iter().filter(|m| m.outgoing).collect();
        let ends: Vec<&&Marker> = group.iter().filter(|m| !m.outgoing).collect();
        if starts.len() != 1 || ends.len() != 1 {
            return fail(format!(
                "pipe '{label}' has {} '{start_glyph}' and {} '{end_glyph}' marker(s) — a pipe is \
                 exactly one of each",
                starts.len(),
                ends.len()
            ));
        }
        pairs.push((label, (*starts[0]).clone(), (*ends[0]).clone()));
    }
    Ok(pairs)
}

// ---------------------------------------------------------------------------------------- routing

fn shift((x, y): Cell) -> Cell {
    (x + MARGIN, y + MARGIN)
}

fn unshift((x, y): Cell) -> Cell {
    (x - MARGIN, y - MARGIN)
}

/// The design on a blank frame, with the markers and their labels erased.
///
/// They are notation, not program text: the marker cell becomes the pipe's first or last cell, and
/// the label cell becomes free space a pipe may route through.
fn canvas_of(grid: &Grid, markers: &[Marker], label_cells: &BTreeSet<Cell>) -> Vec<Vec<u8>> {
    let width = (grid.width() + 2 * MARGIN) as usize;
    let height = (grid.height() + 2 * MARGIN) as usize;
    let mut cells = vec![vec![b' '; width]; height];
    for y in 0..grid.height() {
        for x in 0..grid.width() {
            cells[(y + MARGIN) as usize][(x + MARGIN) as usize] = grid.at(x, y);
        }
    }
    for cell in markers.iter().map(|m| m.cell).chain(label_cells.iter().copied()) {
        let (x, y) = shift(cell);
        cells[y as usize][x as usize] = b' ';
    }
    cells
}

/// Place both ends of every pipe on the canvas and work out the cells they must leave through.
fn plan(pairs: &[(String, Marker, Marker)], lengths: &BTreeMap<String, usize>) -> Vec<Pair> {
    pairs
        .iter()
        .map(|(label, start, end)| {
            // A letter pipe is named by its lowercase letter; `--pipe-length A=6` means the same.
            let swapped = label.to_uppercase();
            let want = *lengths.get(label).or_else(|| lengths.get(&swapped)).unwrap_or(&2).max(&2);
            let (head, tail) = (shift(start.cell), shift(end.cell));
            let (ox, oy) = DELTAS[start.direction as usize];
            let (ix, iy) = DELTAS[((end.direction + 2) % 4) as usize];
            Pair {
                label: label.clone(),
                start: start.clone(),
                end: end.clone(),
                head,
                tail,
                exit_cell: (head.0 + ox, head.1 + oy),
                entry_cell: (tail.0 + ix, tail.1 + iy),
                want,
            }
        })
        .collect()
}

/// The exit-cell rule, checked before a single pipe is drawn.
fn reject_exit_collisions(pairs: &[Pair], markers: &[Marker], free: &HashSet<Cell>) -> Result<()> {
    let at_cell: HashMap<Cell, &Marker> =
        markers.iter().map(|marker| (shift(marker.cell), marker)).collect();
    for pair in pairs {
        let cell = pair.exit_cell;
        // A two-cell pipe: its exit *is* the far marker, which is exactly right.
        if cell == pair.tail {
            continue;
        }
        let (x, y) = unshift(cell);
        if let Some(other) = at_cell.get(&cell) {
            return fail(format!(
                "the '{}' marker at ({x},{y}) sits one cell out from the '{}' marker at ({},{}), \
                 and that reads two ways:\n  (1) it is a marker of its own, ending or starting \
                 pipe '{}';\n  (2) it is the cell pipe '{}' has to leave through — an arrowhead \
                 leaving a room points straight away from the wall, so that cell is pipe '{}'s own \
                 first segment.\n  It cannot be both. Fix: slide one marker one cell along its \
                 wall, or leave a blank cell between them.",
                other.glyph(),
                pair.start.glyph(),
                pair.start.cell.0,
                pair.start.cell.1,
                other.label,
                pair.label,
                pair.label,
            ));
        }
        if !free.contains(&cell) {
            return fail(format!(
                "pipe '{}' cannot leave its room: the cell straight out from the '{}' marker at \
                 ({},{}) is ({x},{y}), which is not blank. That cell is the pipe's own first \
                 segment and must stay clear — move the marker along its wall, or open up ({x},{y}).",
                pair.label,
                pair.start.glyph(),
                pair.start.cell.0,
                pair.start.cell.1,
            ));
        }
    }
    let mut claimed: HashMap<Cell, &Pair> = HashMap::new();
    for pair in pairs {
        if pair.exit_cell == pair.tail {
            continue;
        }
        match claimed.get(&pair.exit_cell) {
            None => {
                claimed.insert(pair.exit_cell, pair);
            }
            Some(owner) => {
                let (x, y) = unshift(pair.exit_cell);
                return fail(format!(
                    "pipes '{}' and '{}' both have to leave through ({x},{y}) — their FROM markers \
                     face the same cell, and it can only be one pipe's first segment. Move one \
                     marker along its wall.",
                    owner.label, pair.label
                ));
            }
        }
    }
    Ok(())
}

/// Cell -> the one pipe allowed to use it. Exit cells are reserved before anything is routed.
fn reservations(pairs: &[Pair], ends: bool) -> HashMap<Cell, String> {
    let mut reserved: HashMap<Cell, String> = HashMap::new();
    for pair in pairs {
        if pair.exit_cell != pair.tail {
            reserved.insert(pair.exit_cell, pair.label.clone());
        }
    }
    if !ends {
        return reserved;
    }
    let mut shared: HashSet<Cell> = HashSet::new();
    let mut entries: HashMap<Cell, String> = HashMap::new();
    for pair in pairs {
        let cell = pair.entry_cell;
        if cell == pair.head
            || cell == pair.tail
            || reserved.contains_key(&cell)
            || shared.contains(&cell)
        {
            continue;
        }
        match entries.get(&cell) {
            None => {
                entries.insert(cell, pair.label.clone());
            }
            Some(owner) if owner != &pair.label => {
                // Two pipes would both like it: reserving it for either helps neither.
                entries.remove(&cell);
                shared.insert(cell);
            }
            Some(_) => {}
        }
    }
    reserved.extend(entries);
    reserved
}

/// Least freedom first: short before long, straight before bent, then by name for determinism.
fn tightness(pair: &Pair) -> (i32, u8, String) {
    let ((hx, hy), (tx, ty)) = (pair.head, pair.tail);
    let straight = u8::from(hx != tx && hy != ty);
    ((tx - hx).abs() + (ty - hy).abs(), straight, pair.label.clone())
}

/// One step of Marsaglia's xorshift64, shifts 13 / 7 / 17.
///
/// THE ORDER THIS PRODUCES IS PART OF THE CONTRACT. `littleman.ephemeral._xorshift` runs the same
/// generator with the same seed so both routers synthesise the same pipe graph; the fixtures are in
/// `py/libs/runner/tests/test_ephemeral.py` and `tests/ephemeral.rs`.
pub fn xorshift(mut state: u64) -> u64 {
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    state
}

/// `rounds` permutations of `pairs`: Fisher-Yates, `i` from the end down, `j = rand % (i + 1)`.
///
/// One generator drives all the rounds, so round two continues where round one left off — and every
/// round shuffles a *fresh* copy of the input order, not the previous permutation.
fn shuffles(pairs: &[Pair], rounds: usize) -> Vec<Vec<Pair>> {
    let mut state = SEED;
    let mut out = Vec::with_capacity(rounds);
    for _ in 0..rounds {
        let mut order = pairs.to_vec();
        for i in (1..order.len()).rev() {
            state = xorshift(state);
            let j = (state % (i as u64 + 1)) as usize;
            order.swap(i, j);
        }
        out.push(order);
    }
    out
}

/// Orders to try, best guess first. Label order is kept as one of them, never as the only one.
///
/// The first three are the good guesses and are what almost every design routes on. The tail is
/// there for the sprawls that do not: rotations of the tight order (which move exactly one pipe out
/// of everyone else's way, the usual reason a pass fails) and then reproducible shuffles. Order
/// matters only in that the *first* one to succeed wins, so lengthening the tail can turn a failure
/// into a success but can never do the reverse.
pub fn orderings(pairs: &[Pair]) -> Vec<Vec<Pair>> {
    let mut tight = pairs.to_vec();
    tight.sort_by_key(tightness);
    let mut by_label = pairs.to_vec();
    by_label.sort_by(|a, b| a.label.cmp(&b.label));

    let mut orders = vec![tight.clone(), tight.iter().rev().cloned().collect(), by_label];
    for cut in 1..tight.len().min(ROTATIONS + 1) {
        let mut rotated = tight[cut..].to_vec();
        rotated.extend_from_slice(&tight[..cut]);
        orders.push(rotated);
    }
    orders.extend(shuffles(pairs, SHUFFLES));

    let mut seen: HashSet<Vec<String>> = HashSet::new();
    let mut unique = Vec::new();
    for order in orders {
        let key: Vec<String> = order.iter().map(|pair| pair.label.clone()).collect();
        if seen.insert(key) {
            unique.push(order);
        }
    }
    unique
}

/// Route every pipe, retrying under other orders before giving up — and never giving up quietly.
#[allow(clippy::type_complexity)]
fn route_all(
    canvas: &[Vec<u8>],
    free: &HashSet<Cell>,
    pairs: &[Pair],
    max_orders: usize,
) -> Result<(Vec<Vec<u8>>, BTreeMap<String, Route>)> {
    let mut best: Option<(usize, String)> = None;
    for ends in [true, false] {
        let reserved = reservations(pairs, ends);
        for order in orderings(pairs).into_iter().take(max_orders) {
            match attempt(canvas, free, &order, &reserved) {
                Ok(result) => return Ok(result),
                Err(blocked) => {
                    let (message, retry) = diagnose(&blocked, free, pairs);
                    if !retry {
                        return Err(EphemeralError(message));
                    }
                    if best.as_ref().is_none_or(|(count, _)| blocked.routed.len() >= *count) {
                        best = Some((blocked.routed.len(), message));
                    }
                }
            }
        }
    }
    Err(EphemeralError(best.expect("at least one ordering was tried").1))
}

// ----------------------------------------------------------------- negotiated congestion routing

/// How many rip-up-and-reroute rounds [`Router::Negotiated`] runs before it declares a placement
/// unwireable. Convergence is usually 2–5 rounds; the tail is for genuinely tight boards.
pub const NEGOTIATION_ROUNDS: usize = 24;

/// Route every pipe by **negotiated congestion** — the PathFinder algorithm.
///
/// [`route_all`] draws pipes one at a time and freezes each as it lands, so the first pipe into a
/// corridor owns it and the only recourse is trying another *permutation*. With a dozen pipes that
/// is hopeless: the corridor is contested, not mis-ordered.
///
/// Here every pipe takes its cheapest path and is allowed to overlap the others. A cell wanted by
/// more than one pipe gets a *history* penalty, and the whole set is ripped up and rerouted. The
/// pipe with an alternative leaves; the pipe with none stays. It converges in a handful of rounds,
/// costs one Dijkstra per pipe per round, and never backtracks.
enum NegotiatedRoutes {
    Routed(Vec<Vec<u8>>, BTreeMap<String, Route>),
    Congested(Vec<Route>),
}

#[allow(clippy::type_complexity)]
fn route_all_negotiated(
    canvas: &[Vec<u8>],
    free: &HashSet<Cell>,
    pairs: &[Pair],
    rounds: usize,
) -> Result<(Vec<Vec<u8>>, BTreeMap<String, Route>)> {
    match route_all_negotiated_attempt(canvas, free, pairs, rounds)? {
        NegotiatedRoutes::Routed(cells, routes) => Ok((cells, routes)),
        NegotiatedRoutes::Congested(routes) => {
            Err(EphemeralError(congestion_report(pairs, &routes, rounds)))
        }
    }
}

fn route_all_negotiated_attempt(
    canvas: &[Vec<u8>],
    free: &HashSet<Cell>,
    pairs: &[Pair],
    rounds: usize,
) -> Result<NegotiatedRoutes> {
    let width = canvas.first().map_or(0, |row| row.len());
    let height = canvas.len();
    let at = |cell: Cell| cell.1 as usize * width + cell.0 as usize;

    let mut passable = vec![false; width * height];
    for &cell in free {
        passable[at(cell)] = true;
    }
    // The exit cell is a pipe's own first segment — same reservation the specified router makes
    // before it draws anything.
    let mut reserved = vec![usize::MAX; width * height];
    for (index, pair) in pairs.iter().enumerate() {
        if pair.exit_cell != pair.tail {
            reserved[at(pair.exit_cell)] = index;
        }
    }

    // Tightest first, purely for determinism — negotiation, not order, resolves the conflicts.
    let mut order: Vec<usize> = (0..pairs.len()).collect();
    order.sort_by_key(|&index| tightness(&pairs[index]));

    let mut history = vec![0u32; width * height];
    let mut occupancy = vec![0u32; width * height];
    let mut routes: Vec<Route> = vec![Vec::new(); pairs.len()];

    for round in 0..rounds.max(1) {
        // Present cost climbs each round: early rounds explore, late rounds force a decision.
        let present = 2 + 6 * round as u32;
        for &index in &order {
            for cell in std::mem::take(&mut routes[index]) {
                occupancy[at(cell)] -= 1;
            }
            let route = negotiate(
                &pairs[index],
                index,
                width,
                height,
                Costs {
                    passable: &passable,
                    reserved: &reserved,
                    history: &history,
                    occupancy: &occupancy,
                    present,
                },
            )?;
            for &cell in &route {
                occupancy[at(cell)] += 1;
            }
            routes[index] = route;
        }
        let contested: Vec<usize> =
            (0..width * height).filter(|&index| occupancy[index] > 1).collect();
        if contested.is_empty() {
            lengthen(free, pairs, &mut routes)?;
            let (cells, routes) = draw_routes(canvas, pairs, routes);
            return Ok(NegotiatedRoutes::Routed(cells, routes));
        }
        for &index in &contested {
            history[index] += 1;
        }
    }
    Ok(NegotiatedRoutes::Congested(routes))
}

/// Everything the per-pipe search prices a cell by.
struct Costs<'a> {
    passable: &'a [bool],
    reserved: &'a [usize],
    history: &'a [u32],
    occupancy: &'a [u32],
    present: u32,
}

/// Cheapest path for one pipe, allowed to overlap the others at a price. Dijkstra, ties broken by
/// cell index so the same board always yields the same pipe.
fn negotiate(
    pair: &Pair,
    index: usize,
    width: usize,
    height: usize,
    costs: Costs<'_>,
) -> Result<Route> {
    if pair.exit_cell == pair.tail {
        return Ok(vec![pair.head, pair.tail]);
    }
    let at = |cell: Cell| cell.1 as usize * width + cell.0 as usize;
    let (start, goal) = (at(pair.exit_cell), at(pair.tail));

    let mut distance = vec![u64::MAX; width * height];
    let mut came_from = vec![usize::MAX; width * height];
    let mut heap = std::collections::BinaryHeap::new();
    distance[start] = 0;
    heap.push(std::cmp::Reverse((0u64, start)));

    while let Some(std::cmp::Reverse((so_far, here))) = heap.pop() {
        if so_far > distance[here] {
            continue;
        }
        if here == goal {
            break;
        }
        let (x, y) = ((here % width) as i32, (here / width) as i32);
        for &(dx, dy) in DELTAS.iter() {
            let (nx, ny) = (x + dx, y + dy);
            if nx < 0 || ny < 0 || nx as usize >= width || ny as usize >= height {
                continue;
            }
            let there = ny as usize * width + nx as usize;
            let step = if there == goal {
                0
            } else if !costs.passable[there]
                || (costs.reserved[there] != usize::MAX && costs.reserved[there] != index)
            {
                continue;
            } else {
                // Length is the base; history is what a cell learned about being fought over;
                // present is what it costs *right now* to share.
                1 + u64::from(costs.history[there])
                    + u64::from(costs.present) * u64::from(costs.occupancy[there])
            };
            let total = so_far + step;
            if total < distance[there] {
                distance[there] = total;
                came_from[there] = here;
                heap.push(std::cmp::Reverse((total, there)));
            }
        }
    }

    if distance[goal] == u64::MAX {
        let ((sx, sy), (gx, gy)) = (unshift(pair.exit_cell), unshift(pair.end.cell));
        return fail(format!(
            "pipe '{}' has no path at all from its exit cell ({sx},{sy}) to the TO marker at \
             ({gx},{gy}) — the rooms wall it off entirely, so no amount of rerouting helps. Move a \
             room, or pick a variant whose pin is on another wall.",
            pair.label
        ));
    }
    let mut path = vec![goal];
    let mut here = goal;
    while here != start {
        here = came_from[here];
        path.push(here);
    }
    path.reverse();
    let mut route = vec![pair.head];
    route.extend(path.into_iter().map(|cell| ((cell % width) as i32, (cell / width) as i32)));
    Ok(route)
}

/// Negotiation optimises for cost, not length, so a pipe with a `min` may come back too short.
/// Those few get the exact-length search over whatever space the others left — longest want first,
/// because it is the one with the least slack.
fn lengthen(free: &HashSet<Cell>, pairs: &[Pair], routes: &mut [Route]) -> Result<()> {
    let mut short: Vec<usize> =
        (0..pairs.len()).filter(|&index| routes[index].len() < pairs[index].want).collect();
    short.sort_by_key(|&index| std::cmp::Reverse(pairs[index].want));
    for index in short {
        let pair = &pairs[index];
        let mut open = free.clone();
        for (other, route) in routes.iter().enumerate() {
            if other != index {
                for cell in route {
                    open.remove(cell);
                }
            }
        }
        open.insert(pair.tail);
        let rest =
            route_one(&open, pair.exit_cell, pair.tail, pair.want - 1, pair).map_err(|_| {
                EphemeralError(format!(
                    "pipe '{}' must hold at least {} cells and the space the other pipes left will \
                     not take a route that long — spread the rooms out, or shorten the delay.",
                    pair.label, pair.want
                ))
            })?;
        let mut route = vec![pair.head];
        route.extend(rest);
        routes[index] = route;
    }
    Ok(())
}

/// Write every route's glyphs onto its own copy of the canvas.
fn draw_routes(
    canvas: &[Vec<u8>],
    pairs: &[Pair],
    routes: Vec<Route>,
) -> (Vec<Vec<u8>>, BTreeMap<String, Route>) {
    let mut cells: Vec<Vec<u8>> = canvas.to_vec();
    let mut drawn = BTreeMap::new();
    for (pair, route) in pairs.iter().zip(routes) {
        for (cell, glyph) in route.iter().zip(glyphs(&route, pair.end.direction)) {
            cells[cell.1 as usize][cell.0 as usize] = glyph;
        }
        drawn.insert(pair.label.clone(), route);
    }
    (cells, drawn)
}

fn congestion_of(pairs: &[Pair], routes: &[Route]) -> NegotiatedCongestion {
    let mut owners: BTreeMap<Cell, Vec<&str>> = BTreeMap::new();
    for (pair, route) in pairs.iter().zip(routes) {
        for &cell in route {
            owners.entry(cell).or_default().push(&pair.label);
        }
    }
    owners.retain(|_, labels| labels.len() > 1);
    let mut pipe_pressure = BTreeMap::new();
    for labels in owners.values() {
        for &label in labels {
            *pipe_pressure.entry(label.to_string()).or_insert(0) += 1;
        }
    }
    NegotiatedCongestion { contested_cells: owners.len(), pipe_pressure }
}

/// What is still being fought over, named — a placement report, not a routing one.
fn congestion_report(pairs: &[Pair], routes: &[Route], rounds: usize) -> String {
    let mut wanted: BTreeMap<Cell, Vec<&str>> = BTreeMap::new();
    for (pair, route) in pairs.iter().zip(routes) {
        for &cell in route {
            wanted.entry(cell).or_default().push(&pair.label);
        }
    }
    wanted.retain(|_, owners| owners.len() > 1);
    let mut lines = vec![format!(
        "negotiated routing did not converge after {rounds} rounds: {} cell(s) are still wanted by \
         more than one pipe.",
        wanted.len()
    )];
    for (cell, owners) in wanted.iter().take(3) {
        let (x, y) = unshift(*cell);
        lines.push(format!("  ({x},{y}) is contested by {}", owners.join(", ")));
    }
    lines.push(
        "  These rooms cannot be wired where they stand — the pipes need a corridor that does not \
         exist. Move them apart, or choose variants whose pins face a different wall."
            .to_string(),
    );
    lines.join("\n")
}

/// One full pass over the pipes in one order, on its own copy of the canvas.
#[allow(clippy::type_complexity)]
fn attempt(
    canvas: &[Vec<u8>],
    free: &HashSet<Cell>,
    order: &[Pair],
    reserved: &HashMap<Cell, String>,
) -> std::result::Result<(Vec<Vec<u8>>, BTreeMap<String, Route>), Box<Blocked>> {
    let mut blocked_for: HashMap<&str, HashSet<Cell>> = HashMap::new();
    for pair in order {
        blocked_for.entry(&pair.label).or_insert_with(|| {
            reserved
                .iter()
                .filter(|(_, owner)| owner.as_str() != pair.label)
                .map(|(&cell, _)| cell)
                .collect()
        });
    }
    let mut cells: Vec<Vec<u8>> = canvas.to_vec();
    let mut left = free.clone();
    let mut owner: HashMap<Cell, String> = HashMap::new();
    let mut routes: BTreeMap<String, Route> = BTreeMap::new();
    let mut order_seen: Vec<String> = Vec::new();
    for pair in order {
        let banned = &blocked_for[pair.label.as_str()];
        let usable: HashSet<Cell> = left.difference(banned).copied().collect();
        match draw(&mut cells, &usable, pair) {
            Ok(route) => {
                for cell in &route {
                    left.remove(cell);
                    owner.insert(*cell, pair.label.clone());
                }
                routes.insert(pair.label.clone(), route);
                order_seen.push(pair.label.clone());
            }
            Err(mut blocked) => {
                blocked.owner = owner;
                blocked.routed = order_seen;
                return Err(blocked);
            }
        }
    }
    Ok((cells, routes))
}

/// Route one pipe and write its glyphs. Returns the cells, source first.
fn draw(
    cells: &mut [Vec<u8>],
    free: &HashSet<Cell>,
    pair: &Pair,
) -> std::result::Result<Route, Box<Blocked>> {
    let route = if pair.exit_cell == pair.tail {
        vec![pair.head, pair.tail]
    } else if !free.contains(&pair.exit_cell) {
        return Err(Blocked::new(pair, Reason::Exit, vec![pair.exit_cell], 0));
    } else {
        let mut open = free.clone();
        open.insert(pair.tail);
        let rest = route_one(&open, pair.exit_cell, pair.tail, pair.want - 1, pair)?;
        let mut route = vec![pair.head];
        route.extend(rest);
        route
    };
    if route.len() < pair.want {
        return Err(Blocked::new(pair, Reason::Short, route, pair.want));
    }
    for (cell, glyph) in route.iter().zip(glyphs(&route, pair.end.direction)) {
        cells[cell.1 as usize][cell.0 as usize] = glyph;
    }
    Ok(route)
}

/// A simple path of at least `want` cells from `start` to `goal` through `free`.
fn route_one(
    free: &HashSet<Cell>,
    start: Cell,
    goal: Cell,
    want: usize,
    pair: &Pair,
) -> std::result::Result<Route, Box<Blocked>> {
    let dist = distances(free, goal);
    let Some(&from_start) = dist.get(&start) else {
        return Err(Blocked::new(pair, Reason::Unreachable, vec![start, goal], 0));
    };
    let mut target = (from_start as usize + 1).max(want);
    // A grid is bipartite, so every simple path between two cells has the same length parity.
    target += (target - from_start as usize - 1) % 2;
    walk(&dist, start, goal, target, pair)
}

/// Breadth-first distance to `goal` for every reachable free cell.
fn distances(free: &HashSet<Cell>, goal: Cell) -> HashMap<Cell, i32> {
    let mut seen: HashMap<Cell, i32> = HashMap::from([(goal, 0)]);
    let mut frontier = vec![goal];
    while !frontier.is_empty() {
        let mut next = Vec::new();
        for (x, y) in frontier {
            let here = seen[&(x, y)];
            for &(dx, dy) in DELTAS.iter() {
                let cell = (x + dx, y + dy);
                if free.contains(&cell) && !seen.contains_key(&cell) {
                    seen.insert(cell, here + 1);
                    next.push(cell);
                }
            }
        }
        frontier = next;
    }
    seen
}

/// Depth-first search for a simple path of exactly `target` cells, distance-pruned.
fn walk(
    dist: &HashMap<Cell, i32>,
    start: Cell,
    goal: Cell,
    target: usize,
    pair: &Pair,
) -> std::result::Result<Route, Box<Blocked>> {
    let mut path = vec![start];
    let mut seen: HashSet<Cell> = HashSet::from([start]);
    let mut stack: Vec<std::vec::IntoIter<Cell>> =
        vec![options(dist, start, target as i32 - 1, &seen).into_iter()];
    let mut budget = ROUTE_BUDGET;
    while !stack.is_empty() {
        budget -= 1;
        if budget < 0 {
            return Err(Blocked::new(pair, Reason::Budget, vec![start, goal], target));
        }
        let Some(cell) = stack.last_mut().and_then(Iterator::next) else {
            stack.pop();
            if let Some(cell) = path.pop() {
                seen.remove(&cell);
            }
            continue;
        };
        path.push(cell);
        seen.insert(cell);
        if path.len() == target && cell == goal {
            return Ok(path);
        }
        let remaining = target as i32 - path.len() as i32;
        stack.push(options(dist, cell, remaining, &seen).into_iter());
    }
    Err(Blocked::new(pair, Reason::Length, vec![start, goal], target))
}

/// Free neighbours that can still reach the goal in exactly `remaining` more steps.
///
/// `remaining` counts steps left from `cell`, so a neighbour has `remaining - 1` — and since a grid
/// is bipartite, one that cannot spend exactly that many is pruned on parity, not tried.
fn options(
    dist: &HashMap<Cell, i32>,
    (x, y): Cell,
    remaining: i32,
    seen: &HashSet<Cell>,
) -> Vec<Cell> {
    let left = remaining - 1;
    let mut out: Vec<(i32, Cell)> = Vec::new();
    for &(dx, dy) in DELTAS.iter() {
        let step = (x + dx, y + dy);
        let Some(&reach) = dist.get(&step) else { continue };
        if seen.contains(&step) || reach > left || (left - reach) % 2 != 0 {
            continue;
        }
        // Landing on the goal early strands the path: it may only be entered on the last step.
        if reach == 0 && left != 0 {
            continue;
        }
        out.push((reach, step));
    }
    // Closing on the goal first keeps the drawing tidy and the search shallow. Python's `sorted` is
    // stable, so ties keep DELTAS order — `sort_by_key` is stable too.
    out.sort_by_key(|&(reach, _)| reach);
    out.into_iter().map(|(_, cell)| cell).collect()
}

// ------------------------------------------------------------------------------------ diagnostics

/// One shortest path from `start` to `goal`, read straight off a distance map.
fn descend(dist: &HashMap<Cell, i32>, start: Cell, goal: Cell) -> Route {
    let mut path = vec![start];
    let mut cell = start;
    while cell != goal && path.len() <= dist.len() {
        let (x, y) = cell;
        let mut best: Option<(i32, Cell)> = None;
        for &(dx, dy) in DELTAS.iter() {
            let step = (x + dx, y + dy);
            if let Some(&reach) = dist.get(&step)
                && best.is_none_or(|(seen, _)| reach < seen)
            {
                best = Some((reach, step));
            }
        }
        let Some((_, next)) = best else { break };
        cell = next;
        path.push(cell);
    }
    path
}

/// The failure report, and whether another pipe ordering could plausibly rescue it.
///
/// Every coordinate here is in the *design's* own frame, not the padded canvas.
fn diagnose(blocked: &Blocked, free: &HashSet<Cell>, pairs: &[Pair]) -> (String, bool) {
    let pair = &blocked.pair;
    let (mut lines, retry) = explain(blocked, free);
    let header = format!(
        "ephemeral routing failed on pipe '{}': no route from the FROM marker {} to the TO marker {}",
        pair.label,
        pair.start.where_(),
        pair.end.where_()
    );
    if !blocked.routed.is_empty() {
        let order: Vec<String> = blocked.routed.iter().map(|label| format!("'{label}'")).collect();
        lines.push(format!(
            "  {} of {} pipes were routed first, in this order: {}",
            blocked.routed.len(),
            pairs.len(),
            order.join(", ")
        ));
    }
    (std::iter::once(header).chain(lines).collect::<Vec<_>>().join("\n"), retry)
}

fn explain(blocked: &Blocked, free: &HashSet<Cell>) -> (Vec<String>, bool) {
    let pair = &blocked.pair;
    match blocked.reason {
        Reason::Exit => return explain_exit(blocked),
        Reason::Unreachable => return explain_unreachable(blocked, free),
        _ => {}
    }
    let (gx, gy) = unshift(pair.tail);
    let gave_up = if blocked.reason == Reason::Budget {
        format!(" (gave up after {ROUTE_BUDGET} steps)")
    } else {
        String::new()
    };
    (
        vec![
            format!(
                "  it needs a {}-cell route into ({gx},{gy}) and the free space left will not \
                 carry one{gave_up}",
                blocked.detail
            ),
            format!("  asked-for minimum length: {} cells", pair.want),
            "  fix: ask for a different --pipe-length, or open a blank row or column near the \
             receiving room so the pipe has somewhere to fold"
                .to_string(),
        ],
        true,
    )
}

fn explain_exit(blocked: &Blocked) -> (Vec<String>, bool) {
    let pair = &blocked.pair;
    let (x, y) = unshift(pair.exit_cell);
    let mut lines = vec![format!(
        "  the cell straight out from its FROM marker is ({x},{y}); an arrowhead leaving a room \
         points away from the wall, so that cell is pipe '{}'s own first segment",
        pair.label
    )];
    let Some(culprit) = blocked.owner.get(&pair.exit_cell) else {
        lines.push("  it is not free, and no already-routed pipe is in it".to_string());
        lines.push(format!(
            "  fix: clear ({x},{y}), or slide the FROM marker one cell along its wall"
        ));
        return (lines, false);
    };
    lines.push(format!("  pipe '{culprit}' was routed first and is sitting in it"));
    lines.push(format!(
        "  fix: slide one of the two markers one cell along its wall, or leave a blank column for \
         pipe '{culprit}' to detour through"
    ));
    (lines, true)
}

fn explain_unreachable(blocked: &Blocked, free: &HashSet<Cell>) -> (Vec<String>, bool) {
    let (start, goal) = (blocked.cells[0], blocked.cells[1]);
    let (sx, sy) = unshift(start);
    let (gx, gy) = unshift(goal);
    let mut lines = vec![format!(
        "  no free path from its exit cell ({sx},{sy}) to the TO marker at ({gx},{gy})"
    )];
    let mut open = free.clone();
    open.insert(goal);
    let open_dist = distances(&open, goal);
    if !open_dist.contains_key(&start) {
        lines.push(
            "  and none exists on an empty grid either — the two rooms are not connected by blank \
             cells at all"
                .to_string(),
        );
        lines.push("  fix: leave a blank row or column between the blocks".to_string());
        return (lines, false);
    }
    let corridor = descend(&open_dist, start, goal);
    let blockers: BTreeSet<&String> =
        corridor.iter().filter_map(|cell| blocked.owner.get(cell)).collect();
    if blockers.is_empty() {
        lines.push(
            "  the corridor is clear on an empty grid, so what closed it is the exit cells \
             reserved for other pipes"
                .to_string(),
        );
        lines.push(
            "  fix: widen the gap between the blocks, or move the markers whose exits crowd this \
             corridor"
                .to_string(),
        );
        return (lines, true);
    }
    let named: Vec<String> = blockers.iter().map(|label| format!("'{label}'")).collect();
    lines.push(format!(
        "  the only corridor between them is blocked by already-routed pipe(s): {}",
        named.join(", ")
    ));
    lines.push(format!(
        "  fix: widen that corridor by one cell, or move pipe '{}' out of it — the router already \
         retried other pipe orders and none of them cleared it",
        blockers.iter().next().expect("non-empty")
    ));
    (lines, true)
}

/// Pipe glyphs for a route: a body along a straight run, an arrowhead at every bend.
///
/// The first and last cells are always arrowheads — the first so the pipe reads as leaving its
/// room, the last so it points into the receiving one (that terminal arrowhead may itself be the
/// final bend).
fn glyphs(route: &[Cell], entry: u8) -> Vec<u8> {
    let mut directions: Vec<u8> =
        route.windows(2).map(|pair| direction(pair[0], pair[1])).collect();
    directions.push(entry);
    let mut out = vec![ARROW[directions[0] as usize]];
    for index in 1..route.len() {
        let turn = directions[index] != directions[index - 1];
        let last = index == route.len() - 1;
        if turn || last {
            out.push(ARROW[directions[index] as usize]);
            continue;
        }
        out.push(if directions[index] % 2 == 0 { b'-' } else { b'|' });
    }
    out
}

fn direction(here: Cell, there: Cell) -> u8 {
    let step = (there.0 - here.0, there.1 - here.1);
    DELTAS.iter().position(|&delta| delta == step).expect("adjacent cells") as u8
}

fn rows_text(cells: &[Vec<u8>]) -> String {
    cells
        .iter()
        .map(|row| String::from_utf8_lossy(row).trim_end().to_string())
        .collect::<Vec<_>>()
        .join("\n")
}

fn trim(cells: &[Vec<u8>]) -> String {
    let grid = Grid::parse(&rows_text(cells));
    let (x0, y0, x1, y1) = grid.content_box();
    if x1 < x0 {
        return String::new();
    }
    let mut out: Vec<String> = Vec::new();
    for y in y0..=y1 {
        let row = grid.row(y);
        let slice = &row[x0 as usize..(x1 + 1) as usize];
        out.push(String::from_utf8_lossy(slice).trim_end().to_string());
    }
    out.join("\n") + "\n"
}

/// Pipe index -> label, matched on the source cell after the canvas was trimmed.
fn match_labels(
    program: &Program,
    routes: &BTreeMap<String, Route>,
    cells: &[Vec<u8>],
) -> BTreeMap<usize, String> {
    let (x0, y0, _, _) = Grid::parse(&rows_text(cells)).content_box();
    let by_source: HashMap<Cell, &String> =
        routes.iter().map(|(label, route)| ((route[0].0 - x0, route[0].1 - y0), label)).collect();
    let mut labels = BTreeMap::new();
    for (index, pipe) in program.pipes.iter().enumerate() {
        if let Some(label) = by_source.get(&pipe.source()) {
            labels.insert(index, (*label).clone());
        }
    }
    labels
}

// --------------------------------------------------------------------------------------- analysis

/// Per-room resolution report, plus every warning a repack could turn into a wrong answer.
pub fn analyse(program: &Program, labels: &BTreeMap<usize, String>) -> (Vec<String>, Vec<String>) {
    let mut warnings: Vec<String> = Vec::new();
    let mut report: Vec<String> = Vec::new();
    for (index, room) in program.rooms.iter().enumerate() {
        if room.kind == RoomKind::Display {
            continue;
        }
        warnings.extend(side_warnings(program, labels, index, room));
        let lines = room_report(program, labels, index, room, &mut warnings);
        if !lines.is_empty() {
            report.push(room_header(program, labels, index, room));
            report.extend(lines);
        }
    }
    (warnings, report)
}

fn name_of(program: &Program, labels: &BTreeMap<usize, String>, index: usize) -> String {
    let pipe = &program.pipes[index];
    let label = labels.get(&index).map_or("?", String::as_str);
    format!("pipe '{label}' (room {} -> room {})", pipe.src_room, pipe.dst_room)
}

fn side(room: &Room, (x, y): Cell) -> &'static str {
    if y == room.y0 - 1 {
        return "north";
    }
    if y == room.y1 + 1 {
        return "south";
    }
    if x == room.x0 - 1 {
        return "west";
    }
    if x == room.x1 + 1 {
        return "east";
    }
    "off-wall"
}

fn segment(program: &Program, room_index: usize, pipe_index: usize) -> Cell {
    let pipe = &program.pipes[pipe_index];
    if pipe.src_room as usize == room_index { pipe.source() } else { pipe.dest() }
}

fn side_warnings(
    program: &Program,
    labels: &BTreeMap<usize, String>,
    index: usize,
    room: &Room,
) -> Vec<String> {
    let mut sides: Vec<(&'static str, Vec<usize>)> = Vec::new();
    for &pipe_index in room.outgoing.iter().chain(room.incoming.iter()) {
        let pipe_index = pipe_index as usize;
        let key = side(room, segment(program, index, pipe_index));
        match sides.iter_mut().find(|(name, _)| *name == key) {
            Some((_, group)) => group.push(pipe_index),
            None => sides.push((key, vec![pipe_index])),
        }
    }
    let mut warnings = Vec::new();
    for (key, group) in sides {
        if group.len() < 2 {
            continue;
        }
        let named: Vec<String> = group.iter().map(|&i| name_of(program, labels, i)).collect();
        warnings.push(format!(
            "WARN room {index} at ({},{}) has {} pipes on its {key} side: {} — their order along \
             that wall decides who wins a nearest-pipe tie, so the packer has to be told it",
            room.x0,
            room.y0,
            group.len(),
            named.join(", ")
        ));
    }
    warnings
}

fn room_header(
    program: &Program,
    labels: &BTreeMap<usize, String>,
    index: usize,
    room: &Room,
) -> String {
    let kind = match room.kind {
        RoomKind::Room => String::new(),
        RoomKind::Input => " [input]".into(),
        RoomKind::Output => " [output]".into(),
        RoomKind::Display => " [display]".into(),
    };
    let named = |list: &[u32]| -> String {
        let parts: Vec<&str> =
            list.iter().map(|&i| labels.get(&(i as usize)).map_or("?", String::as_str)).collect();
        if parts.is_empty() { "-".to_string() } else { parts.join(", ") }
    };
    let _ = program;
    format!(
        "room {index}{kind} ({},{})-({},{})  out={} in={}",
        room.x0,
        room.y0,
        room.x1,
        room.y1,
        named(&room.outgoing),
        named(&room.incoming)
    )
}

fn room_report(
    program: &Program,
    labels: &BTreeMap<usize, String>,
    index: usize,
    room: &Room,
    warnings: &mut Vec<String>,
) -> Vec<String> {
    let mut lines = Vec::new();
    for cell in room.interior_cells() {
        let char = program.grid.at(cell.0, cell.1);
        if !matches!(char, b's' | b'r' | b'q') {
            continue;
        }
        let outgoing = char == b's';
        let chosen = nearest(program, cell, outgoing);
        let candidates: &[u32] = if outgoing { &room.outgoing } else { &room.incoming };
        let Some(chosen) = chosen else {
            lines.push(format!("  '{}' at ({},{}) -> NO PIPE", char as char, cell.0, cell.1));
            continue;
        };
        let mut ranked: Vec<(i32, usize)> = candidates
            .iter()
            .map(|&i| (walk_distance(program, index, i as usize, cell), i as usize))
            .collect();
        ranked.sort_by_key(|&(distance, i)| {
            let (x, y) = segment(program, index, i);
            (distance, y, x)
        });
        let note = resolution_note(program, labels, index, cell, char, &ranked, warnings);
        lines.push(format!(
            "  '{}' at ({},{}) -> {}{note}",
            char as char,
            cell.0,
            cell.1,
            name_of(program, labels, chosen)
        ));
    }
    lines
}

/// The pipe an `s` / `r` / `q` on `cell` resolves to, read out of the loader's own compiled table.
///
/// Public because the packer's binding gate asks exactly this question per cell. That caller
/// derives the cell from a *candidate* placement, so it can name a cell off the grid entirely —
/// which is not a crash, it is simply a cell no pipe reaches.
pub fn nearest(program: &Program, cell: Cell, outgoing: bool) -> Option<usize> {
    use crate::model::Op;
    let (width, height) = (program.grid.width(), program.grid.height());
    if cell.0 < 0 || cell.1 < 0 || cell.0 >= width || cell.1 >= height {
        return None;
    }
    // Every direction compiles to the same pipe for these cells, so any one of them will do.
    match program.ops[program.index(cell.0, cell.1)][0] {
        Op::Send(pipe) if outgoing => Some(pipe as usize),
        Op::Receive(pipe) | Op::Query(pipe) if !outgoing => Some(pipe as usize),
        _ => None,
    }
}

fn walk_distance(program: &Program, room_index: usize, pipe_index: usize, cell: Cell) -> i32 {
    let (x, y) = segment(program, room_index, pipe_index);
    (x - cell.0).abs() + (y - cell.1).abs()
}

fn resolution_note(
    program: &Program,
    labels: &BTreeMap<usize, String>,
    index: usize,
    cell: Cell,
    char: u8,
    ranked: &[(i32, usize)],
    warnings: &mut Vec<String>,
) -> String {
    if ranked.len() < 2 {
        return "  (the room's only one — unambiguous)".to_string();
    }
    let (best, winner) = ranked[0];
    let (second, runner_up) = ranked[1];
    let runner_label = labels.get(&runner_up).map_or("?", String::as_str);
    if best == second {
        warnings.push(format!(
            "WARN AMBIGUOUS '{}' at ({},{}) in room {index} is {best} cells from {} and {second} \
             from {}; reading order picks '{}' — any repack can flip it",
            char as char,
            cell.0,
            cell.1,
            name_of(program, labels, winner),
            name_of(program, labels, runner_up),
            labels.get(&winner).map_or("?", String::as_str)
        ));
        return format!("  (TIED at {best} with '{runner_label}', broken by reading order)");
    }
    format!("  ({best} cells vs {second} to '{runner_label}' — hold this ordering)")
}

pub const BANNER: &str = "ephemeral pipes: the pipes below were SYNTHESISED from handoff markers. \
A pass proves the LOGIC, not the LAYOUT — real routing moves every pipe segment, and s/r/q take the \
nearest pipe, so a repack can silently re-point a send.
And local proves less than it looks: on 2026-07-25 a 46x46 matmul repack passed 7/7 public and 95/95 \
fuzzed cases under both lm and lmr, and the server still returned 18/20 — it had loaded a different \
pipe graph than either local loader. Ephemeral pipes are a cheap early filter for logic errors, \
never a substitute for `icfp submit --wait`.";

/// The resolved edge list: which room-to-room edge each pipe forms, and where it attaches.
pub fn pipe_graph(program: &Program, labels: &BTreeMap<usize, String>) -> Vec<String> {
    program
        .pipes
        .iter()
        .enumerate()
        .map(|(index, pipe)| {
            let label = labels.get(&index).map_or("?", String::as_str);
            let src = &program.rooms[pipe.src_room as usize];
            let dst = &program.rooms[pipe.dst_room as usize];
            let (sx, sy) = pipe.source();
            let (dx, dy) = pipe.dest();
            format!(
                "pipe '{label}' #{index}: room {}{} ({sx}, {sy}) [{}] -> room {}{} ({dx}, {dy}) \
                 [{}], {} cell(s)",
                pipe.src_room,
                kind_of(src),
                side(src, pipe.source()),
                pipe.dst_room,
                kind_of(dst),
                side(dst, pipe.dest()),
                pipe.cells.len()
            )
        })
        .collect()
}

fn kind_of(room: &Room) -> &'static str {
    match room.kind {
        RoomKind::Room => "",
        RoomKind::Input => "[input]",
        RoomKind::Output => "[output]",
        RoomKind::Display => "[display]",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pair(label: &str) -> Pair {
        let marker = Marker {
            cell: (0, 0),
            label: label.into(),
            room: 0,
            direction: 0,
            outgoing: true,
            legacy: false,
        };
        Pair {
            label: label.into(),
            start: marker.clone(),
            end: marker,
            head: (0, 0),
            tail: (2, 0),
            exit_cell: (1, 0),
            entry_cell: (1, 0),
            want: 2,
        }
    }

    #[test]
    fn negotiated_congestion_counts_cells_and_pressure_by_label() {
        let pairs = [pair("a"), pair("b"), pair("c")];
        let routes = [vec![(0, 0), (1, 0)], vec![(0, 1), (1, 0)], vec![(1, 0), (2, 0)]];
        let congestion = congestion_of(&pairs, &routes);
        assert_eq!(congestion.contested_cells, 1);
        assert_eq!(
            congestion.pipe_pressure,
            BTreeMap::from([("a".into(), 1), ("b".into(), 1), ("c".into(), 1)])
        );
    }
}
