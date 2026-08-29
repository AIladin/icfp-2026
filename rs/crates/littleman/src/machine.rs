//! The machine: little men walking the grid, and the four-phase tick loop.
//!
//! > Within one tick, in order:
//! > 1. Pipes shift ... 2. I/O ... 3. Execution ... 4. Movement
//! > — language-reference#Tick order
//!
//! Until `Y` (Split) arrived, executing the men sequentially in reading order was equivalent to
//! executing them simultaneously: a room held at most one man, a pipe has exactly one source room
//! and one destination room, and a pipe's source and destination cells are always distinct (pipes
//! are at least 2 cells long). So no two men could ever touch the same pipe cell within one phase.
//!
//! `Y` breaks the one-man-per-room premise, and the spec replaces it with an explicit order:
//!
//! > Little men act in creation order, every tick. On a split, the copy born to the right takes
//! > over the splitting man's place in that order; the copy born to the left becomes the newest
//! > little man and acts after all others. — split#Y, precisely
//!
//! [`Machine::men`] *is* that order, so the right copy is spliced in at the splitter's index and
//! the left copy is pushed. Removing the dead never reorders the living.

use std::collections::HashMap;
use std::collections::hash_map::Entry;

use crate::errors::{RunError, RunErrorKind};
use crate::load::{bad_op_detail, no_pipe_detail};
use crate::model::{Cell, DELTAS, Display, EAST, Op, Port, Program};

const HEX: &[u8; 16] = b"0123456789abcdef";

/// > The maximum number of live little men is 65536. Exceeding this limit is an error and ends
/// > your program. — split#Y, precisely
pub const MAX_MEN: usize = 65536;

/// Committed frames are kept only for reports and `lmr run`; the judge compares them streaming, so
/// a program that swaps every tick must not be able to fill memory with its own history.
const FRAME_HISTORY: usize = 64;

/// One committed frame in the contest's wire format: `height` rows of `width` hex digits.
pub type Frame = Vec<String>;

/// How a run ended.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    /// Every little man stopped and the pipes drained.
    Halted,
    /// The [`Io`] ended it — passed, or failed on a mismatch.
    Judged,
    /// The step cap was reached.
    StepCap,
}

#[derive(Debug, Clone)]
pub struct Man {
    pub room: u32,
    pub x: i32,
    pub y: i32,
    pub dir: u8,
    pub a: i64,
    pub b: i64,
    pub bp: i64,
    pub stopped: bool,
    pub blocked: bool,
    /// Placed by a `Y` during this tick's execution phase. A newborn is already *on* his cell, so
    /// he skips the movement phase he was born in and executes that cell on the next tick — exactly
    /// as if he had walked onto it. Cleared by the movement phase.
    pub born: bool,
    /// A wall step is fatal, but not until the man would *execute* on the cell — the next tick's
    /// I/O phase runs first, so a value still in the output pipe is emitted before the run dies.
    /// Confirmed against the server 2026-07-24; see `Output survives the wall error` in the vault.
    pub fault: Option<RunError>,
}

impl Man {
    /// A little man on `cell`, facing `dir`, with empty hands and an empty backpack.
    pub fn new(room: u32, (x, y): Cell, dir: u8) -> Self {
        Self {
            room,
            x,
            y,
            dir,
            a: 0,
            b: 0,
            bp: 0,
            stopped: false,
            blocked: false,
            born: false,
            fault: None,
        }
    }

    /// A copy of this man, born one step `dir` away and facing that way.
    fn copy_at(&self, room: u32, (x, y): Cell, dir: u8) -> Self {
        Self {
            room,
            x,
            y,
            dir,
            a: self.a,
            b: self.b,
            bp: self.bp,
            stopped: false,
            blocked: false,
            born: true,
            fault: None,
        }
    }

    #[inline]
    fn cell(&self) -> Cell {
        (self.x, self.y)
    }
}

/// How the machine talks to the judge: input it may release, output it must account for.
pub trait Io {
    /// The next input value, or `None` when nothing is released yet (a withheld round).
    fn take(&mut self) -> Option<i64>;

