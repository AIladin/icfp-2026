use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use clap::{Parser, ValueEnum};
use littleman::model::{Cell, Pipe, Program, Room};
use littleman::{
    DEFAULT_MAX_TICKS, Grid, Marker, Synthesis, load_program, parse_cases, run_case, score,
    synthesise_markers_negotiated,
};

const DEFAULT_ROUNDS: usize = 24;

#[derive(Debug, Parser)]
#[command(about = "Isolated post-route orthogonal compaction experiment")]
struct Args {
    /// Passing routed program to compact.
    input: PathBuf,
    /// Test cases in the bare-list or problem-object JSON shape.
    #[arg(short, long)]
    cases: PathBuf,
    /// Where to write an improved program. No file is written without an improvement.
    #[arg(short, long)]
    output: PathBuf,
    /// Judge scoring mode.
    #[arg(long, value_enum, default_value_t = Scoring::FootprintTick)]
    scoring: Scoring,
    #[arg(long, default_value_t = DEFAULT_MAX_TICKS)]
    max_ticks: u64,
    /// Negotiated rip-up-and-reroute rounds per placement.
    #[arg(long, default_value_t = DEFAULT_ROUNDS)]
    rounds: usize,
    /// Greedy sweeps over all horizontal and vertical room-band cuts.
    #[arg(long, default_value_t = 4)]
    passes: usize,
}

#[derive(Debug, Clone, Copy, ValueEnum)]
enum Scoring {
    Footprint,
    FootprintTick,
}

impl Scoring {
    fn as_str(self) -> &'static str {
        match self {
            Self::Footprint => "footprint",
            Self::FootprintTick => "footprint-tick",
        }
    }
}

#[derive(Clone)]
struct RoomTemplate {
    width: i32,
    height: i32,
    cells: Vec<Vec<u8>>,
}

#[derive(Clone)]
struct Endpoint {
    room: usize,
    offset: Cell,
    direction: u8,
    outgoing: bool,
}

#[derive(Clone)]
struct PipeTemplate {
    label: String,
    from: Endpoint,
    to: Endpoint,
    min_length: usize,
}

struct Design {
    rooms: Vec<RoomTemplate>,
    pipes: Vec<PipeTemplate>,
}

struct Evaluated {
    positions: Vec<Cell>,
    synthesis: Synthesis,
    score: f64,
    max_dim: i32,
    avg_ticks: f64,
}

