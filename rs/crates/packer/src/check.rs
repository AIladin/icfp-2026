//! Fast abstract netlist logic check.
//!
//! This composes the first allowed variant of every room directly from the `.eman.toml`. It loads
//! the room grids, installs real runtime pipe queues from the declared nets, resolves each audited
//! `s`/`r`/`q` intent to its net, and runs the normal machine. No route search or `.man` file is
//! involved, so this checks room logic rather than packability or layout-dependent timing.

use std::collections::BTreeMap;
use std::path::Path;

use littleman::machine::Pipes;
use littleman::model::{Op, Pipe, Port, Room, RoomKind};
use littleman::{
    Man, Program, RunResult, Screen, Synthesis, TestCase, Tracer, load_program, run_case,
    run_case_traced,
};
use rayon::prelude::*;

use crate::assemble;
use crate::design::Design;
use crate::floorplan::Floorplan;
use crate::library::Library;
use crate::{PackError, validate};

pub fn run(
    library: &Library,
    design: &Design,
    design_path: &Path,
    cases: &[TestCase],
    max_ticks: u64,
    logic_trace: Option<u64>,
    json: bool,
) -> Result<(), PackError> {
    let synthesis = synthesise(library, design)?;
    let runs: Vec<_> = match logic_trace {
        Some(0) => {
            return Err(PackError("--logic-trace interval must be greater than zero".into()));
        }
        Some(interval) => cases
            .iter()
            .enumerate()
            .map(|(index, case)| {
                if index == 0 {
                    let labels = (0..synthesis.program.pipes.len())
                        .map(|pipe| {
                            synthesis
                                .labels
                                .get(&pipe)
                                .cloned()
                                .unwrap_or_else(|| format!("pipe#{pipe}"))
                        })
                        .collect();
                    run_case_traced(
                        &synthesis.program,
                        case,
                        max_ticks,
                        LogicSampler { interval, labels, program: &synthesis.program },
                    )
                } else {
                    run_case(&synthesis.program, case, max_ticks)
                }
            })
            .collect(),
        // Cases share only the immutable loaded program; every run owns its men, pipes, displays
        // and judge state. The indexed parallel iterator preserves case order for diagnostics.
        None => {
            cases.par_iter().map(|case| run_case(&synthesis.program, case, max_ticks)).collect()
        }
    };
    let judged = (!runs.is_empty()).then(|| {
        let passed = runs.iter().filter(|run| run.passed).count();
        let ticks: u64 = runs.iter().map(|run| run.ticks).sum();
        validate::Judged { passed, total: runs.len(), avg_ticks: ticks as f64 / runs.len() as f64 }
    });

    if let Some(result) = &judged
        && result.passed != result.total
    {
        let failure = runs
            .iter()
            .find(|run| !run.passed)
            .map(|run| {
                format!(
                    "; first failure after {} ticks: {}{}",
                    run.ticks,
                    run.detail,
                    frame_mismatch_detail(run)
                )
            })
            .unwrap_or_default();
        return Err(PackError(format!(
            "logic check passes only {}/{} cases — the first room variants or netlist logic are \
             wrong{failure}",
            result.passed, result.total
        )));
    }

    if json {
        let verdict = judged.as_ref().map(|result| {
            serde_json::json!({
                "passed": result.passed,
                "total": result.total,
                "avgTicks": result.avg_ticks,
            })
        });
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "design": design_path.to_string_lossy(),
                "problem": design.problem,
                "mode": "logic-check",
                "verdict": verdict,
            }))
            .expect("serialisable")
        );
        return Ok(());
    }

    let verdict = judged.map_or_else(
        || "NOT JUDGED".to_string(),
        |result| {
            format!("{}/{} pass, avg {:.1} ticks", result.passed, result.total, result.avg_ticks)
        },
    );
    println!(
        "--logic-check: direct first-variant netlist, {} rooms, {} pipes, {verdict}",
        design.instances.len(),
        design.pipes.len()
    );
    Ok(())
}

