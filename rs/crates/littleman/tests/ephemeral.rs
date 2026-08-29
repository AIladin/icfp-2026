//! Ephemeral pipes: a design marked with letter pairs must synthesise the grid `lm` synthesises.
//!
//! A port of the parts of `py/libs/runner/tests/test_ephemeral.py` that pin behaviour rather than
//! wording. The full message-for-message comparison is `test_parity.py`, which runs both routers
//! over the same designs.

use std::collections::BTreeMap;

use littleman::ephemeral::{self, EphemeralError, Synthesis, synthesise};
use littleman::{load_program, run_free};

fn no_lengths() -> BTreeMap<String, usize> {
    BTreeMap::new()
}

fn routed(source: &str) -> Synthesis {
    synthesise(source, &no_lengths()).unwrap_or_else(|error| panic!("should route: {error}"))
}

fn refused(source: &str) -> EphemeralError {
    synthesise(source, &no_lengths()).err().expect("should refuse")
}

/// Two relay rooms between I and O, each doubling the value it receives. Every pipe is 2 cells, so
/// the marked version below synthesises to exactly this grid.
const ROUTED: &str = "+-+
|I|
+-+
 v
 v
+------+
|>@rM+v|
|^.H.s<|
+------+
 v
 v
+-+
|O|
+-+";

const MARKED: &str = "+-+
|I|
+-+
 a

 A
+------+
|>@rM+v|
|^.H.s<|
+------+
 c

 C
+-+
|O|
+-+";

fn normalise(source: &str) -> String {
    source.trim_matches('\n').lines().map(str::trim_end).collect::<Vec<_>>().join("\n")
}

#[test]
fn letter_pairs_synthesise_the_routed_grid() {
    // Three cells rather than two: the marker's own cell plus the gap it was drawn across.
    let expected = normalise(ROUTED).replace(" v\n v\n", " v\n |\n v\n");
    assert_eq!(normalise(&routed(MARKED).source), normalise(&expected));
}

#[test]
fn letter_pairs_run_identically_to_the_routed_program() {
    let synthesised = routed(MARKED);
    let hand = load_program(&normalise(ROUTED).replace(" v\n v\n", " v\n |\n v\n"))
        .expect("hand-drawn grid should load");
    let from_markers = run_free(&synthesised.program, vec![3, 7], 10_000);
    let from_hand = run_free(&hand, vec![3, 7], 10_000);
    assert_eq!(from_markers.output, from_hand.output);
    assert_eq!(from_markers.ticks, from_hand.ticks);
}

#[test]
fn pipes_carry_their_labels() {
    let result = routed(MARKED);
    assert_eq!(result.labels.values().cloned().collect::<Vec<_>>(), vec!["a", "c"]);
}

#[test]
fn a_minimum_length_lengthens_the_route() {
    let lengths = BTreeMap::from([("a".to_string(), 6)]);
    let result = synthesise(MARKED, &lengths).expect("should route");
    let index = *result.labels.iter().find(|(_, label)| *label == "a").expect("pipe a").0;
    assert!(result.program.pipes[index].cells.len() >= 6);
}

#[test]
fn a_program_without_markers_says_so() {
    assert!(refused("+---+\n|@ H|\n+---+").0.contains("nothing to synthesise"));
}

#[test]
fn an_unpaired_marker_is_an_error() {
    let message = refused("+---+\n|@ H|\n+---+\n a").0;
    assert!(message.contains("exactly one of each"), "{message}");
}

#[test]
fn a_letter_off_the_wall_is_an_error() {
    let message = refused("+---+\n|@ H|\n+---+\n\n\n   z").0;
    assert!(message.contains("touches no room wall"), "{message}");
}

#[test]
fn v_and_uppercase_v_cannot_name_a_pipe() {
    let message = refused("+---+\n|@ H|\n+---+\n V\n\n v\n+---+\n|@ H|\n+---+").0;
    assert!(message.contains("RESERVED"), "{message}");
}

/// Four bands of a sprawl, three pipes each — the design the retry pool exists for.
fn sprawl() -> String {
    let bands = [["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"], ["j", "k", "l"]];
    let mut out = Vec::new();
    for band in bands {
        let up = band.map(str::to_uppercase);
        out.push("+--------------------+".to_string());
        out.push("|@                   |".to_string());
        out.push("+--------------------+".to_string());
        out.push(format!("   {}    {}      {}", band[0], band[1], band[2]));
        out.extend(["".to_string(), "".to_string(), "".to_string()]);
        out.push(format!("          {}      {}", up[0], up[1]));
        out.push("  +---+  +---+  +---+".to_string());
        out.push(format!("  |@ H|  |@ H|  |@ H|{}", up[2]));
        out.push("  +---+  +---+  +---+".to_string());
        out.extend(["".to_string(), "".to_string()]);
    }
    out.join("\n")
}

#[test]
fn a_twelve_pipe_sprawl_routes() {
    let result = routed(&sprawl());
    assert_eq!(result.program.pipes.len(), 12);
    let mut labels: Vec<String> = result.labels.values().cloned().collect();
    labels.sort();
    assert_eq!(labels, "abcdefghijkl".chars().map(String::from).collect::<Vec<_>>());
    load_program(&result.source).expect("the synthesised grid must load");
}

#[test]
fn every_pipe_keeps_its_own_exit_cell() {
    let result = routed(&sprawl());
    let seconds: Vec<_> = result.program.pipes.iter().map(|pipe| pipe.cells[1]).collect();
    let unique: std::collections::HashSet<_> = seconds.iter().collect();
    assert_eq!(unique.len(), seconds.len());
}

// ---------------------------------------------------------------------------------- the retry order

/// The cross-language contract. These are the same fixtures `test_ephemeral.py` pins, and the two
/// must never drift — see `docs/vault/heap/The retry order is a specification, not a shuffle.md`.
const XORSHIFT_CHAIN: [u64; 6] = [
    21903399195127931,
    1084646099022742235,
    17201177773494424350,
    8549851669132419384,
    16403554352028563834,
    972527648881529992,
];

#[test]
fn the_generator_is_pinned() {
    let mut state = ephemeral::SEED;
    let chain: Vec<u64> = (0..XORSHIFT_CHAIN.len())
        .map(|_| {
            state = ephemeral::xorshift(state);
            state
        })
        .collect();
    assert_eq!(chain, XORSHIFT_CHAIN);
}

#[test]
fn a_design_routes_the_same_way_twice() {
    // Determinism at the level that matters: the same input must give the same grid, every run.
    let first = routed(&sprawl()).source;
    let second = routed(&sprawl()).source;
    assert_eq!(first, second);
}
