//! Source text to a [`Program`]: every structural rule is checked here, before any tick runs.
//!
//! The contest server reports these failures as `loadError` with no test case run at all, so
//! anything this module lets through and the server rejects costs a submission round-trip. The four
//! documented pipe traps (`docs/vault/heap/Pipes/Pipe drawing traps.md`) are encoded as explicit
//! checks.
//!
//! This is a port of `py/libs/runner/src/littleman/load.py` and must stay in step with it.

use crate::errors::LoadError;
use crate::grid::Grid;
use crate::model::{
    Cell, DELTAS, Display, MAX_DISPLAY, Op, Pipe, Port, Program, Room, RoomKind, arrow,
};

type Result<T> = std::result::Result<T, LoadError>;

/// Parse and validate a `.man` program.
pub fn load_program(source: &str) -> Result<Program> {
    let grid = Grid::parse(source);

    let mut rooms = find_rooms(&grid)?;
    reject_overlaps(&rooms)?;
    classify_io_rooms(&grid, &mut rooms)?;
    let spawns = find_spawns(&grid, &mut rooms)?;

    let pipes = find_pipes(&grid, &rooms)?;
    for (index, pipe) in pipes.iter().enumerate() {
        rooms[pipe.src_room as usize].outgoing.push(index as u32);
        rooms[pipe.dst_room as usize].incoming.push(index as u32);
    }
    let (input_pipe, output_pipe) = check_io_pipes(&rooms, &pipes)?;
    let displays = display_ports(&rooms, &pipes)?;

    let loads = literal_loads(&grid, &rooms)?;
    let (ops, room_of, incoming_sorted) = tables(&grid, &rooms, &pipes, &loads);

    Ok(Program {
        grid,
        rooms,
        pipes,
        displays,
        spawns,
        input_pipe,
        output_pipe,
        ops,
        room_of,
        incoming_sorted,
    })
}

/// Python's `repr()` of a one-character string, so error messages read the same on both sides.
fn repr_char(char: u8) -> String {
    match char {
        b'\'' => "\"'\"".to_string(),
        b'\\' => "'\\\\'".to_string(),
        0x20..=0x7e => format!("'{}'", char as char),
        b'\n' => "'\\n'".to_string(),
        b'\t' => "'\\t'".to_string(),
        b'\r' => "'\\r'".to_string(),
        _ => format!("'\\x{char:02x}'"),
    }
}

// ---------------------------------------------------------------------------------------------
// Rooms
// ---------------------------------------------------------------------------------------------

/// Rectangles of `+`/`-`/`|` (rooms) and of `+`/`=`/`:` (LM-75 displays), outermost first.
///
/// A `+` inside an already-accepted room is skipped: `+` is also the addition instruction, and a
/// run like `+--+` written as code would otherwise look like a nested room.
pub fn find_rooms(grid: &Grid) -> Result<Vec<Room>> {
    let mut rooms: Vec<Room> = Vec::new();
    for y in 0..grid.height() {
        for x in 0..grid.width() {
            if grid.at(x, y) != b'+' {
                continue;
            }
            if rooms.iter().any(|room| room.contains_interior(x, y)) {
                continue;
            }
            let room = match box_from_corner(grid, x, y, b'-', b'|')? {
                Some(room) => Some(room),
                None => box_from_corner(grid, x, y, b'=', b':')?,
            };
            if let Some(room) = room {
                rooms.push(room);
            }
        }
    }
    Ok(rooms)
}

/// The smallest verified rectangle with this cell as its top-left corner, if any.
///
/// The wall glyphs decide what it is: `-`/`|` is a room, `=`/`:` an LM-75 display.
fn box_from_corner(grid: &Grid, x0: i32, y0: i32, across: u8, down: u8) -> Result<Option<Room>> {
    let Some(x1) = run_end(grid, x0, y0, 1, 0, across) else { return Ok(None) };
    let Some(y1) = run_end(grid, x0, y0, 0, 1, down) else { return Ok(None) };
    if x1 - x0 < 2 || y1 - y0 < 2 || grid.at(x1, y1) != b'+' {
        return Ok(None);
    }
    if (x0 + 1..x1).any(|x| grid.at(x, y1) != across) {
        return Ok(None);
    }
    if (y0 + 1..y1).any(|y| grid.at(x1, y) != down) {
        return Ok(None);
    }
    if across == b'-' {
        return Ok(Some(Room::new(x0, y0, x1, y1, RoomKind::Room)));
    }
    if x1 - x0 - 1 > MAX_DISPLAY || y1 - y0 - 1 > MAX_DISPLAY {
        return Err(LoadError(format!(
            "the display at ({x0},{y0}) is {}x{}: the LM-75 interior caps at \
             {MAX_DISPLAY}x{MAX_DISPLAY}",
            x1 - x0 - 1,
            y1 - y0 - 1
        )));
    }
    Ok(Some(Room::new(x0, y0, x1, y1, RoomKind::Display)))
}