    /// Consume an output value; return `false` to end the run (passed, or failed on a mismatch).
    fn emit(&mut self, value: i64, tick: u64) -> bool;

    /// Account for a frame an LM-75 just swapped in. Same contract as [`Io::emit`].
    fn commit(&mut self, frame: &Frame, tick: u64) -> bool;
}

/// Where a run reports what it just did, one call per event.
///
/// `ACTIVE` is what makes tracing free: [`NoTrace`] sets it to `false`, so the compiler drops both
/// the calls and the work of preparing their arguments.
pub trait Tracer {
    const ACTIVE: bool = true;

    /// Pipe occupancy, offered once per tick before whatever else that tick did.
    fn pipes(&mut self, tick: u64, pipes: &Pipes);

    fn step(&mut self, tick: u64, man: &Man, char: u8);

    fn device(&mut self, tick: u64, display: usize, port: Port, value: i64, screen: &Screen);
}

/// The tracer used when nobody is watching.
pub struct NoTrace;

impl Tracer for NoTrace {
    const ACTIVE: bool = false;
    fn pipes(&mut self, _tick: u64, _pipes: &Pipes) {}
    fn step(&mut self, _tick: u64, _man: &Man, _char: u8) {}
    fn device(&mut self, _tick: u64, _display: usize, _port: Port, _value: i64, _screen: &Screen) {}
}

/// Every pipe's contents, in one flat arena.
///
/// Slot 0 of a pipe is the source cell (where `s` writes) and the last slot is the destination
/// (where `r` reads, where output lands, and where a display consumes). `count` is what lets the
/// shift phase skip an idle pipe outright instead of walking it.
pub struct Pipes {
    slots: Vec<i64>,
    full: Vec<bool>,
    span: Vec<(usize, usize)>,
    count: Vec<u32>,
}

impl Pipes {
    fn new(program: &Program) -> Self {
        let mut span = Vec::with_capacity(program.pipes.len());
        let mut total = 0;
        for pipe in &program.pipes {
            span.push((total, pipe.cells.len()));
            total += pipe.cells.len();
        }
        Self {
            slots: vec![0; total],
            full: vec![false; total],
            count: vec![0; program.pipes.len()],
            span,
        }
    }

    pub fn len(&self) -> usize {
        self.span.len()
    }

    pub fn is_empty(&self) -> bool {
        self.span.is_empty()
    }

    /// The value at the destination end, if any.
    #[inline]
    pub fn peek_dest(&self, pipe: usize) -> Option<i64> {
        let (offset, len) = self.span[pipe];
        let last = offset + len - 1;
        if self.full[last] { Some(self.slots[last]) } else { None }
    }

    /// Take the value at the destination end.
    #[inline]
    fn take_dest(&mut self, pipe: usize) -> Option<i64> {
        let (offset, len) = self.span[pipe];
        let last = offset + len - 1;
        if !self.full[last] {
            return None;
        }
        self.full[last] = false;
        self.count[pipe] -= 1;
        Some(self.slots[last])
    }

    /// Whether the source end is occupied — a `s` onto a full pipe blocks.
    #[inline]
    fn source_full(&self, pipe: usize) -> bool {
        self.full[self.span[pipe].0]
    }

    #[inline]
    fn put_source(&mut self, pipe: usize, value: i64) {
        let offset = self.span[pipe].0;
        self.slots[offset] = value;
        self.full[offset] = true;
        self.count[pipe] += 1;
    }

    #[inline]
    pub fn occupancy(&self, pipe: usize) -> u32 {
        self.count[pipe]
    }

    /// Place a value straight onto a pipe's destination cell, skipping the shift phase.
    ///
    /// For tests and tools that drive a device directly instead of writing a program to feed it.
    /// A value already there is replaced.
    pub fn put_dest(&mut self, pipe: usize, value: i64) {
        let (offset, len) = self.span[pipe];
        let last = offset + len - 1;
        if !self.full[last] {
            self.count[pipe] += 1;
        }
        self.slots[last] = value;
        self.full[last] = true;
    }