fn frame_mismatch_detail(run: &RunResult) -> String {
    if run.error.as_deref() != Some("frame-mismatch") {
        return String::new();
    }
    let Some(actual) = run.frames.last() else {
        return String::new();
    };
    let Some(expected) = run.expected_frames.get(run.matched_frames) else {
        return String::new();
    };

    let differing = actual.iter().zip(expected).enumerate().find_map(|(y, (got, want))| {
        got.bytes()
            .zip(want.bytes())
            .position(|(got, want)| got != want)
            .map(|x| (x, y, got.as_bytes()[x] as char, want.as_bytes()[x] as char))
    });
    let pixel = differing.map_or_else(
        || "first differing pixel unavailable".to_string(),
        |(x, y, got, want)| {
            format!("first differing pixel ({x},{y}): actual {got}, expected {want}")
        },
    );
    format!(
        "\n{pixel}\nactual frame:\n{}\nexpected frame:\n{}",
        actual.join("\n"),
        expected.join("\n")
    )
}

struct LogicSampler<'a> {
    interval: u64,
    labels: Vec<String>,
    program: &'a Program,
}

impl Tracer for LogicSampler<'_> {
    fn pipes(&mut self, tick: u64, pipes: &Pipes) {
        if tick % self.interval != 0 {
            return;
        }
        let occupancy = self
            .labels
            .iter()
            .enumerate()
            .map(|(pipe, label)| {
                let contents: Vec<_> = pipes.contents(pipe).collect();
                let first = contents.iter().position(Option::is_some);
                let last = contents.iter().rposition(Option::is_some);
                let span = match (first, last) {
                    (Some(first), Some(last)) => format!("@{first}..{last}"),
                    _ => String::new(),
                };
                format!("{label}={}/{}{span}", pipes.occupancy(pipe), contents.len())
            })
            .collect::<Vec<_>>()
            .join(" ");
        eprintln!("logic trace tick {tick}: {occupancy}");
    }

    fn step(&mut self, tick: u64, man: &Man, char: u8) {
        if tick % self.interval == 0 {
            let compiled = &self.program.ops[self.program.index(man.x, man.y)][man.dir as usize];
            eprintln!(
                "  room={} at=({}, {}) dir={} A={} B={} BP={} blocked={} char={:?} op={compiled:?}",
                man.room, man.x, man.y, man.dir, man.a, man.b, man.bp, man.blocked, char as char,
            );
        }
    }

    fn device(&mut self, tick: u64, display: usize, port: Port, value: i64, _screen: &Screen) {
        if port == Port::Swap {
            eprintln!("  display {display} SWAP {value} at tick {tick}");
        }
    }
}

fn synthesise(library: &Library, design: &Design) -> Result<Synthesis, PackError> {
    let count = design.instances.len();
    let cells: Vec<(usize, usize)> = (0..count).map(|index| (index, index)).collect();
    let variants: Vec<usize> =
        design.instances.iter().map(|instance| instance.allowed[0]).collect();
    let state = Floorplan::grid(library, design, &cells, variants, 2).realize(library, design);
    let (source, _, origin) = assemble::assemble(library, design, &state);
    let mut program = load_program(&source).map_err(|error| PackError(error.to_string()))?;

    let room_of_instance: Vec<usize> =
        state
            .pos
            .iter()
            .map(|&(x, y)| {
                let expected = (x - origin.0, y - origin.1);
                program.rooms.iter().position(|room| (room.x0, room.y0) == expected).ok_or_else(
                    || PackError(format!("temporary room at {expected:?} was not loaded")),
                )
            })
            .collect::<Result<_, _>>()?;

    let mut labels = BTreeMap::new();
    for (pipe_index, spec) in design.pipes.iter().enumerate() {
        let src_room = room_of_instance[spec.from.0];
        let dst_room = room_of_instance[spec.to.0];
        let src_variant = assemble::variant_of(library, design, &state, spec.from.0);
        let dst_variant = assemble::variant_of(library, design, &state, spec.to.0);
        let src_pin = &src_variant.pins[&spec.from.1];
        let dst_pin = &dst_variant.pins[&spec.to.1];
        let source_cell = shifted(state.pos[spec.from.0], src_pin.offset, origin);
        let dest_cell = shifted(state.pos[spec.to.0], dst_pin.offset, origin);
        // `min` is the abstract check's pipe model: designs declare every capacity/latency that
        // their logic needs. Adding arbitrary spare slots both changes behaviour and makes long
        // step-cap checks needlessly expensive.
        let mut pipe_cells = vec![source_cell; spec.min];
        *pipe_cells.last_mut().expect("a pipe has at least two cells") = dest_cell;

        program.pipes.push(Pipe {
            cells: pipe_cells,
            src_room: src_room as u32,
            dst_room: dst_room as u32,
            entry_dir: dst_pin.direction,
        });
        program.rooms[src_room].outgoing.push(pipe_index as u32);
        program.rooms[dst_room].incoming.push(pipe_index as u32);
        labels.insert(pipe_index, spec.id.clone());
    }

    bind_instructions(library, design, &state, &room_of_instance, origin, &mut program)?;
    finish_topology(&room_of_instance, &mut program)?;

    Ok(Synthesis { source, program, labels, warnings: Vec::new(), report: Vec::new() })
}

