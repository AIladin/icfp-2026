//! The global room library: `rooms/<type>/interface.toml` + one `.room` file per variant.
//!
//! A room type's `interface.toml` is the contract every variant must satisfy: a `[ports]` table of
//! `name = "letter"`, where the letter's case encodes direction exactly as in the handoff
//! convention — lowercase is an outgoing FROM end, uppercase an incoming TO end. Letters are local
//! to the room type; two types may both use `a`. `v`/`V` stay reserved (the router draws `v`).
//!
//! A `.room` file is one room box with its port letters written on the cells immediately outside
//! the wall. Which wall and offset each letter sits on is precisely what varies between variants.

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::path::Path;

use littleman::grid::Grid;
use littleman::load::find_rooms;
use littleman::model::{Cell, DELTAS, EAST, NORTH, SOUTH, WEST};
use serde::Deserialize;

use crate::PackError;

pub const RESERVED: [u8; 2] = *b"vV";

/// Directions match `littleman::model`: 0 east, 1 south, 2 west, 3 north.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PortSpec {
    pub name: String,
    /// Lowercase form of the marker letter, whatever the case in the contract.
    pub letter: u8,
    pub outgoing: bool,
}

/// One pipe attachment of a variant: where the marker cell sits relative to the box origin.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Pin {
    /// Marker cell relative to the room box's top-left corner; one step outside the wall, so a
    /// coordinate may be -1, `width` or `height`.
    pub offset: Cell,
    /// Flow direction at the marker cell: away from the wall for FROM, into it for TO.
    pub direction: u8,
    pub outgoing: bool,
}

/// Which wall of its box a pin sits outside. The marker cell is one step out, so exactly one
/// coordinate leaves the box's range and that names the wall.
pub fn wall_of(pin: &Pin, width: i32) -> u8 {
    let (x, y) = pin.offset;
    if x < 0 {
        WEST
    } else if x >= width {
        EAST
    } else if y < 0 {
        NORTH
    } else {
        SOUTH
    }
}

#[derive(Debug, Clone)]
pub struct Variant {
    pub name: String,
    /// The room box only (walls inclusive), row-major bytes; markers are NOT part of it.
    pub rows: Vec<Vec<u8>>,
    pub width: i32,
    pub height: i32,
    pub pins: BTreeMap<String, Pin>,
    /// Minimum clearance the box needs on each wall, indexed by `littleman::model` direction. A
    /// wall carrying a pin needs 2 — the marker cell is one step out and its exit cell two, and
    /// `assemble::feasible` demands both be clear of every box. A bare wall still needs 1, because
    /// two room boxes sharing a border is not a grid the room finder can read.
    pub pad: [i32; 4],
    /// Binding intent: interior `s`/`r`/`q` cell (box-relative) -> the port it must resolve to.
    /// Placement-invariant: relative reading order survives translation.
    pub intent: Vec<(Cell, u8, String)>,
    pub is_input: bool,
    /// Not consulted yet; recorded so a later seed heuristic can pin the output room too.
    #[allow(dead_code)]
    pub is_output: bool,
    /// Interior cells that are not spaces — the occupied-cell count the report prints.
    pub occupied: usize,
}

#[derive(Debug, Clone)]
pub struct RoomType {
    pub name: String,
    /// From interface.toml; surfaced in `lmp --json` consumers and future reports.
    #[allow(dead_code)]
    pub description: String,
    pub ports: BTreeMap<String, PortSpec>,
    pub variants: Vec<Variant>,
}

impl RoomType {
    pub fn variant(&self, name: &str) -> Option<usize> {
        self.variants.iter().position(|v| v.name == name)
    }
}

#[derive(Debug, Clone, Default)]
pub struct Library {
    pub types: BTreeMap<String, RoomType>,
}

#[derive(Deserialize)]
struct InterfaceFile {
    #[serde(default)]
    description: String,
    ports: BTreeMap<String, String>,
}