    /// The slots of one pipe, source end first, for tracing.
    pub fn contents(&self, pipe: usize) -> impl Iterator<Item = Option<i64>> + '_ {
        let (offset, len) = self.span[pipe];
        (offset..offset + len).map(move |i| if self.full[i] { Some(self.slots[i]) } else { None })
    }

    fn shift(&mut self) {
        for (pipe, &(offset, len)) in self.span.iter().enumerate() {
            if self.count[pipe] == 0 {
                continue;
            }
            for i in (1..len).rev() {
                let (here, behind) = (offset + i, offset + i - 1);
                if !self.full[here] && self.full[behind] {
                    self.slots[here] = self.slots[behind];
                    self.full[here] = true;
                    self.full[behind] = false;
                }
            }
        }
    }
}

/// One LM-75's state: two buffers of colour indices, and the cursor into `next`.
///
/// > The current and next buffers are initially filled with color 0 (black). The cursor begins at
/// > position 0, 0. — language-reference#The LM-75 Display
pub struct Screen {
    pub display: Display,
    pub current: Vec<u8>,
    pub next: Vec<u8>,
    pub cursor: usize,
}

impl Screen {
    fn new(display: &Display) -> Self {
        let pixels = display.pixels();
        Self {
            display: display.clone(),
            current: vec![0; pixels],
            next: vec![0; pixels],
            cursor: 0,
        }
    }

    /// The current buffer in the wire format: one lowercase hex digit per pixel, row by row.
    pub fn frame(&self) -> Frame {
        self.current
            .chunks(self.display.width as usize)
            .map(|row| row.iter().map(|&c| HEX[c as usize] as char).collect())
            .collect()
    }
}

pub struct Machine<'p, I: Io, T: Tracer> {
    pub program: &'p Program,
    pub io: I,
    pub trace: T,
    pub pipes: Pipes,
    pub men: Vec<Man>,
    pub screens: Vec<Screen>,
    pub output: Vec<i64>,
    /// The last [`FRAME_HISTORY`] committed frames, for reports; `frame_count` is the real total.
    pub frames: Vec<Frame>,
    pub frame_count: u64,
    pub tick: u64,
    /// Two men can only ever share a cell if the program can split: a room holds at most one `@`,
    /// so without `Y` every man has a room to himself and the collision rules are dead letters.
    /// Deciding it once here keeps the per-tick scan off every program that never splits. A test
    /// that places men by hand sets this itself.
    pub can_collide: bool,
}

impl<'p, I: Io> Machine<'p, I, NoTrace> {
    pub fn new(program: &'p Program, io: I) -> Self {
        Self::traced(program, io, NoTrace)
    }
}

impl<'p, I: Io, T: Tracer> Machine<'p, I, T> {
    pub fn traced(program: &'p Program, io: I, trace: T) -> Self {
        Self {
            pipes: Pipes::new(program),
            men: program.spawns.iter().map(|&(room, cell)| Man::new(room, cell, EAST)).collect(),
            screens: program.displays.iter().map(Screen::new).collect(),
            output: Vec::new(),
            frames: Vec::new(),
            frame_count: 0,
            tick: 0,
            can_collide: (0..program.grid.height()).any(|y| program.grid.row(y).contains(&b'Y')),
            program,
            io,
            trace,
        }
    }

    /// Run to completion.
    pub fn run(&mut self, max_ticks: u64) -> Result<Outcome, RunError> {
        while self.tick < max_ticks {
            if self.men.iter().all(|man| man.stopped) {
                return self.drain(max_ticks);
            }
            self.tick += 1;
            self.pipes.shift();
            if T::ACTIVE {
                self.trace.pipes(self.tick, &self.pipes);
            }
            if !self.transfer_io() {
                return Ok(Outcome::Judged);
            }
            self.execute_all()?;
            if !self.display_step()? {
                return Ok(Outcome::Judged);
            }
            self.move_all();
        }
        Ok(Outcome::StepCap)
    }

