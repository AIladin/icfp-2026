//! Program topology: rooms, pipes, and the tables the tick loop reads instead of doing geometry.
//!
//! Nothing here is mutated by a run — a [`Program`] is loaded once and can be run against many test
//! cases. All mutable state lives in [`crate::machine::Machine`].

use serde::Serialize;

use crate::grid::Grid;

// Directions are indices into DELTAS, in clockwise order, so a clockwise turn is `(d + 1) % 4` and
// a counter-clockwise turn is `(d + 3) % 4`.
pub const EAST: u8 = 0;
pub const SOUTH: u8 = 1;
pub const WEST: u8 = 2;
pub const NORTH: u8 = 3;
pub const DELTAS: [(i32, i32); 4] = [(1, 0), (0, 1), (-1, 0), (0, -1)];
pub const DIR_NAMES: [&str; 4] = ["E", "S", "W", "N"];

/// The LM-75's interior is capped at 64x64 (66x66 counting the borders).
pub const MAX_DISPLAY: i32 = 64;

/// Pipe arrowheads. The reference lists only lowercase `v` for pipes; uppercase `V` is a direction
/// instruction only (see the runner's CLAUDE.md, ambiguity 3).
pub fn arrow(char: u8) -> Option<u8> {
    match char {
        b'>' => Some(EAST),
        b'v' => Some(SOUTH),
        b'<' => Some(WEST),
        b'^' => Some(NORTH),
        _ => None,
    }
}

pub type Cell = (i32, i32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum RoomKind {
    Room,
    Input,
    Output,
    Display,
}

/// A rectangle drawn with `+`, `-`, `|`. Border coordinates are inclusive.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Room {
    pub x0: i32,
    pub y0: i32,
    pub x1: i32,
    pub y1: i32,
    pub kind: RoomKind,
    pub spawn: Option<Cell>,
    pub outgoing: Vec<u32>,
    pub incoming: Vec<u32>,
}

impl Room {
    pub fn new(x0: i32, y0: i32, x1: i32, y1: i32, kind: RoomKind) -> Self {
        Self { x0, y0, x1, y1, kind, spawn: None, outgoing: Vec::new(), incoming: Vec::new() }
    }

    pub fn contains_interior(&self, x: i32, y: i32) -> bool {
        self.x0 < x && x < self.x1 && self.y0 < y && y < self.y1
    }

    pub fn on_border(&self, x: i32, y: i32) -> bool {
        if !(self.x0 <= x && x <= self.x1 && self.y0 <= y && y <= self.y1) {
            return false;
        }
        x == self.x0 || x == self.x1 || y == self.y0 || y == self.y1
    }

    pub fn interior_cells(&self) -> impl Iterator<Item = Cell> + '_ {
        (self.y0 + 1..self.y1).flat_map(move |y| (self.x0 + 1..self.x1).map(move |x| (x, y)))
    }
}

/// A one-way connection between two rooms. Capacity and latency are both `cells.len()`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Pipe {
    pub cells: Vec<Cell>,
    pub src_room: u32,
    pub dst_room: u32,
    /// Where the terminal arrowhead points, which is *not* the direction of the last hop: that
    /// arrowhead may itself be the final bend (`>--^` into a room above). This is the direction `U`
    /// leaves the man facing, and the direction that decides which side of a display a pipe lands
    /// on. See `docs/vault/heap/Pipes/A terminal arrowhead may also be a bend.md`.
    pub entry_dir: u8,
}

impl Pipe {
    /// The segment touching the sending room — where `s` writes.
    pub fn source(&self) -> Cell {
        self.cells[0]
    }

    /// The segment touching the receiving room — where `r` reads and where output lands.
    pub fn dest(&self) -> Cell {
        self.cells[self.cells.len() - 1]
    }

    /// The border cell the pipe points into — which side of a display it attaches to.
    pub fn entry(&self) -> Cell {
        let (dx, dy) = DELTAS[self.entry_dir as usize];
        let (x, y) = self.dest();
        (x + dx, y + dy)
    }
}

/// Which LM-75 port a pipe drives. The side it lands on is the opcode.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Port {
    Addr,
    Data,
    Swap,
}

impl Port {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Addr => "ADDR",
            Self::Data => "DATA",
            Self::Swap => "SWAP",
        }
    }
}