/// Load every `rooms/<type>/` directory that holds an `interface.toml`.
pub fn load_library(root: &Path) -> Result<Library, PackError> {
    let mut types = BTreeMap::new();
    let entries = std::fs::read_dir(root)
        .map_err(|e| PackError(format!("cannot read rooms library {}: {e}", root.display())))?;
    let mut dirs: Vec<_> = entries.filter_map(|e| e.ok()).map(|e| e.path()).collect();
    dirs.sort();
    for dir in dirs {
        if !dir.is_dir() || !dir.join("interface.toml").exists() {
            continue;
        }
        let room = load_type(&dir)?;
        types.insert(room.name.clone(), room);
    }
    if types.is_empty() {
        return Err(PackError(format!(
            "the rooms library {} holds no <type>/interface.toml — nothing to instantiate",
            root.display()
        )));
    }
    Ok(Library { types })
}

fn load_type(dir: &Path) -> Result<RoomType, PackError> {
    let name = dir.file_name().unwrap_or_default().to_string_lossy().to_string();
    let raw = std::fs::read_to_string(dir.join("interface.toml"))
        .map_err(|e| PackError(format!("cannot read {}/interface.toml: {e}", dir.display())))?;
    let parsed: InterfaceFile = toml::from_str(&raw)
        .map_err(|e| PackError(format!("{}/interface.toml: {e}", dir.display())))?;
    let ports = parse_ports(&name, &parsed.ports)?;

    let mut variants = Vec::new();
    let mut files: Vec<_> = std::fs::read_dir(dir)
        .map_err(|e| PackError(format!("cannot list {}: {e}", dir.display())))?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|ext| ext == "room"))
        .collect();
    files.sort();
    for file in files {
        variants.push(load_variant(&name, &ports, &file)?);
    }
    if variants.is_empty() {
        return Err(PackError(format!(
            "room type '{name}' has an interface.toml but no .room variants in {}",
            dir.display()
        )));
    }
    Ok(RoomType { name, description: parsed.description, ports, variants })
}

fn parse_ports(
    room: &str,
    raw: &BTreeMap<String, String>,
) -> Result<BTreeMap<String, PortSpec>, PackError> {
    let mut ports = BTreeMap::new();
    let mut by_letter: BTreeMap<u8, String> = BTreeMap::new();
    for (name, letter) in raw {
        let [char] = letter.as_bytes() else {
            return Err(PackError(format!(
                "room type '{room}', port '{name}': the marker must be a single ASCII letter, got \
                 {letter:?}"
            )));
        };
        let char = *char;
        if !char.is_ascii_alphabetic() || RESERVED.contains(&char) {
            return Err(PackError(format!(
                "room type '{room}', port '{name}': '{}' cannot mark a pipe — markers are ASCII \
                 letters and 'v'/'V' are reserved for the router's arrowheads",
                char as char
            )));
        }
        let lower = char.to_ascii_lowercase();
        if let Some(other) = by_letter.insert(lower, name.clone()) {
            return Err(PackError(format!(
                "room type '{room}': ports '{other}' and '{name}' both use the letter '{}' — one \
                 letter names one port (its case only states the direction)",
                lower as char
            )));
        }
        ports.insert(
            name.clone(),
            PortSpec { name: name.clone(), letter: lower, outgoing: char.is_ascii_lowercase() },
        );
    }
    if ports.is_empty() {
        return Err(PackError(format!("room type '{room}': the [ports] table is empty")));
    }
    Ok(ports)
}