    /// > pipes and I/O rooms keep ticking until the output pipe drains — Tick order fine print
    ///
    /// Display pipes are drained too, so a SWAP still in flight when the last man halts commits
    /// rather than being lost. The reference names only the output pipe; see the runner's
    /// CLAUDE.md, assumption 6.
    fn drain(&mut self, max_ticks: u64) -> Result<Outcome, RunError> {
        while self.tick < max_ticks {
            if !self.in_flight() {
                return Ok(Outcome::Halted);
            }
            self.tick += 1;
            self.pipes.shift();
            if T::ACTIVE {
                self.trace.pipes(self.tick, &self.pipes);
            }
            if !self.transfer_io() {
                return Ok(Outcome::Judged);
            }
            if !self.display_step()? {
                return Ok(Outcome::Judged);
            }
        }
        Ok(Outcome::StepCap)
    }

    /// Whether any value is still on its way to the output room or to a display.
    fn in_flight(&self) -> bool {
        if let Some(out) = self.program.output_pipe
            && self.pipes.occupancy(out as usize) > 0
        {
            return true;
        }
        self.program
            .displays
            .iter()
            .flat_map(|display| display.ports())
            .any(|(_, index)| self.pipes.occupancy(index as usize) > 0)
    }

    fn transfer_io(&mut self) -> bool {
        if let Some(out) = self.program.output_pipe
            && let Some(value) = self.pipes.take_dest(out as usize)
        {
            self.output.push(value);
            if !self.io.emit(value, self.tick) {
                return false;
            }
        }
        if let Some(source) = self.program.input_pipe {
            let source = source as usize;
            if !self.pipes.source_full(source)
                && let Some(value) = self.io.take()
            {
                self.pipes.put_source(source, value);
            }
        }
        true
    }

    fn execute_all(&mut self) -> Result<(), RunError> {
        let program = self.program;
        let tick = self.tick;
        let Self { men, pipes, trace, .. } = self;
        let mut split = false;
        // The length is read once: a left copy pushed by a split does not execute on the tick it
        // was born, and a right copy has already been passed by the time it replaces its splitter.
        for index in 0..men.len() {
            let wants_split = {
                let man = &mut men[index];
                if man.stopped || man.born {
                    continue;
                }
                if let Some(fault) = man.fault.take() {
                    return Err(fault);
                }
                let wants_split = execute(man, program, pipes)?;
                if T::ACTIVE {
                    let char = program.grid.at(man.x, man.y);
                    trace.step(tick, man, char);
                }
                wants_split
            };
            if wants_split {
                Self::split(men, index, program)?;
                split = true;
            }
        }
        if split {
            // Births are the only way two men can end the execution phase on one cell, so this
            // scan covers both "born onto an occupant" and "two `Y`s spawning onto one cell".
            cull(men, &overlaps(men));
        }
        Ok(())
    }

    /// `Y`: two copies born beside the splitter, each heading away from him.
    ///
    /// > `Y` splits the little man in two. The copies are born on the cells to his left and his
    /// > right — left and right relative to his heading as he enters the `Y` — each heading away
    /// > from the `Y`. The original man does not continue past the `Y`; only the two copies remain.
    /// > — split#Y, precisely
    ///
    /// Directions are clockwise, so right of the heading is `dir + 1` and left is `dir + 3`. `Y` is
    /// unconditional: both births happen (or raise) whatever is standing there.
    fn split(men: &mut Vec<Man>, index: usize, program: &Program) -> Result<(), RunError> {
        let man = &men[index];
        let right = birth(man, (man.dir + 1) % 4, program)?;
        let left = birth(man, (man.dir + 3) % 4, program)?;
        let cell = man.cell();
        men[index] = right;
        men.push(left);
        if men.len() > MAX_MEN {
            return Err(RunError::new(
                RunErrorKind::Population,
                format!("a split took the population past {MAX_MEN} live little men"),
                cell,
            ));
        }
        Ok(())
    }

    /// > Displays consume and process input. — Tick order, phase 3
    ///
    /// > The display can read a value from all 3 of its pipes in the same tick. The display
    /// > processes ADDR first, then DATA, then SWAP. — language-reference#The LM-75 Display
    ///
    /// Running this after the men is safe either way: a man only ever writes a pipe's *source*
    /// cell and a display only reads its *destination* cell, and pipes are at least two cells long.
    pub fn display_step(&mut self) -> Result<bool, RunError> {
        for number in 0..self.screens.len() {
            let ports: Vec<(Port, u32)> = self.screens[number].display.ports().collect();
            for (port, index) in ports {
                let Some(value) = self.pipes.take_dest(index as usize) else { continue };
                let cell = self.program.pipes[index as usize].dest();
                if !self.apply(number, cell, port, value)? {
                    return Ok(false);
                }
                if T::ACTIVE {
                    self.trace.device(self.tick, number, port, value, &self.screens[number]);
                }
            }
        }
        Ok(true)
    }