/// Walk a wall of `body` glyphs from a corner; return the coordinate of the closing `+`.
fn run_end(grid: &Grid, x: i32, y: i32, dx: i32, dy: i32, body: u8) -> Option<i32> {
    for step in 1..=grid.width().max(grid.height()) {
        let (cx, cy) = (x + dx * step, y + dy * step);
        let char = grid.at(cx, cy);
        if char == b'+' {
            return Some(if dx != 0 { cx } else { cy });
        }
        if char != body {
            return None;
        }
    }
    None
}

fn reject_overlaps(rooms: &[Room]) -> Result<()> {
    for (i, first) in rooms.iter().enumerate() {
        for second in &rooms[i + 1..] {
            let overlap_x = first.x0 <= second.x1 && second.x0 <= first.x1;
            let overlap_y = first.y0 <= second.y1 && second.y0 <= first.y1;
            if overlap_x && overlap_y {
                return Err(LoadError(format!(
                    "rooms overlap: ({},{}) and ({},{})",
                    first.x0, first.y0, second.x0, second.y0
                )));
            }
        }
    }
    Ok(())
}

/// A 3x3 room whose one interior cell is `I` or `O` is the input / output room.
fn classify_io_rooms(grid: &Grid, rooms: &mut [Room]) -> Result<()> {
    let mut seen: Vec<(u8, Cell)> = Vec::new();
    for room in rooms.iter_mut() {
        if room.kind == RoomKind::Display || room.x1 - room.x0 != 2 || room.y1 - room.y0 != 2 {
            continue;
        }
        let char = grid.at(room.x0 + 1, room.y0 + 1);
        if char != b'I' && char != b'O' {
            continue;
        }
        if let Some(&(_, first)) = seen.iter().find(|&&(c, _)| c == char) {
            // `(0, 0) and (5,0)` — the first cell is a Python tuple repr, the second an f-string.
            // Ugly, and copied on purpose so the two runners' messages match character for
            // character.
            return Err(LoadError(format!(
                "more than one {} room: ({}, {}) and ({},{})",
                repr_char(char),
                first.0,
                first.1,
                room.x0,
                room.y0
            )));
        }
        seen.push((char, (room.x0, room.y0)));
        room.kind = if char == b'I' { RoomKind::Input } else { RoomKind::Output };
    }
    Ok(())
}

fn find_spawns(grid: &Grid, rooms: &mut [Room]) -> Result<Vec<(u32, Cell)>> {
    let mut spawns = Vec::new();
    for y in 0..grid.height() {
        for x in 0..grid.width() {
            if grid.at(x, y) != b'@' {
                continue;
            }
            let index = rooms.iter().position(|room| room.contains_interior(x, y));
            let Some(index) = index else {
                return Err(LoadError(format!(
                    "little man at ({x},{y}) is not inside a room \
                     (a malformed room border reads as no room at all)"
                )));
            };
            let room = &mut rooms[index];
            if room.kind == RoomKind::Display {
                return Err(LoadError(format!(
                    "little man at ({x},{y}) is inside the display at ({},{}) — \
                     an LM-75 is driven by pipes, not by a man",
                    room.x0, room.y0
                )));
            }
            if room.spawn.is_some() {
                return Err(LoadError(format!(
                    "room at ({},{}) has multiple '@'s — rooms start with at most one little man",
                    room.x0, room.y0
                )));
            }
            room.spawn = Some((x, y));
            spawns.push((index as u32, (x, y)));
        }
    }
    Ok(spawns)
}