fn main() -> Result<(), String> {
    let args = Args::parse();
    if args.rounds == 0 {
        return Err("--rounds must be greater than zero".into());
    }

    let source = read(&args.input)?;
    let original =
        load_program(&source).map_err(|error| format!("load {}: {error}", args.input.display()))?;
    let cases_text = read(&args.cases)?;
    let cases = parse_cases(&cases_text)
        .map_err(|error| format!("parse {}: {error}", args.cases.display()))?;
    if cases.is_empty() {
        return Err("the supplied cases file contains no cases".into());
    }

    let original_runs: Vec<_> =
        cases.iter().map(|case| run_case(&original, case, args.max_ticks)).collect();
    let Some(original_score) = score(&original, &original_runs, args.scoring.as_str()) else {
        let failure = original_runs
            .iter()
            .find(|run| !run.passed)
            .map(|run| format!("{} after {} ticks: {}", run.case, run.ticks, run.detail))
            .unwrap_or_else(|| "unknown failure".into());
        return Err(format!("input is not passing the supplied cases: {failure}"));
    };

    let design = extract(&original)?;
    let positions: Vec<Cell> = original.rooms.iter().map(|room| (room.x0, room.y0)).collect();
    let (width, height) = original.grid.footprint();
    let original_dim = width.max(height);
    let original_avg = average_ticks(&original_runs);
    eprintln!(
        "baseline: {} rooms, {} pipes, max-dim {}, score {:.3}, avg {:.1} ticks",
        design.rooms.len(),
        design.pipes.len(),
        original_dim,
        original_score,
        original_avg,
    );

    match route(&design, &positions, args.rounds) {
        Ok(_) => eprintln!("baseline room-only reconstruction routes successfully"),
        Err(error) => eprintln!(
            "warning: baseline room-only reconstruction did not reroute; translated candidates may still work: {error}"
        ),
    }

    let baseline_synthesis = Synthesis {
        source: source.clone(),
        program: original,
        labels: BTreeMap::new(),
        warnings: Vec::new(),
        report: Vec::new(),
    };
    let mut best = Evaluated {
        positions,
        synthesis: baseline_synthesis,
        score: original_score,
        max_dim: original_dim,
        avg_ticks: original_avg,
    };

    let mut routed = 0_u64;
    let mut route_failed = 0_u64;
    let mut first_route_error = None;
    let mut ambiguous = 0_u64;
    let mut judged = 0_u64;
    for pass in 0..args.passes {
        let mut improvement: Option<Evaluated> = None;
        for positions in band_moves(&best.positions) {
            if rooms_overlap(&design.rooms, &positions) {
                continue;
            }
            let synthesis = match route(&design, &positions, args.rounds) {
                Ok(synthesis) => synthesis,
                Err(error) => {
                    route_failed += 1;
                    first_route_error.get_or_insert(error);
                    continue;
                }
            };
            routed += 1;
            if synthesis.warnings.iter().any(|warning| warning.contains("AMBIGUOUS")) {
                ambiguous += 1;
                continue;
            }
            let max_dim = max_dim(&synthesis.program);
            if max_dim > best.max_dim {
                continue;
            }
            let mut runs = Vec::with_capacity(cases.len());
            for case in &cases {
                let result = run_case(&synthesis.program, case, args.max_ticks);
                let passed = result.passed;
                runs.push(result);
                if !passed {
                    break;
                }
            }
            judged += 1;
            let Some(candidate_score) = score(&synthesis.program, &runs, args.scoring.as_str())
            else {
                continue;
            };
            let candidate = Evaluated {
                positions,
                synthesis,
                score: candidate_score,
                max_dim,
                avg_ticks: average_ticks(&runs),
            };
            let reference = improvement.as_ref().unwrap_or(&best);
            if objective(&candidate) < objective(reference) {
                improvement = Some(candidate);
            }
        }

        let Some(next) = improvement else {
            eprintln!("pass {}: no improving band translation", pass + 1);
            break;
        };
        eprintln!(
            "pass {}: max-dim {} -> {}, score {:.3} -> {:.3}, avg {:.1} ticks",
            pass + 1,
            best.max_dim,
            next.max_dim,
            best.score,
            next.score,
            next.avg_ticks,
        );
        best = next;
    }

    if objective(&best) >= (original_dim, ordered_score(original_score)) {
        eprintln!(
            "no improvement ({routed} routed, {route_failed} unroutable, {ambiguous} ambiguous and {judged} judged candidates)"
        );
        if let Some(error) = first_route_error {
            eprintln!("first routing failure: {error}");
        }
        return Ok(());
    }
    if let Some(parent) = args.output.parent()
        && !parent.as_os_str().is_empty()
    {
        fs::create_dir_all(parent)
            .map_err(|error| format!("create {}: {error}", parent.display()))?;
    }
    fs::write(&args.output, &best.synthesis.source)
        .map_err(|error| format!("write {}: {error}", args.output.display()))?;
    println!(
        "wrote {}: max-dim {} -> {}, score {:.3} -> {:.3}, avg ticks {:.1} -> {:.1} \
         ({routed} routed, {route_failed} unroutable, {ambiguous} ambiguous, {judged} judged)",
        args.output.display(),
        original_dim,
        best.max_dim,
        original_score,
        best.score,
        original_avg,
        best.avg_ticks,
    );
    Ok(())
}

fn read(path: &Path) -> Result<String, String> {
    fs::read_to_string(path).map_err(|error| format!("read {}: {error}", path.display()))
}

fn extract(program: &Program) -> Result<Design, String> {
    let rooms = program
        .rooms
        .iter()
        .map(|room| RoomTemplate {
            width: room.x1 - room.x0 + 1,
            height: room.y1 - room.y0 + 1,
            cells: (room.y0..=room.y1)
                .map(|y| (room.x0..=room.x1).map(|x| program.grid.at(x, y)).collect())
                .collect(),
        })
        .collect();
    let pipes = program
        .pipes
        .iter()
        .enumerate()
        .map(|(index, pipe)| pipe_template(index, pipe, &program.rooms))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(Design { rooms, pipes })
}