    /// One value into one port. Every out-of-range value ends the whole program.
    fn apply(
        &mut self,
        number: usize,
        cell: (i32, i32),
        port: Port,
        value: i64,
    ) -> Result<bool, RunError> {
        let screen = &mut self.screens[number];
        let pixels = screen.display.pixels() as i64;
        match port {
            Port::Addr => {
                if value < 0 || value >= pixels {
                    return Err(RunError::new(
                        RunErrorKind::Display,
                        format!(
                            "ADDR {value} is outside a {}x{} display (0..{})",
                            screen.display.width,
                            screen.display.height,
                            pixels - 1
                        ),
                        cell,
                    ));
                }
                screen.cursor = value as usize;
            }
            Port::Data => {
                if !(0..=15).contains(&value) {
                    return Err(RunError::new(
                        RunErrorKind::Display,
                        format!("colour {value} is not one of the 16 colours (0..15)"),
                        cell,
                    ));
                }
                screen.next[screen.cursor] = value as u8;
                // Next column, else next row, else back to the upper-left — which is what
                // advancing a `row * width + column` cursor modulo the pixel count does.
                screen.cursor = (screen.cursor + 1) % pixels as usize;
            }
            Port::Swap => {
                if value != 0 && value != 1 {
                    return Err(RunError::new(
                        RunErrorKind::Display,
                        format!("SWAP {value} is neither 0 nor 1"),
                        cell,
                    ));
                }
                screen.current.copy_from_slice(&screen.next);
                if value == 0 {
                    screen.next.fill(0);
                    screen.cursor = 0;
                }
                let frame = screen.frame();
                return Ok(self.commit(frame));
            }
        }
        Ok(true)
    }

    fn commit(&mut self, frame: Frame) -> bool {
        self.frame_count += 1;
        self.frames.push(frame);
        if self.frames.len() > FRAME_HISTORY {
            self.frames.drain(..self.frames.len() - FRAME_HISTORY);
        }
        let frame = self.frames.last().expect("just pushed");
        self.io.commit(frame, self.tick)
    }

    fn move_all(&mut self) {
        let program = self.program;
        let (width, height) = (program.grid.width(), program.grid.height());
        let before: Vec<Cell> =
            if self.can_collide { self.men.iter().map(Man::cell).collect() } else { Vec::new() };
        for man in self.men.iter_mut() {
            if man.born {
                // Born already standing on his cell during this tick's execution phase; he executes
                // it next tick, so this movement phase is the one he does not get.
                man.born = false;
                continue;
            }
            if man.stopped || man.blocked {
                continue;
            }
            let (dx, dy) = DELTAS[man.dir as usize];
            let (nx, ny) = (man.x + dx, man.y + dy);
            let interior = nx >= 0
                && ny >= 0
                && nx < width
                && ny < height
                && program.room_of[(ny * width + nx) as usize] != Program::NO_ROOM;
            if !interior {
                // Armed here, thrown at the next tick's execution phase — phases 1 and 2 of that
                // tick still run, so the output pipe gets to deliver.
                man.fault = Some(RunError::new(
                    RunErrorKind::Wall,
                    format!(
                        "a little man walked into the wall at ({nx},{ny}) from ({},{})",
                        man.x, man.y
                    ),
                    (nx, ny),
                ));
                continue;
            }
            (man.x, man.y) = (nx, ny);
        }
        if self.can_collide && self.men.len() > 1 {
            let mut doomed = overlaps(&self.men);
            doomed.extend(swaps(&self.men, &before));
            cull(&mut self.men, &doomed);
        }
    }
}

