//! The `.eman.toml` netlist: room instances wired by named ports.
//!
//! ```toml
//! problem = "sudoku-validity"
//!
//! [rooms]
//! loader = "loader"                                   # all library variants allowed
//! tail   = { type = "shuttle", variants = ["vertical-first"] }
//!
//! [[pipes]]
//! from = "loader.out"
//! to   = "tail.feed"
//! min  = 17
//! max  = 24
//! ```
//!
//! `min` is a floor on the routed length and `max` an optional ceiling. Both are in routed pipe
//! cells, the unit `lmp` reports and the unit `--pipe-length` uses. A pipe with no `max` is
//! unbounded, which is what every design got before the field existed.
//!
//! Pipes are identified by their endpoints, never by letters, so a design can hold any number of
//! them. Every port of every instance must be wired exactly once — an unwired port is a marker
//! with no pipe, which is a mis-binding waiting to happen.

use std::collections::BTreeMap;
use std::path::Path;

use serde::Deserialize;

use crate::PackError;
use crate::library::Library;

#[derive(Debug, Clone)]
pub struct Instance {
    pub name: String,
    pub type_name: String,
    /// Indices into the room type's variant list the packer may choose between.
    pub allowed: Vec<usize>,
}

/// One end of a pipe: (instance index, port name).
pub type End = (usize, String);

#[derive(Debug, Clone)]
pub struct PipeSpec {
    /// Stable id used as the router label and the `min_lengths` key.
    pub id: String,
    pub from: End,
    pub to: End,
    pub min: usize,
    /// Ceiling on the routed length, in the same cells as [`PipeSpec::min`]. `None` is unbounded
    /// — the default, and bit-for-bit the behaviour of every design written before the field.
    ///
    /// A bound exists because pipe length is semantically load-bearing: the LM-75 display applies
    /// ADDR before DATA within a tick, so `snake` needs `len(ADDR) <= len(DATA) + send_gap`. The
    /// router only ever lengthens a pipe (to meet `min`), so this is checked after routing and a
    /// candidate that exceeds it is rejected, never silently accepted at the wrong length.
    pub max: Option<usize>,
}

#[derive(Debug, Clone)]
pub struct Design {
    pub problem: Option<String>,
    pub instances: Vec<Instance>,
    pub pipes: Vec<PipeSpec>,
}

impl Design {
    pub fn instance(&self, name: &str) -> Option<usize> {
        self.instances.iter().position(|i| i.name == name)
    }
}

#[derive(Deserialize)]
struct DesignFile {
    #[serde(default)]
    problem: Option<String>,
    rooms: BTreeMap<String, RoomDecl>,
    #[serde(default)]
    pipes: Vec<PipeDecl>,
}

#[derive(Deserialize)]
#[serde(untagged)]
enum RoomDecl {
    Type(String),
    Full {
        #[serde(rename = "type")]
        type_name: String,
        #[serde(default)]
        variants: Option<Vec<String>>,
    },
}

/// `deny_unknown_fields` because a mistyped bound that is silently ignored is exactly the failure
/// this field exists to remove — `mak = 12` must be an error, not an unbounded pipe.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct PipeDecl {
    from: String,
    to: String,
    #[serde(default)]
    min: Option<usize>,
    #[serde(default)]
    max: Option<usize>,
}