/// An LM-75, and which of its pipes is which port.
///
/// The device is also a [`Room`] with [`RoomKind::Display`] so that pipe walking, overlap checks
/// and error messages treat it like any other box; this record holds what is display-specific.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Display {
    pub room: u32,
    pub width: i32,
    pub height: i32,
    pub addr: Option<u32>,
    pub data: Option<u32>,
    pub swap: Option<u32>,
}

impl Display {
    pub fn pixels(&self) -> usize {
        (self.width * self.height) as usize
    }

    /// Every attached pipe, in the order the device processes them.
    ///
    /// > The display processes ADDR first, then DATA, then SWAP.
    /// > — language-reference#The LM-75 Display
    pub fn ports(&self) -> impl Iterator<Item = (Port, u32)> + '_ {
        [(Port::Addr, self.addr), (Port::Data, self.data), (Port::Swap, self.swap)]
            .into_iter()
            .filter_map(|(port, index)| index.map(|index| (port, index)))
    }
}

/// One instruction, resolved for one cell walked in one direction.
///
/// Everything geometric is decided at load time: which pipe an `s`/`r`/`q` talks to, what a digit
/// or backtick loads when walked this way, and whether the character is an instruction at all. The
/// tick loop is then one array index and one `match`, with no grid lookup and no hashing.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Op {
    /// A space, a `.`, an `@`, or a digit that belongs to a literal along this axis.
    Nop,
    Halt,
    /// A digit or a closing backtick, with the value it puts in A when walked this way.
    Load(i64),
    ToB,
    Swap,
    Add,
    Sub,
    Mul,
    Neg,
    Div,
    Mod,
    And,
    Or,
    Xor,
    Shl,
    Shr,
    /// `>`, `<`, `^`, `v`, `V` — face this direction.
    Face(u8),
    /// `X` — turn by the sign of A.
    Branch,
    BpSet,
    BpDec,
    BpShr,
    /// `d` — clockwise while the backpack is positive.
    BpCw,
    /// `a` — counter-clockwise while the backpack is positive.
    BpCcw,
    /// `x` — always turns, by the raw low bit.
    BpBit,
    Send(u32),
    Receive(u32),
    Query(u32),
    Broadcast,
    /// `R`, and `U` which also turns toward the pipe it read from.
    Select {
        turn: bool,
    },
    /// `Y` — two copies born left and right of the heading; the original does not continue. Handled
    /// by [`crate::machine::Machine`] rather than by the per-man `execute`, because it changes the
    /// population and its order.
    Split,
    /// A pipe instruction in a room that has no pipe of that direction; the character, for the
    /// message. Fatal when executed, not when loaded — an unreachable `s` is legal.
    NoPipe(u8),
    /// Not an instruction. Fatal when executed, for the same reason.
    BadOp(u8),
}

pub struct Program {
    pub grid: Grid,
    pub rooms: Vec<Room>,
    pub pipes: Vec<Pipe>,
    pub displays: Vec<Display>,
    /// `(room index, spawn cell)` per little man, in reading order.
    pub spawns: Vec<(u32, Cell)>,
    pub input_pipe: Option<u32>,
    pub output_pipe: Option<u32>,
    /// Per cell, the instruction for each of the four walk directions. Indexed by
    /// [`Program::index`]. This is `loads`, the character fetch, `nearest_out` and `nearest_in`
    /// from the Python runner, all folded into one table.
    pub ops: Vec<[Op; 4]>,
    /// Per cell, the room whose interior it is, or [`Program::NO_ROOM`]. A step onto a cell that
    /// is not interior is a `wall` error.
    pub room_of: Vec<u16>,
    /// Per room, incoming pipes ordered by their destination cell in reading order, for `R` / `U`.
    pub incoming_sorted: Vec<Vec<u32>>,
}

impl Program {
    /// No room owns this cell — every step onto it is a `wall` error.
    pub const NO_ROOM: u16 = u16::MAX;

    /// Flat index of a cell. Callers must have bounds-checked `x` and `y` against the grid.
    #[inline]
    pub fn index(&self, x: i32, y: i32) -> usize {
        (y * self.grid.width() + x) as usize
    }

    /// `max(width, height)²` over the content bounding box — the size term of the score.
    pub fn footprint(&self) -> i64 {
        let (width, height) = self.grid.footprint();
        let side = width.max(height) as i64;
        side * side
    }
}
