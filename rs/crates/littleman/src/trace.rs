//! Per-tick tracing and failure reports.
//!
//! A trace line is one man executing one instruction:
//!
//! ```text
//! t=00007 (3,1) E A=42 B=0 BP=0 '*'
//! t=00008 (4,1) E A=42 B=0 BP=0 's' blocked
//! ```

use std::io::Write;

use crate::grid::Grid;
use crate::judge::RunResult;
use crate::machine::{Frame, Man, Pipes, Screen, Tracer};
use crate::model::{DIR_NAMES, Port, Program, RoomKind};

/// Prints the machine's state as it runs. Pass one as the `trace` of a run.
pub struct Printer<W: Write> {
    stream: W,
    last_tick: i64,
}

impl<W: Write> Printer<W> {
    pub fn new(stream: W) -> Self {
        Self { stream, last_tick: -1 }
    }
}

impl<W: Write> Tracer for Printer<W> {
    /// Pipe occupancy, printed once per tick before whatever else that tick did.
    fn pipes(&mut self, tick: u64, pipes: &Pipes) {
        if self.last_tick == tick as i64 {
            return;
        }
        self.last_tick = tick as i64;
        let busy: Vec<String> = (0..pipes.len())
            .filter(|&index| pipes.occupancy(index) > 0)
            .map(|index| {
                let slots: Vec<String> = pipes
                    .contents(index)
                    .map(|slot| slot.map_or("_".to_string(), |value| value.to_string()))
                    .collect();
                format!("#{index}=[{}]", slots.join(","))
            })
            .collect();
        if !busy.is_empty() {
            let _ = writeln!(self.stream, "t={tick:05} pipes {}", busy.join(" "));
        }
    }

    fn step(&mut self, tick: u64, man: &Man, char: u8) {
        let flags = if man.blocked {
            " blocked"
        } else if man.stopped {
            " stopped"
        } else {
            ""
        };
        let _ = writeln!(
            self.stream,
            "t={tick:05} ({},{}) {} A={} B={} BP={} '{}'{flags}",
            man.x, man.y, DIR_NAMES[man.dir as usize], man.a, man.b, man.bp, char as char
        );
    }

    fn device(&mut self, tick: u64, display: usize, port: Port, value: i64, screen: &Screen) {
        let width = screen.display.width as usize;
        let (column, row) = (screen.cursor % width, screen.cursor / width);
        let _ = writeln!(
            self.stream,
            "t={tick:05} display {display} {} {value} cursor=({column},{row})",
            port.as_str()
        );
    }
}

/// What the loader made of the program — the first thing to check when a run misbehaves.
pub fn summary(program: &Program) -> String {
    let (width, height) = program.grid.footprint();
    let mut lines = vec![
        format!("{width}x{height} grid, footprint {}", program.footprint()),
        format!(
            "{} room(s), {} pipe(s), {} little man/men",
            program.rooms.len(),
            program.pipes.len(),
            program.spawns.len()
        ),
    ];
    for (index, room) in program.rooms.iter().enumerate() {
        let kind = match room.kind {
            RoomKind::Room => String::new(),
            other => format!(" [{}]", format!("{other:?}").to_lowercase()),
        };
        let spawn = room.spawn.map_or(String::new(), |(x, y)| format!(" @({x}, {y})"));
        lines.push(format!(
            "  room {index}{kind} ({},{})-({},{}){spawn} out={:?} in={:?}",
            room.x0, room.y0, room.x1, room.y1, room.outgoing, room.incoming
        ));
    }
    for display in &program.displays {
        let room = &program.rooms[display.room as usize];
        let ports: Vec<String> =
            display.ports().map(|(name, index)| format!("{}=#{index}", name.as_str())).collect();
        let ports = if ports.is_empty() { "no pipes".to_string() } else { ports.join(", ") };
        lines.push(format!(
            "  display ({},{})-({},{}) {}x{}, {ports}",
            room.x0, room.y0, room.x1, room.y1, display.width, display.height
        ));
    }
    for (index, pipe) in program.pipes.iter().enumerate() {
        let (sx, sy) = pipe.source();
        let (dx, dy) = pipe.dest();
        lines.push(format!(
            "  pipe {index} room {} ({sx}, {sy}) -> room {} ({dx}, {dy}), {} cell(s)",
            pipe.src_room,
            pipe.dst_room,
            pipe.cells.len()
        ));
    }
    lines.join("\n")
}

/// Expected beside committed, with every differing pixel marked underneath.
pub fn frame_diff(expected: &Frame, got: &Frame) -> String {
    let width = expected.iter().chain(got).map(|row| row.len()).max().unwrap_or(0);
    let mut lines = vec![format!("  {:<width$}   committed", "expected")];
    for index in 0..expected.len().max(got.len()) {
        let want = expected.get(index).map_or("", |row| row.as_str());
        let have = got.get(index).map_or("", |row| row.as_str());
        let marks: String = (0..want.len().max(have.len()))
            .map(|i| {
                let same =
                    want.as_bytes().get(i).is_some_and(|w| have.as_bytes().get(i) == Some(w));
                if same { ' ' } else { '^' }
            })
            .collect();
        lines.push(format!("  {want:<width$}   {have:<width$}   {marks}"));
    }
    lines.join("\n")
}

/// Why a case failed, with the divergence marked and the offending cell shown.
pub fn failure_report(grid: &Grid, result: &RunResult) -> String {
    let error = result.error.as_deref().unwrap_or("failed");
    let mut lines = vec![format!("{error}: {}", result.detail)];
    if !result.expected_frames.is_empty() {
        lines.push(format!(
            "  {}/{} frame(s) matched",
            result.matched_frames,
            result.expected_frames.len()
        ));
        // The frame that failed is the one after the last match, and `frames` ends with it.
        if let Some(got) = result.frames.last()
            && result.matched_frames < result.expected_frames.len()
        {
            lines.push(frame_diff(&result.expected_frames[result.matched_frames], got));
        }
    }
    if !result.expected.is_empty() {
        lines.push(format!("  expected: {}", join(&result.expected)));
        lines.push(format!("  emitted:  {}", join(&result.output)));
        let marker = join(&result.output[..result.matched.min(result.output.len())]).len();
        let pad = marker + usize::from(result.matched > 0);
        lines.push(format!("            {}^", " ".repeat(pad)));
    }
    if let Some((x, y)) = result.cell {
        lines.push(grid.excerpt(x, y, 3));
    }
    lines.join("\n")
}

fn join(values: &[i64]) -> String {
    values.iter().map(|value| value.to_string()).collect::<Vec<_>>().join(" ")
}