pub fn load_design(path: &Path, library: &Library) -> Result<Design, PackError> {
    let raw = std::fs::read_to_string(path)
        .map_err(|e| PackError(format!("cannot read {}: {e}", path.display())))?;
    let file: DesignFile =
        toml::from_str(&raw).map_err(|e| PackError(format!("{}: {e}", path.display())))?;
    let at = |detail: String| PackError(format!("{}: {detail}", path.display()));

    let mut instances = Vec::new();
    for (name, decl) in &file.rooms {
        instances.push(resolve_instance(name, decl, library, &at)?);
    }
    let design = Design { problem: file.problem, instances, pipes: Vec::new() };

    let mut pipes = Vec::new();
    let mut used: BTreeMap<(usize, String), String> = BTreeMap::new();
    for decl in &file.pipes {
        let pipe = resolve_pipe(decl, &design, library, &at)?;
        for (end, want_out) in [(&pipe.from, true), (&pipe.to, false)] {
            let _ = want_out;
            if let Some(other) = used.insert(end.clone(), pipe.id.clone()) {
                return Err(at(format!(
                    "port '{}.{}' is wired by both '{other}' and '{}' — every port carries exactly \
                     one pipe",
                    design.instances[end.0].name, end.1, pipe.id
                )));
            }
        }
        pipes.push(pipe);
    }

    for instance in &design.instances {
        let index = design.instance(&instance.name).expect("just built");
        let room = &library.types[&instance.type_name];
        let unwired: Vec<&str> = room
            .ports
            .keys()
            .filter(|port| !used.contains_key(&(index, (*port).clone())))
            .map(String::as_str)
            .collect();
        if !unwired.is_empty() {
            return Err(at(format!(
                "instance '{}' (type '{}') leaves port(s) {} unwired — every port of every \
                 instance must carry exactly one pipe",
                instance.name,
                instance.type_name,
                unwired.join(", ")
            )));
        }
    }
    if pipes.is_empty() {
        return Err(at("the [[pipes]] list is empty — nothing connects the rooms".into()));
    }
    Ok(Design { pipes, ..design })
}

fn resolve_instance(
    name: &str,
    decl: &RoomDecl,
    library: &Library,
    at: &dyn Fn(String) -> PackError,
) -> Result<Instance, PackError> {
    let (type_name, wanted) = match decl {
        RoomDecl::Type(type_name) => (type_name.clone(), None),
        RoomDecl::Full { type_name, variants } => (type_name.clone(), variants.clone()),
    };
    let Some(room) = library.types.get(&type_name) else {
        let known: Vec<&str> = library.types.keys().map(String::as_str).collect();
        return Err(at(format!(
            "instance '{name}': unknown room type '{type_name}' — the library holds: {}",
            known.join(", ")
        )));
    };
    let allowed = match wanted {
        None => (0..room.variants.len()).collect(),
        Some(names) => {
            let mut allowed = Vec::new();
            for variant in &names {
                let Some(index) = room.variant(variant) else {
                    let known: Vec<&str> = room.variants.iter().map(|v| v.name.as_str()).collect();
                    return Err(at(format!(
                        "instance '{name}': room type '{type_name}' has no variant '{variant}' — \
                         it holds: {}",
                        known.join(", ")
                    )));
                };
                allowed.push(index);
            }
            allowed
        }
    };
    if allowed.is_empty() {
        return Err(at(format!("instance '{name}': the variants list is empty")));
    }
    Ok(Instance { name: name.to_string(), type_name, allowed })
}

fn resolve_pipe(
    decl: &PipeDecl,
    design: &Design,
    library: &Library,
    at: &dyn Fn(String) -> PackError,
) -> Result<PipeSpec, PackError> {
    let from = resolve_end(&decl.from, true, design, library, at)?;
    let to = resolve_end(&decl.to, false, design, library, at)?;
    let id = format!(
        "{}.{}>{}.{}",
        design.instances[from.0].name, from.1, design.instances[to.0].name, to.1
    );
    // The floor the router actually enforces, not the number written down: a pipe is two cells
    // even when nobody says so, and `max` is compared against the same reality.
    let min = decl.min.unwrap_or(2).max(2);
    if let Some(max) = decl.max
        && max < min
    {
        return Err(at(format!(
            "pipe '{id}': max = {max} is below min = {min} — no route can satisfy both (min \
             defaults to 2 cells, the shortest pipe there is)"
        )));
    }
    Ok(PipeSpec { id, from, to, min, max: decl.max })
}