/// One copy, on the cell one step `dir` from the splitter and facing that way.
///
/// > If the birth cell is a wall, the program halts with an error. — split#Y, precisely
///
/// Any cell that is not room interior is a wall here, exactly as it is for a step (assumption 5 in
/// the runner's CLAUDE.md) — a room's own border, another room, a pipe, or open paper.
fn birth(man: &Man, dir: u8, program: &Program) -> Result<Man, RunError> {
    let (dx, dy) = DELTAS[dir as usize];
    let (nx, ny) = (man.x + dx, man.y + dy);
    let (width, height) = (program.grid.width(), program.grid.height());
    let room = if nx >= 0 && ny >= 0 && nx < width && ny < height {
        program.room_of[(ny * width + nx) as usize]
    } else {
        Program::NO_ROOM
    };
    if room == Program::NO_ROOM {
        return Err(RunError::new(
            RunErrorKind::Wall,
            format!(
                "a little man was split into the wall at ({nx},{ny}) from ({},{})",
                man.x, man.y
            ),
            (nx, ny),
        ));
    }
    Ok(man.copy_at(room as u32, (nx, ny), dir))
}

/// Indices of men sharing a cell with another man. Both parties die, and it is not an error.
///
/// > If two little men in the same room collide, they both die. This is not an error.
/// > — split#Y, precisely
fn overlaps(men: &[Man]) -> Vec<usize> {
    let mut seen: HashMap<Cell, usize> = HashMap::with_capacity(men.len());
    let mut doomed = Vec::new();
    for (index, man) in men.iter().enumerate() {
        match seen.entry(man.cell()) {
            Entry::Vacant(slot) => {
                slot.insert(index);
            }
            Entry::Occupied(slot) => {
                doomed.push(*slot.get());
                doomed.push(index);
            }
        }
    }
    doomed
}

/// Indices of men who moved *through* each other. Both die, and it is not an error.
///
/// > This includes two men arriving on the same cell in the same tick, and two adjacent men moving
/// > through each other (swapping cells) in the same tick. — split#Y, precisely
///
/// Arriving on one cell is [`overlaps`]; this is the other half, which needs each man's cell from
/// *before* the phase as well as after. A man who did not move cannot swap: he still stands where
/// he started, so nobody can have taken his old cell for his new one.
fn swaps(men: &[Man], before: &[Cell]) -> Vec<usize> {
    // Cells at the start of the phase are distinct — every collision is culled as it happens.
    let origin: HashMap<Cell, usize> =
        before.iter().enumerate().map(|(index, &cell)| (cell, index)).collect();
    let mut doomed = Vec::new();
    for (index, man) in men.iter().enumerate() {
        let Some(&other) = origin.get(&man.cell()) else { continue };
        if other != index && men[other].cell() == before[index] {
            doomed.push(index);
            doomed.push(other);
        }
    }
    doomed
}

/// Drop the dead. Survivors keep their relative order, which *is* the creation order.
fn cull(men: &mut Vec<Man>, doomed: &[usize]) {
    if doomed.is_empty() {
        return;
    }
    let mut dead = vec![false; men.len()];
    for &index in doomed {
        dead[index] = true;
    }
    let mut index = 0;
    men.retain(|_| {
        let keep = !dead[index];
        index += 1;
        keep
    });
}