fn pipe_template(index: usize, pipe: &Pipe, rooms: &[Room]) -> Result<PipeTemplate, String> {
    let src_index = pipe.src_room as usize;
    let dst_index = pipe.dst_room as usize;
    let src = rooms.get(src_index).ok_or_else(|| format!("pipe {index} has bad source room"))?;
    let dst =
        rooms.get(dst_index).ok_or_else(|| format!("pipe {index} has bad destination room"))?;
    let source = pipe.source();
    let dest = pipe.dest();
    let source_direction = attachment_direction(src, source).ok_or_else(|| {
        format!("pipe {index} source {source:?} is not immediately outside its room")
    })?;
    if attachment_direction(dst, dest).is_none() {
        return Err(format!(
            "pipe {index} destination {dest:?} is not immediately outside its room"
        ));
    }
    Ok(PipeTemplate {
        label: format!("pipe-{index}"),
        from: Endpoint {
            room: src_index,
            offset: (source.0 - src.x0, source.1 - src.y0),
            direction: source_direction,
            outgoing: true,
        },
        to: Endpoint {
            room: dst_index,
            offset: (dest.0 - dst.x0, dest.1 - dst.y0),
            direction: pipe.entry_dir,
            outgoing: false,
        },
        min_length: pipe.cells.len(),
    })
}

fn attachment_direction(room: &Room, cell: Cell) -> Option<u8> {
    if cell.0 == room.x1 + 1 && (room.y0..=room.y1).contains(&cell.1) {
        return Some(0);
    }
    if cell.1 == room.y1 + 1 && (room.x0..=room.x1).contains(&cell.0) {
        return Some(1);
    }
    if cell.0 == room.x0 - 1 && (room.y0..=room.y1).contains(&cell.1) {
        return Some(2);
    }
    if cell.1 == room.y0 - 1 && (room.x0..=room.x1).contains(&cell.0) {
        return Some(3);
    }
    None
}

fn route(design: &Design, positions: &[Cell], rounds: usize) -> Result<Synthesis, String> {
    let (grid, markers) = candidate_grid(design, positions)?;
    let minimums = design.pipes.iter().map(|pipe| (pipe.label.clone(), pipe.min_length)).collect();
    synthesise_markers_negotiated(&grid, &markers, &BTreeSet::new(), &minimums, rounds)
        .map_err(|error| error.to_string())
}

fn candidate_grid(design: &Design, positions: &[Cell]) -> Result<(Grid, Vec<Marker>), String> {
    let mut marker_cells = Vec::with_capacity(design.pipes.len() * 2);
    for pipe in &design.pipes {
        marker_cells.push(endpoint_cell(&pipe.from, positions));
        marker_cells.push(endpoint_cell(&pipe.to, positions));
    }
    let min_x = positions
        .iter()
        .map(|cell| cell.0)
        .chain(marker_cells.iter().map(|cell| cell.0))
        .min()
        .unwrap_or(0);
    let min_y = positions
        .iter()
        .map(|cell| cell.1)
        .chain(marker_cells.iter().map(|cell| cell.1))
        .min()
        .unwrap_or(0);
    let max_x = design
        .rooms
        .iter()
        .zip(positions)
        .map(|(room, pos)| pos.0 + room.width - 1)
        .chain(marker_cells.iter().map(|cell| cell.0))
        .max()
        .unwrap_or(0);
    let max_y = design
        .rooms
        .iter()
        .zip(positions)
        .map(|(room, pos)| pos.1 + room.height - 1)
        .chain(marker_cells.iter().map(|cell| cell.1))
        .max()
        .unwrap_or(0);
    let mut rows = vec![vec![b' '; (max_x - min_x + 1) as usize]; (max_y - min_y + 1) as usize];
    for (room, &(x, y)) in design.rooms.iter().zip(positions) {
        for (dy, source_row) in room.cells.iter().enumerate() {
            for (dx, &cell) in source_row.iter().enumerate() {
                let target = &mut rows[(y - min_y) as usize + dy][(x - min_x) as usize + dx];
                if *target != b' ' && cell != b' ' {
                    return Err("translated rooms overlap".into());
                }
                if cell != b' ' {
                    *target = cell;
                }
            }
        }
    }
    let text = rows
        .iter()
        .map(|row| String::from_utf8_lossy(row).trim_end().to_string())
        .collect::<Vec<_>>()
        .join("\n");
    let mut markers = Vec::with_capacity(design.pipes.len() * 2);
    for pipe in &design.pipes {
        for endpoint in [&pipe.from, &pipe.to] {
            let cell = endpoint_cell(endpoint, positions);
            markers.push(Marker {
                cell: (cell.0 - min_x, cell.1 - min_y),
                label: pipe.label.clone(),
                room: endpoint.room as u32,
                direction: endpoint.direction,
                outgoing: endpoint.outgoing,
                legacy: false,
            });
        }
    }
    Ok((Grid::parse(&text), markers))
}