fn load_variant(
    room: &str,
    ports: &BTreeMap<String, PortSpec>,
    file: &Path,
) -> Result<Variant, PackError> {
    let name = file.file_stem().unwrap_or_default().to_string_lossy().to_string();
    let text = std::fs::read_to_string(file)
        .map_err(|e| PackError(format!("cannot read {}: {e}", file.display())))?;
    let at = |detail: String| PackError(format!("{room}/{name}.room: {detail}"));

    let grid = Grid::parse(&text);
    let boxes = find_rooms(&grid).map_err(|e| at(e.0))?;
    let [room_box] = boxes.as_slice() else {
        return Err(at(format!("expected exactly one room box, found {}", boxes.len())));
    };
    let (x0, y0, x1, y1) = (room_box.x0, room_box.y0, room_box.x1, room_box.y1);

    let pins = find_pins(room, ports, &grid, (x0, y0, x1, y1), &at)?;
    let mut rows = Vec::new();
    for y in y0..=y1 {
        rows.push((x0..=x1).map(|x| grid.at(x, y)).collect());
    }
    let intent = binding_intent(ports, &pins, &rows, &at)?;
    let interior: Vec<u8> =
        rows.iter().skip(1).take(rows.len() - 2).flat_map(|r| r[1..r.len() - 1].to_vec()).collect();
    let mut pad = [1i32; 4];
    for pin in pins.values() {
        pad[wall_of(pin, x1 - x0 + 1) as usize] = 2;
    }
    Ok(Variant {
        name,
        width: x1 - x0 + 1,
        height: y1 - y0 + 1,
        pad,
        occupied: interior.iter().filter(|&&c| c != b' ').count(),
        is_input: interior.contains(&b'I'),
        is_output: interior.contains(&b'O'),
        rows,
        pins,
        intent,
    })
}

fn find_pins(
    room: &str,
    ports: &BTreeMap<String, PortSpec>,
    grid: &Grid,
    (x0, y0, x1, y1): (i32, i32, i32, i32),
    at: &dyn Fn(String) -> PackError,
) -> Result<BTreeMap<String, Pin>, PackError> {
    let mut pins: BTreeMap<String, Pin> = BTreeMap::new();
    let mut stray = Vec::new();
    for y in 0..grid.height() {
        for x in 0..grid.width() {
            let inside = x0 <= x && x <= x1 && y0 <= y && y <= y1;
            let char = grid.at(x, y);
            if inside || !char.is_ascii_alphabetic() {
                continue;
            }
            if RESERVED.contains(&char) {
                return Err(at(format!(
                    "'{}' at ({x},{y}) outside the box — 'v'/'V' are reserved for the router",
                    char as char
                )));
            }
            match marker_of(ports, room, grid, (x, y), (x0, y0, x1, y1)) {
                Ok(Some((port, pin))) => {
                    if let Some(prior) = pins.insert(port.clone(), pin) {
                        let _ = prior;
                        return Err(at(format!(
                            "port '{port}' is marked twice — each port appears exactly once per \
                             variant"
                        )));
                    }
                }
                Ok(None) => stray.push((x, y, char)),
                Err(detail) => return Err(at(detail)),
            }
        }
    }
    if let Some(&(x, y, char)) = stray.first() {
        return Err(at(format!(
            "the letter '{}' at ({x},{y}) touches no wall of the room box — markers sit on the \
             cell immediately outside the border",
            char as char
        )));
    }
    let missing: Vec<&str> =
        ports.keys().filter(|p| !pins.contains_key(*p)).map(String::as_str).collect();
    if !missing.is_empty() {
        return Err(at(format!(
            "missing marker(s) for port(s): {} — the interface.toml contract lists every pipe the \
             variant must attach",
            missing.join(", ")
        )));
    }
    Ok(pins)
}