/// One little man, one instruction. Returns whether the cell was a `Y` and wants a split.
fn execute(man: &mut Man, program: &Program, pipes: &mut Pipes) -> Result<bool, RunError> {
    man.blocked = false;
    let op = program.ops[program.index(man.x, man.y)][man.dir as usize];
    match op {
        Op::Nop => {}
        Op::Load(value) => man.a = value,
        Op::Halt => man.stopped = true,
        Op::ToB => man.b = man.a,
        Op::Swap => std::mem::swap(&mut man.a, &mut man.b),
        Op::Add => man.a = man.a.wrapping_add(man.b),
        Op::Sub => man.a = man.a.wrapping_sub(man.b),
        Op::Mul => man.a = man.a.wrapping_mul(man.b),
        Op::Neg => man.a = man.a.wrapping_neg(),
        Op::Div => {
            // Floored, remainder into B. B = 0 gives A = 0 with the dividend kept in B.
            if man.b == 0 {
                (man.a, man.b) = (0, man.a);
            } else {
                let (quotient, remainder) = floor_divmod(man.a, man.b);
                (man.a, man.b) = (quotient, remainder);
            }
        }
        Op::Mod => man.a = if man.b == 0 { 0 } else { floor_divmod(man.a, man.b).1 },
        Op::And => man.a &= man.b,
        Op::Or => man.a |= man.b,
        Op::Xor => man.a ^= man.b,
        Op::Shl => {
            man.a = if (0..=63).contains(&man.b) { man.a.wrapping_shl(man.b as u32) } else { 0 }
        }
        Op::Shr => man.a = shift_right(man.a, man.b),
        Op::Face(dir) => man.dir = dir,
        Op::Branch => {
            if man.a > 0 {
                man.dir = (man.dir + 1) % 4;
            } else if man.a < 0 {
                man.dir = (man.dir + 3) % 4;
            }
        }
        Op::BpSet => man.bp = man.a,
        Op::BpDec => man.bp = man.bp.wrapping_sub(1),
        Op::BpShr => man.bp >>= 1,
        Op::BpCw => {
            if man.bp > 0 {
                man.dir = (man.dir + 1) % 4;
            }
        }
        Op::BpCcw => {
            if man.bp > 0 {
                man.dir = (man.dir + 3) % 4;
            }
        }
        // Always turns, and reads the raw low bit: a negative backpack is not zero.
        Op::BpBit => man.dir = if man.bp & 1 != 0 { (man.dir + 1) % 4 } else { (man.dir + 3) % 4 },
        Op::Query(pipe) => man.bp = pipes.occupancy(pipe as usize) as i64,
        Op::Send(pipe) => {
            let pipe = pipe as usize;
            if pipes.source_full(pipe) {
                man.blocked = true;
            } else {
                pipes.put_source(pipe, man.a);
            }
        }
        Op::Broadcast => {
            let outgoing = &program.rooms[man.room as usize].outgoing;
            // All or nothing: it never writes to just some of them.
            if outgoing.iter().any(|&index| pipes.source_full(index as usize)) {
                man.blocked = true;
            } else {
                for &index in outgoing {
                    pipes.put_source(index as usize, man.a);
                }
            }
        }
        Op::Receive(pipe) => match pipes.take_dest(pipe as usize) {
            Some(value) => man.a = value,
            None => man.blocked = true,
        },
        // `R` takes from any ready incoming pipe, reading order breaking ties; `U` then turns.
        Op::Select { turn } => {
            man.blocked = true;
            for &index in &program.incoming_sorted[man.room as usize] {
                let Some(value) = pipes.take_dest(index as usize) else { continue };
                man.a = value;
                man.blocked = false;
                if turn {
                    // Turn away from the pipe he read from: face the way that pipe flows into the
                    // room.
                    man.dir = program.pipes[index as usize].entry_dir;
                }
                break;
            }
        }
        Op::NoPipe(char) => {
            return Err(RunError::new(
                RunErrorKind::NoPipe,
                no_pipe_detail(char, man.x, man.y),
                (man.x, man.y),
            ));
        }
        Op::BadOp(char) => {
            return Err(RunError::new(
                RunErrorKind::BadOp,
                bad_op_detail(char, man.x, man.y),
                (man.x, man.y),
            ));
        }
        // The population and its order are the machine's business, not one man's.
        Op::Split => return Ok(true),
    }
    Ok(false)
}

/// Python's `divmod`: floored quotient, remainder taking the divisor's sign.
#[inline]
fn floor_divmod(a: i64, b: i64) -> (i64, i64) {
    let quotient = a.wrapping_div(b);
    let remainder = a.wrapping_rem(b);
    if remainder != 0 && (remainder < 0) != (b < 0) {
        (quotient.wrapping_sub(1), remainder.wrapping_add(b))
    } else {
        (quotient, remainder)
    }
}

/// Arithmetic right shift: 0 when B < 0, sign-filled when B > 63.
#[inline]
fn shift_right(a: i64, b: i64) -> i64 {
    if b < 0 {
        return 0;
    }
    if b > 63 {
        return if a < 0 { -1 } else { 0 };
    }
    a >> b
}