// ---------------------------------------------------------------------------------------------
// Pipes
// ---------------------------------------------------------------------------------------------

pub(crate) fn border_room(rooms: &[Room], x: i32, y: i32) -> Option<u32> {
    rooms.iter().position(|room| room.on_border(x, y)).map(|i| i as u32)
}

pub(crate) fn in_room(rooms: &[Room], x: i32, y: i32) -> bool {
    rooms.iter().any(|room| room.on_border(x, y) || room.contains_interior(x, y))
}

/// Every pipe, walked from the arrowhead that leaves a room border.
///
/// A bend can also sit next to a wall, so a candidate start that turns out to be a cell of another
/// pipe is dropped rather than walked twice. Its **errors** are dropped with it — walking a
/// candidate is speculative, so a malformed one is only fatal if nothing else claims its cell.
/// Without that, tightly packed rooms are rejected: in an 8x8 `triangle` layout the second cell of
/// a 2-cell pipe backs onto the other room's wall, and eagerly raising there reported it as a
/// one-cell pipe. The server accepts these — see `Pipe start scanning may be greedy` in the vault.
/// Every pipe, walked from the arrowhead that leaves a room border — **greedily**.
///
/// One cell can be both "cell #12 of a long pipe" and "a legal start for a new pipe out of the room
/// behind it". The server breaks that tie by claiming cells as it scans, **in reading order**: the
/// first candidate to reach a cell owns it, and a later candidate starting on an owned cell is not a
/// pipe at all. Resolving it the other way — walk everything, then drop whatever turned out to be
/// interior — is order-independent and looks more principled, but it is not what the server does and
/// it cost two submissions. See `find_pipes` in `load.py` for both, and the vault note.
///
/// Walking a candidate stays speculative: a malformed one is only fatal if no pipe ever claims its
/// cell, which is what lets tightly packed rooms load.
fn find_pipes(grid: &Grid, rooms: &[Room]) -> Result<Vec<Pipe>> {
    let mut claimed: std::collections::HashSet<Cell> = std::collections::HashSet::new();
    let mut held: Vec<(Cell, LoadError)> = Vec::new();
    let mut pipes = Vec::new();
    for y in 0..grid.height() {
        for x in 0..grid.width() {
            // Pipes cannot be drawn inside a room: in there these glyphs are turn instructions,
            // and a turn one cell below the top wall would otherwise read as a pipe leaving it.
            let Some(direction) = arrow(grid.at(x, y)) else { continue };
            if in_room(rooms, x, y) || claimed.contains(&(x, y)) {
                continue;
            }
            let (dx, dy) = DELTAS[direction as usize];
            let Some(source) = border_room(rooms, x - dx, y - dy) else { continue };
            match walk_pipe(grid, rooms, (x, y), direction, source) {
                Ok(pipe) => {
                    claimed.extend(pipe.cells.iter().copied());
                    pipes.push(pipe);
                }
                Err(error) => held.push(((x, y), error)),
            }
        }
    }

    for (cell, error) in held {
        if !claimed.contains(&cell) {
            return Err(error);
        }
    }
    Ok(pipes)
}

fn walk_pipe(
    grid: &Grid,
    rooms: &[Room],
    start: Cell,
    mut direction: u8,
    source: u32,
) -> Result<Pipe> {
    let mut cells = vec![start];
    let (mut x, mut y) = start;
    let mut is_arrow = true;
    let limit = (grid.width() as usize * grid.height() as usize) + 2;
    while cells.len() <= limit {
        let (dx, dy) = DELTAS[direction as usize];
        let (nx, ny) = (x + dx, y + dy);
        if let Some(room) = border_room(rooms, nx, ny) {
            if !is_arrow {
                return Err(LoadError(format!(
                    "pipe from ({},{}) runs a body glyph into the wall at ({nx},{ny}) — \
                     end with an arrowhead pointing into the room",
                    start.0, start.1
                )));
            }
            if room == source {
                return Err(LoadError(format!(
                    "pipe from ({},{}) runs back into its own room at ({nx},{ny})",
                    start.0, start.1
                )));
            }
            if cells.len() < 2 {
                return Err(LoadError(format!(
                    "pipe at ({},{}) is one cell long — pipes need at least 2",
                    start.0, start.1
                )));
            }
            return Ok(Pipe { cells, src_room: source, dst_room: room, entry_dir: direction });
        }

        let char = grid.at(nx, ny);
        if let Some(turned) = arrow(char) {
            if turned == (direction + 2) % 4 {
                return Err(LoadError(format!(
                    "arrowhead {} at ({nx},{ny}) points back along the flow of the pipe from \
                     ({},{})",
                    repr_char(char),
                    start.0,
                    start.1
                )));
            }
            direction = turned;
            is_arrow = true;
        } else if char == if dy == 0 { b'-' } else { b'|' } {
            is_arrow = false;
        } else {
            let expected = if dy == 0 { b'-' } else { b'|' };
            return Err(LoadError(format!(
                "pipe from ({},{}) hits {} at ({nx},{ny}): expected an arrowhead or {}",
                start.0,
                start.1,
                repr_char(char),
                repr_char(expected)
            )));
        }
        cells.push((nx, ny));
        (x, y) = (nx, ny);
    }
    Err(LoadError(format!("pipe from ({},{}) never reaches a room", start.0, start.1)))
}