/// Resolve one letter outside the box: which port it marks and where its pipe attaches.
fn marker_of(
    ports: &BTreeMap<String, PortSpec>,
    room: &str,
    grid: &Grid,
    (x, y): Cell,
    (x0, y0, x1, y1): (i32, i32, i32, i32),
) -> Result<Option<(String, Pin)>, String> {
    let on_border = |cx: i32, cy: i32| {
        x0 <= cx
            && cx <= x1
            && y0 <= cy
            && cy <= y1
            && (cx == x0 || cx == x1 || cy == y0 || cy == y1)
    };
    let mut toward = None;
    for (direction, &(dx, dy)) in DELTAS.iter().enumerate() {
        if on_border(x + dx, y + dy) {
            toward = Some(direction as u8);
            break;
        }
    }
    let Some(toward_wall) = toward else { return Ok(None) };

    let char = grid.at(x, y);
    let outgoing = char.is_ascii_lowercase();
    let lower = char.to_ascii_lowercase();
    let Some(spec) = ports.values().find(|p| p.letter == lower) else {
        let known = ports.values().fold(String::new(), |mut acc, p| {
            let _ = write!(
                acc,
                "{}{}={}",
                if acc.is_empty() { "" } else { ", " },
                p.name,
                p.letter as char
            );
            acc
        });
        return Err(format!(
            "the marker '{}' at ({x},{y}) matches no port in interface.toml ({known}) — room type \
             '{room}' takes exactly those",
            char as char
        ));
    };
    if spec.outgoing != outgoing {
        let (want, got) = if spec.outgoing {
            (spec.letter as char, spec.letter.to_ascii_uppercase() as char)
        } else {
            (spec.letter.to_ascii_uppercase() as char, spec.letter as char)
        };
        return Err(format!(
            "the marker '{got}' at ({x},{y}) has the wrong case for port '{}' — the contract says \
             '{want}' ({}), and case is direction, not style",
            spec.name,
            if spec.outgoing {
                "outgoing, a pipe begins here"
            } else {
                "incoming, a pipe ends here"
            }
        ));
    }
    let direction = if outgoing { (toward_wall + 2) % 4 } else { toward_wall };
    Ok(Some((spec.name.clone(), Pin { offset: (x - x0, y - y0), direction, outgoing })))
}

/// For every `s`/`r`/`q` in the interior: the port it must bind to, by the loader's own rule
/// (Manhattan distance to the attached segment = the marker cell). An exact tie is refused here,
/// at library load — a tie is one repack away from a silently re-pointed send.
fn binding_intent(
    ports: &BTreeMap<String, PortSpec>,
    pins: &BTreeMap<String, Pin>,
    rows: &[Vec<u8>],
    at: &dyn Fn(String) -> PackError,
) -> Result<Vec<(Cell, u8, String)>, PackError> {
    let mut intent = Vec::new();
    for (y, row) in rows.iter().enumerate().skip(1).take(rows.len() - 2) {
        for (x, &char) in row.iter().enumerate().skip(1).take(row.len() - 2) {
            if !matches!(char, b's' | b'r' | b'q') {
                continue;
            }
            let outgoing = char == b's';
            let cell = (x as i32, y as i32);
            let mut ranked: Vec<(i32, (i32, i32), &String)> = pins
                .iter()
                .filter(|(port, _)| ports[*port].outgoing == outgoing)
                .map(|(port, pin)| {
                    let (px, py) = pin.offset;
                    ((px - cell.0).abs() + (py - cell.1).abs(), (py, px), port)
                })
                .collect();
            ranked.sort();
            match ranked.as_slice() {
                [] => {
                    return Err(at(format!(
                        "'{}' at box-relative ({},{}) has no {} port to bind to — it would be a \
                         no-pipe error at runtime",
                        char as char,
                        cell.0,
                        cell.1,
                        if outgoing { "outgoing" } else { "incoming" }
                    )));
                }
                [(_, _, port)] => intent.push((cell, char, (*port).clone())),
                [(d1, _, port), (d2, _, other), ..] => {
                    if d1 == d2 {
                        return Err(at(format!(
                            "'{}' at box-relative ({},{}) is {d1} cells from both port '{port}' \
                             and port '{other}' — an exact tie is one repack away from a silently \
                             re-pointed send; move a marker or the instruction one cell",
                            char as char, cell.0, cell.1
                        )));
                    }
                    intent.push((cell, char, (*port).clone()));
                }
            }
        }
    }
    Ok(intent)
}