fn endpoint_cell(endpoint: &Endpoint, positions: &[Cell]) -> Cell {
    let room = positions[endpoint.room];
    (room.0 + endpoint.offset.0, room.1 + endpoint.offset.1)
}

fn rooms_overlap(rooms: &[RoomTemplate], positions: &[Cell]) -> bool {
    for first in 0..rooms.len() {
        let a0 = positions[first];
        let a1 = (a0.0 + rooms[first].width - 1, a0.1 + rooms[first].height - 1);
        for second in first + 1..rooms.len() {
            let b0 = positions[second];
            let b1 = (b0.0 + rooms[second].width - 1, b0.1 + rooms[second].height - 1);
            if a0.0 <= b1.0 && b0.0 <= a1.0 && a0.1 <= b1.1 && b0.1 <= a1.1 {
                return true;
            }
        }
    }
    false
}

fn band_moves(positions: &[Cell]) -> Vec<Vec<Cell>> {
    let mut moves = Vec::new();
    for axis in 0..2 {
        let mut cuts: Vec<i32> =
            positions.iter().map(|pos| if axis == 0 { pos.0 } else { pos.1 }).collect();
        cuts.sort_unstable();
        cuts.dedup();
        for cut in cuts.into_iter().skip(1) {
            let mut candidate = positions.to_vec();
            for pos in &mut candidate {
                let coordinate = if axis == 0 { &mut pos.0 } else { &mut pos.1 };
                if *coordinate >= cut {
                    *coordinate -= 1;
                }
            }
            moves.push(candidate);
        }
    }
    moves
}

fn max_dim(program: &Program) -> i32 {
    let (width, height) = program.grid.footprint();
    width.max(height)
}

fn average_ticks(runs: &[littleman::RunResult]) -> f64 {
    runs.iter().map(|run| run.ticks).sum::<u64>() as f64 / runs.len() as f64
}

fn objective(candidate: &Evaluated) -> (i32, u64) {
    (candidate.max_dim, ordered_score(candidate.score))
}

fn ordered_score(value: f64) -> u64 {
    debug_assert!(value.is_finite() && value >= 0.0);
    value.to_bits()
}

#[cfg(test)]
mod tests {
    use super::*;
    use littleman::model::RoomKind;

    #[test]
    fn identifies_all_four_attachment_sides() {
        let room = Room::new(2, 3, 6, 8, RoomKind::Room);
        assert_eq!(attachment_direction(&room, (7, 5)), Some(0));
        assert_eq!(attachment_direction(&room, (4, 9)), Some(1));
        assert_eq!(attachment_direction(&room, (1, 5)), Some(2));
        assert_eq!(attachment_direction(&room, (4, 2)), Some(3));
        assert_eq!(attachment_direction(&room, (8, 5)), None);
    }

    #[test]
    fn translates_every_room_on_the_far_side_of_a_cut() {
        let positions = vec![(0, 0), (5, 2), (9, 2)];
        let moves = band_moves(&positions);
        assert!(moves.contains(&vec![(0, 0), (4, 2), (8, 2)]));
        assert!(moves.contains(&vec![(0, 0), (5, 2), (8, 2)]));
    }

    #[test]
    fn detects_border_overlap() {
        let rooms = vec![
            RoomTemplate { width: 3, height: 3, cells: Vec::new() },
            RoomTemplate { width: 3, height: 3, cells: Vec::new() },
        ];
        assert!(rooms_overlap(&rooms, &[(0, 0), (2, 2)]));
        assert!(!rooms_overlap(&rooms, &[(0, 0), (3, 0)]));
    }
}