fn check_io_pipes(rooms: &[Room], pipes: &[Pipe]) -> Result<(Option<u32>, Option<u32>)> {
    let mut input_pipe = None;
    let mut output_pipe = None;
    for room in rooms {
        if room.kind == RoomKind::Room || room.kind == RoomKind::Display {
            continue;
        }
        let attached = room.outgoing.len() + room.incoming.len();
        if attached > 1 {
            return Err(LoadError(format!(
                "the {} room at ({},{}) has more than one pipe",
                kind_name(room.kind),
                room.x0,
                room.y0
            )));
        }
        if attached == 0 {
            continue;
        }
        if room.kind == RoomKind::Input && !room.incoming.is_empty() {
            return Err(LoadError(format!(
                "the input room at ({},{}) has a pipe flowing into it",
                room.x0, room.y0
            )));
        }
        if room.kind == RoomKind::Output && !room.outgoing.is_empty() {
            return Err(LoadError(format!(
                "the output room at ({},{}) has a pipe flowing out of it",
                room.x0, room.y0
            )));
        }
        if room.kind == RoomKind::Input {
            input_pipe = Some(room.outgoing[0]);
        } else {
            output_pipe = Some(room.incoming[0]);
        }
    }

    if let Some(index) = input_pipe
        && rooms[pipes[index as usize].dst_room as usize].kind == RoomKind::Output
    {
        return Err(LoadError("the input room's pipe flows straight into the output room".into()));
    }
    Ok((input_pipe, output_pipe))
}

fn kind_name(kind: RoomKind) -> &'static str {
    match kind {
        RoomKind::Room => "room",
        RoomKind::Input => "input",
        RoomKind::Output => "output",
        RoomKind::Display => "display",
    }
}

// ---------------------------------------------------------------------------------------------
// Displays
// ---------------------------------------------------------------------------------------------

/// Which side each pipe lands on, which is the LM-75's opcode.
///
/// > Top: ADDR. Left: DATA. Bottom: SWAP. Attaching multiple pipes to the same side, attaching a
/// > pipe to the right side, or attaching a pipe to the corner is a load error.
/// > — language-reference#The LM-75 Display
fn display_ports(rooms: &[Room], pipes: &[Pipe]) -> Result<Vec<Display>> {
    let mut displays = Vec::new();
    for (index, room) in rooms.iter().enumerate() {
        if room.kind != RoomKind::Display {
            continue;
        }
        if let Some(&out) = room.outgoing.first() {
            let source = pipes[out as usize].source();
            return Err(LoadError(format!(
                "a pipe flows out of the display at ({},{}) from ({},{}) — \
                 an LM-75 only consumes values",
                room.x0, room.y0, source.0, source.1
            )));
        }
        let mut ports: [Option<u32>; 3] = [None; 3];
        for &pipe_index in &room.incoming {
            let (x, y) = pipes[pipe_index as usize].entry();
            let side = display_side(room, x, y)?;
            let slot = side as usize;
            if ports[slot].is_some() {
                return Err(LoadError(format!(
                    "two pipes attach to the {} side of the display at ({},{}); \
                     the second lands at ({x},{y})",
                    side.as_str(),
                    room.x0,
                    room.y0
                )));
            }
            ports[slot] = Some(pipe_index);
        }
        displays.push(Display {
            room: index as u32,
            width: room.x1 - room.x0 - 1,
            height: room.y1 - room.y0 - 1,
            addr: ports[Port::Addr as usize],
            data: ports[Port::Data as usize],
            swap: ports[Port::Swap as usize],
        });
    }
    Ok(displays)
}