fn resolve_end(
    text: &str,
    outgoing: bool,
    design: &Design,
    library: &Library,
    at: &dyn Fn(String) -> PackError,
) -> Result<End, PackError> {
    let side = if outgoing { "from" } else { "to" };
    let Some((instance_name, port_name)) = text.split_once('.') else {
        return Err(at(format!("{side} = {text:?}: expected \"instance.port\"")));
    };
    let Some(index) = design.instance(instance_name) else {
        return Err(at(format!("{side} = {text:?}: no instance named '{instance_name}'")));
    };
    let room = &library.types[&design.instances[index].type_name];
    let Some(port) = room.ports.get(port_name) else {
        let known: Vec<&str> = room.ports.keys().map(String::as_str).collect();
        return Err(at(format!(
            "{side} = {text:?}: room type '{}' has no port '{port_name}' — it has: {}",
            room.name,
            known.join(", ")
        )));
    };
    if port.outgoing != outgoing {
        return Err(at(format!(
            "{side} = {text:?}: port '{port_name}' is {} — a pipe runs from an outgoing port to \
             an incoming one",
            if port.outgoing { "outgoing (a FROM end)" } else { "incoming (a TO end)" }
        )));
    }
    Ok((index, port_name.to_string()))
}

#[cfg(test)]
mod tests {
    use std::sync::atomic::{AtomicUsize, Ordering};

    use super::*;

    /// The real library — the netlist parser resolves types, ports and directions against it, so
    /// a fake one would only test the fake.
    fn library() -> Library {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../rooms");
        crate::library::load_library(&root).expect("the repo rooms/ library loads")
    }

    /// `input.out -> output.feed` and nothing else: the smallest netlist that wires every port.
    fn parse(pipe_extra: &str) -> Result<Design, PackError> {
        static COUNT: AtomicUsize = AtomicUsize::new(0);
        let text = format!(
            "problem = \"triangle\"\n\n[rooms]\nsrc = \"input\"\nsink = \"output\"\n\n\
             [[pipes]]\nfrom = \"src.out\"\nto = \"sink.feed\"\n{pipe_extra}"
        );
        let path = std::env::temp_dir().join(format!(
            "lmp-design-{}-{}.eman.toml",
            std::process::id(),
            COUNT.fetch_add(1, Ordering::Relaxed)
        ));
        std::fs::write(&path, text).expect("write the temp netlist");
        let design = load_design(&path, &library());
        let _ = std::fs::remove_file(&path);
        design
    }

    #[test]
    fn no_max_is_unbounded() {
        let design = parse("").expect("loads");
        assert_eq!(design.pipes[0].min, 2);
        assert_eq!(design.pipes[0].max, None, "a pipe without `max` must stay unbounded");
    }

    #[test]
    fn max_is_read() {
        let design = parse("min = 6\nmax = 9\n").expect("loads");
        assert_eq!(design.pipes[0].min, 6);
        assert_eq!(design.pipes[0].max, Some(9));
    }

    #[test]
    fn max_alone_is_read() {
        let design = parse("max = 4\n").expect("loads");
        assert_eq!((design.pipes[0].min, design.pipes[0].max), (2, Some(4)));
    }

    #[test]
    fn max_below_min_is_rejected() {
        let error = parse("min = 9\nmax = 6\n").expect_err("cannot satisfy both");
        assert!(error.0.contains("src.out>sink.feed"), "{error}");
        assert!(error.0.contains("max = 6"), "{error}");
        assert!(error.0.contains("min = 9"), "{error}");
    }

    /// `min` floors at 2, so `max = 1` is below the floor even with no `min` written down.
    #[test]
    fn max_below_the_implicit_minimum_is_rejected() {
        let error = parse("max = 1\n").expect_err("no pipe is one cell long");
        assert!(error.0.contains("min = 2"), "{error}");
    }

    #[test]
    fn a_mistyped_bound_is_an_error_not_an_unbounded_pipe() {
        let error = parse("mak = 6\n").expect_err("unknown key");
        assert!(error.0.contains("mak"), "{error}");
    }
}