fn shifted(room: (i32, i32), cell: (i32, i32), origin: (i32, i32)) -> (i32, i32) {
    (room.0 + cell.0 - origin.0, room.1 + cell.1 - origin.1)
}

fn bind_instructions(
    library: &Library,
    design: &Design,
    state: &assemble::State,
    room_of_instance: &[usize],
    origin: (i32, i32),
    program: &mut littleman::Program,
) -> Result<(), PackError> {
    for (instance_index, instance) in design.instances.iter().enumerate() {
        let variant = assemble::variant_of(library, design, state, instance_index);
        let room_index = room_of_instance[instance_index];
        for (cell, char, port) in &variant.intent {
            let outgoing = *char == b's';
            let end = (instance_index, port.clone());
            let pipe_index = design
                .pipes
                .iter()
                .position(|pipe| if outgoing { pipe.from == end } else { pipe.to == end })
                .ok_or_else(|| {
                    PackError(format!("instance '{}' port '{port}' is not wired", instance.name))
                })?;
            let op = match char {
                b's' => Op::Send(pipe_index as u32),
                b'r' => Op::Receive(pipe_index as u32),
                b'q' => Op::Query(pipe_index as u32),
                _ => continue,
            };
            let at = shifted(state.pos[instance_index], *cell, origin);
            let index = program.index(at.0, at.1);
            program.ops[index] = [op; 4];
        }

        // These instructions select their pipes dynamically, so they have no per-port binding
        // intent. `load_program` saw the room before the synthetic topology existed and compiled
        // them as NoPipe; compile them again now that incoming/outgoing lists are populated.
        for (y, row) in variant.rows.iter().enumerate().skip(1).take(variant.rows.len() - 2) {
            for (x, &char) in row.iter().enumerate().skip(1).take(row.len() - 2) {
                let op = match char {
                    b'S' if !program.rooms[room_index].outgoing.is_empty() => Op::Broadcast,
                    b'R' if !program.rooms[room_index].incoming.is_empty() => {
                        Op::Select { turn: false }
                    }
                    b'U' if !program.rooms[room_index].incoming.is_empty() => {
                        Op::Select { turn: true }
                    }
                    _ => continue,
                };
                let at = shifted(state.pos[instance_index], (x as i32, y as i32), origin);
                let index = program.index(at.0, at.1);
                program.ops[index] = [op; 4];
            }
        }
    }
    Ok(())
}