fn display_side(room: &Room, x: i32, y: i32) -> Result<Port> {
    if (x == room.x0 || x == room.x1) && (y == room.y0 || y == room.y1) {
        return Err(LoadError(format!(
            "a pipe attaches to the corner ({x},{y}) of the display at ({},{})",
            room.x0, room.y0
        )));
    }
    if y == room.y0 {
        return Ok(Port::Addr);
    }
    if y == room.y1 {
        return Ok(Port::Swap);
    }
    if x == room.x0 {
        return Ok(Port::Data);
    }
    Err(LoadError(format!(
        "a pipe attaches to the right side ({x},{y}) of the display at ({},{}) — \
         that side takes no pipe",
        room.x0, room.y0
    )))
}

// ---------------------------------------------------------------------------------------------
// The op table
// ---------------------------------------------------------------------------------------------

/// Per-cell instructions, room ownership, and `R`/`U` ordering.
///
/// > The distance to a pipe is the Manhattan distance from the operation to the pipe segment that
/// > is attached to the current room ... If multiple pipes are equally close, the pipe whose
/// > segment comes first in reading order wins. — language-reference#Which pipe do I talk to?
///
/// Nearest-pipe resolution is folded straight into [`Op::Send`] / [`Op::Receive`] / [`Op::Query`],
/// so the tick loop never measures a distance. A display has no interior cells a man can stand on,
/// so it contributes nothing here — a 64x64 one would otherwise add 4096 dead cells.
fn tables(
    grid: &Grid,
    rooms: &[Room],
    pipes: &[Pipe],
    loads: &[[Option<i64>; 4]],
) -> (Vec<[Op; 4]>, Vec<u16>, Vec<Vec<u32>>) {
    let cells = (grid.width() * grid.height()) as usize;
    let mut ops = vec![[Op::Nop; 4]; cells];
    let mut room_of = vec![Program::NO_ROOM; cells];
    let mut incoming_sorted = vec![Vec::new(); rooms.len()];

    for (room_index, room) in rooms.iter().enumerate() {
        if room.kind == RoomKind::Display {
            continue;
        }
        let mut incoming = room.incoming.clone();
        incoming.sort_by_key(|&i| {
            let (x, y) = pipes[i as usize].dest();
            (y, x)
        });
        incoming_sorted[room_index] = incoming;

        let sources: Vec<Cell> =
            room.outgoing.iter().map(|&i| pipes[i as usize].source()).collect();
        let dests: Vec<Cell> = room.incoming.iter().map(|&i| pipes[i as usize].dest()).collect();

        for (x, y) in room.interior_cells() {
            let index = (y * grid.width() + x) as usize;
            room_of[index] = room_index as u16;
            let out = nearest((x, y), &room.outgoing, &sources);
            let inp = nearest((x, y), &room.incoming, &dests);
            let char = grid.at(x, y);
            for dir in 0..4 {
                ops[index][dir] = op_for(char, loads[index][dir], out, inp);
            }
        }
    }
    (ops, room_of, incoming_sorted)
}

fn nearest(cell: Cell, indices: &[u32], segments: &[Cell]) -> Option<u32> {
    let (x, y) = cell;
    let best = (0..indices.len()).min_by_key(|&i| {
        let (sx, sy) = segments[i];
        ((sx - x).abs() + (sy - y).abs(), sy, sx)
    })?;
    Some(indices[best])
}