fn finish_topology(
    room_of_instance: &[usize],
    program: &mut littleman::Program,
) -> Result<(), PackError> {
    for incoming in &mut program.incoming_sorted {
        incoming.clear();
    }
    for (room_index, room) in program.rooms.iter().enumerate() {
        let mut incoming = room.incoming.clone();
        incoming.sort_by_key(|&index| {
            let (x, y) = program.pipes[index as usize].dest();
            (y, x)
        });
        program.incoming_sorted[room_index] = incoming;
        match room.kind {
            RoomKind::Input => program.input_pipe = room.outgoing.first().copied(),
            RoomKind::Output => program.output_pipe = room.incoming.first().copied(),
            RoomKind::Room | RoomKind::Display => {}
        }
    }

    for display_index in 0..program.displays.len() {
        let room_index = program.displays[display_index].room as usize;
        if !room_of_instance.contains(&room_index) {
            continue;
        }
        let incoming = program.rooms[room_index].incoming.clone();
        for pipe_index in incoming {
            let port =
                display_port(&program.rooms[room_index], &program.pipes[pipe_index as usize])?;
            let display = &mut program.displays[display_index];
            let slot = match port {
                Port::Addr => &mut display.addr,
                Port::Data => &mut display.data,
                Port::Swap => &mut display.swap,
            };
            if slot.replace(pipe_index).is_some() {
                return Err(PackError(format!(
                    "two synthetic pipes attach to the {} port of display room {room_index}",
                    port.as_str()
                )));
            }
        }
    }
    Ok(())
}

/// Display operations are geometric, not interface-name conventions: top is ADDR, left is DATA,
/// bottom is SWAP, and the right side is invalid.
fn display_port(room: &Room, pipe: &Pipe) -> Result<Port, PackError> {
    let (x, y) = pipe.entry();
    if (x == room.x0 || x == room.x1) && (y == room.y0 || y == room.y1) {
        return Err(PackError(format!(
            "synthetic pipe attaches to a corner of display room at ({},{})",
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
    Err(PackError(format!(
        "synthetic pipe attaches to the right side of display room at ({},{})",
        room.x0, room.y0
    )))
}

#[cfg(test)]
mod tests {
    use super::*;
    use littleman::model::{EAST, NORTH, SOUTH, WEST};

    fn root() -> std::path::PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..")
    }

    #[test]
    fn sudoku_broadcast_and_select_logic_check_passes() {
        let root = root();
        let library = crate::library::load_library(&root.join("rooms")).expect("load rooms");
        let design_path = root.join("programs/sudoku-validity/sudoku.eman.toml");
        let design = crate::design::load_design(&design_path, &library).expect("load design");
        let synthesis = synthesise(&library, &design).expect("synthesise direct topology");
        let raw = std::fs::read_to_string(root.join("cases-sudoku-validity.json")).expect("cases");
        let cases = littleman::parse_cases(&raw).expect("parse cases");
        let judged = validate::judge(&synthesis, &cases, littleman::DEFAULT_MAX_TICKS);
        assert_eq!((judged.passed, judged.total), (6, 6));
    }

    fn pipe(dest: (i32, i32), entry_dir: u8) -> Pipe {
        Pipe { cells: vec![dest, dest], src_room: 0, dst_room: 1, entry_dir }
    }

    #[test]
    fn display_ports_are_geometric() {
        let room = Room::new(0, 0, 10, 10, RoomKind::Display);
        assert_eq!(display_port(&room, &pipe((5, -1), SOUTH)).unwrap(), Port::Addr);
        assert_eq!(display_port(&room, &pipe((-1, 5), EAST)).unwrap(), Port::Data);
        assert_eq!(display_port(&room, &pipe((5, 11), NORTH)).unwrap(), Port::Swap);
        assert!(display_port(&room, &pipe((11, 5), WEST)).is_err());
    }

    #[test]
    fn frame_mismatch_names_the_pixel_and_prints_both_frames() {
        let run = RunResult {
            error: Some("frame-mismatch".into()),
            frames: vec![vec!["40".into(), "00".into()]],
            expected_frames: vec![vec!["44".into(), "00".into()]],
            ..RunResult::default()
        };
        let detail = frame_mismatch_detail(&run);
        assert!(detail.contains("first differing pixel (1,0): actual 0, expected 4"));
        assert!(detail.contains("actual frame:\n40\n00"));
        assert!(detail.contains("expected frame:\n44\n00"));
    }
}