/// One character, resolved for one walk direction.
fn op_for(char: u8, load: Option<i64>, out: Option<u32>, inp: Option<u32>) -> Op {
    // A digit or backtick with no entry for this direction loads nothing: it belongs to a literal
    // along this axis, the backtick does not delimit along it, or the literal is empty.
    if char.is_ascii_digit() || char == b'`' {
        return match load {
            Some(value) => Op::Load(value),
            None => Op::Nop,
        };
    }
    match char {
        b' ' | b'.' | b'@' => Op::Nop,
        b'H' => Op::Halt,
        b'M' => Op::ToB,
        b'W' => Op::Swap,
        b'+' => Op::Add,
        b'-' => Op::Sub,
        b'*' => Op::Mul,
        b'N' => Op::Neg,
        b'/' => Op::Div,
        b'%' => Op::Mod,
        b'&' => Op::And,
        b'|' => Op::Or,
        b'~' => Op::Xor,
        b'{' => Op::Shl,
        b'}' => Op::Shr,
        b'>' => Op::Face(crate::model::EAST),
        b'<' => Op::Face(crate::model::WEST),
        b'^' => Op::Face(crate::model::NORTH),
        b'v' | b'V' => Op::Face(crate::model::SOUTH),
        b'X' => Op::Branch,
        b'Y' => Op::Split,
        b'b' => Op::BpSet,
        b'm' => Op::BpDec,
        b']' => Op::BpShr,
        b'd' => Op::BpCw,
        b'a' => Op::BpCcw,
        b'x' => Op::BpBit,
        b's' => out.map_or(Op::NoPipe(b's'), Op::Send),
        b'S' => {
            if out.is_some() {
                Op::Broadcast
            } else {
                Op::NoPipe(b'S')
            }
        }
        b'r' => inp.map_or(Op::NoPipe(b'r'), Op::Receive),
        b'q' => inp.map_or(Op::NoPipe(b'q'), Op::Query),
        b'R' => {
            if inp.is_some() {
                Op::Select { turn: false }
            } else {
                Op::NoPipe(b'R')
            }
        }
        b'U' => {
            if inp.is_some() {
                Op::Select { turn: true }
            } else {
                Op::NoPipe(b'U')
            }
        }
        other => Op::BadOp(other),
    }
}

/// The message a [`Op::NoPipe`] cell raises when a man actually walks onto it.
pub fn no_pipe_detail(char: u8, x: i32, y: i32) -> String {
    let direction = if char == b's' || char == b'S' { "outgoing" } else { "incoming" };
    format!("{} at ({x},{y}) ran in a room with no {direction} pipe", repr_char(char))
}

pub fn bad_op_detail(char: u8, x: i32, y: i32) -> String {
    format!("{} at ({x},{y}) is not an instruction", repr_char(char))
}

// ---------------------------------------------------------------------------------------------
// Literals
// ---------------------------------------------------------------------------------------------

/// What each digit and backtick loads into A, per walk direction.
///
/// A cell with no entry loads nothing: that is exactly a digit belonging to a literal along the
/// walk axis, a backtick that does not delimit along it, and an empty literal.
fn literal_loads(grid: &Grid, rooms: &[Room]) -> Result<Vec<[Option<i64>; 4]>> {
    let (width, height) = (grid.width(), grid.height());
    let cells = (width * height) as usize;
    let mut loads = vec![[None; 4]; cells];
    let mut matched = vec![false; cells];
    let mut covered_h = vec![false; cells];
    let mut covered_v = vec![false; cells];
    let at = |x: i32, y: i32| (y * width + x) as usize;
    // Which room's interior a cell belongs to; `None` outside every room. Backticks in different
    // rooms never pair — a literal cannot straddle a wall.
    let room_at = |x: i32, y: i32| {
        rooms.iter().position(|r| r.kind != RoomKind::Display && r.contains_interior(x, y))
    };

    for y in 0..height {
        let line: Vec<u8> = (0..width).map(|x| grid.at(x, y)).collect();
        for (lo, hi) in pair_backticks(&line, 0, y, &room_at)? {
            matched[at(lo, y)] = true;
            matched[at(hi, y)] = true;
            for x in lo + 1..hi {
                covered_h[at(x, y)] = true;
            }
            let digits: Vec<u8> = line[(lo + 1) as usize..hi as usize]
                .iter()
                .copied()
                .filter(u8::is_ascii_digit)
                .collect();
            record(&mut loads, &digits, at(hi, y), at(lo, y), (lo, y), 0, 2)?;
        }
    }

    for x in 0..width {
        let column: Vec<u8> = (0..height).map(|y| grid.at(x, y)).collect();
        for (lo, hi) in pair_backticks(&column, 1, x, &room_at)? {
            matched[at(x, lo)] = true;
            matched[at(x, hi)] = true;
            for y in lo + 1..hi {
                covered_v[at(x, y)] = true;
            }
            let digits: Vec<u8> = column[(lo + 1) as usize..hi as usize]
                .iter()
                .copied()
                .filter(u8::is_ascii_digit)
                .collect();
            record(&mut loads, &digits, at(x, hi), at(x, lo), (x, lo), 1, 3)?;
        }
    }

    for y in 0..height {
        for x in 0..width {
            let char = grid.at(x, y);
            let index = at(x, y);
            if char == b'`' && !matched[index] {
                return Err(LoadError(format!("unmatched backtick at ({x},{y})")));
            }
            if !char.is_ascii_digit() {
                continue;
            }
            let value = (char - b'0') as i64;
            if !covered_h[index] {
                loads[index][0] = Some(value);
                loads[index][2] = Some(value);
            }
            if !covered_v[index] {
                loads[index][1] = Some(value);
                loads[index][3] = Some(value);
            }
        }
    }
    Ok(loads)
}

/// Pair backticks along one axis, sequentially. A bad span is a load error, not a skip.
///
/// Confirmed by the server on 2026-07-25: `history-lesson`'s data drum had backticks two rows apart
/// in a column with an `s` between them, every one of them already paired *horizontally*, and the
/// submission came back `expected a digit or a space between backticks, but found 's'`. So the two
/// axes are paired independently, and pairing on one does not excuse the other.
///
/// A backtick left over at the end is not an error here — it may still pair on the other axis, and
/// one that pairs on neither is caught as unmatched.
fn pair_backticks(
    line: &[u8],
    axis: i32,
    other: i32,
    room_at: &dyn Fn(i32, i32) -> Option<usize>,
) -> Result<Vec<(i32, i32)>> {
    let cell = |index: usize| {
        if axis == 0 { (index as i32, other) } else { (other, index as i32) }
    };
    let mut pairs = Vec::new();
    let mut pending: Option<usize> = None;
    for (index, &char) in line.iter().enumerate() {
        if char != b'`' {
            continue;
        }
        let (x, y) = cell(index);
        let room = room_at(x, y);
        let same = pending.is_some_and(|p| {
            let (px, py) = cell(p);
            room.is_some() && room == room_at(px, py)
        });
        if !same {
            pending = Some(index);
            continue;
        }
        let start = pending.unwrap();
        for (offset, &span) in line.iter().enumerate().take(index).skip(start + 1) {
            if !span.is_ascii_digit() && span != b' ' {
                let (sx, sy) = cell(offset);
                return Err(LoadError(format!(
                    "expected a digit or a space between backticks, but found {} at ({sx}, {sy})",
                    repr_char(span)
                )));
            }
        }
        pairs.push((start as i32, index as i32));
        pending = None;
    }
    Ok(pairs)
}
/// A literal loads when the man steps onto its *closing* backtick — which end that is depends on
/// the direction he walks, and the digits read in that order.
fn record(
    loads: &mut [[Option<i64>; 4]],
    digits: &[u8],
    closing_forward: usize,
    closing_backward: usize,
    backward_cell: Cell,
    forward: usize,
    backward: usize,
) -> Result<()> {
    if digits.is_empty() {
        return Ok(());
    }
    let reversed: Vec<u8> = digits.iter().rev().copied().collect();
    let (Some(ahead), Some(behind)) = (parse_i64(digits), parse_i64(&reversed)) else {
        return Err(LoadError(format!(
            "numeric literal '{}' at ({},{}) does not fit in 64 bits read in both directions",
            String::from_utf8_lossy(digits),
            backward_cell.0,
            backward_cell.1
        )));
    };
    loads[closing_forward][forward] = Some(ahead);
    loads[closing_backward][backward] = Some(behind);
    Ok(())
}

/// The digits as an `i64`, or `None` if they overflow. Leading zeros do not count toward the
/// length, so `000...0001` is still 1.
fn parse_i64(digits: &[u8]) -> Option<i64> {
    let mut value: i64 = 0;
    for &digit in digits {
        value = value.checked_mul(10)?.checked_add((digit - b'0') as i64)?;
    }
    Some(value)
}
