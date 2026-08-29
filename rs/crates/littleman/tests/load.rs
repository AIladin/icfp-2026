//! Structural rules: rooms, pipes, literals, and the load errors that cost a submission.
//!
//! A port of `py/libs/runner/tests/test_load.py`.

mod common;

use common::{THREE_PORT_DISPLAY, one_room, program};
use littleman::{EAST, NORTH, Op, Program, RoomKind, SOUTH, WEST, load_program};

const HELLO: &str = "\
+----+    +-+
|@3sH|>-->|O|
+----+    +-+";

/// The op a cell resolves to when walked in one direction.
fn op(program: &Program, x: i32, y: i32, dir: u8) -> Op {
    program.ops[program.index(x, y)][dir as usize]
}

fn error_of(source: &str) -> String {
    load_program(source).err().expect("should not load").to_string()
}

#[test]
fn rooms_pipes_and_io_are_found() {
    let program = program(HELLO);
    let kinds: Vec<RoomKind> = program.rooms.iter().map(|room| room.kind).collect();
    assert_eq!(kinds, vec![RoomKind::Room, RoomKind::Output]);
    assert_eq!(program.rooms[0].spawn, Some((1, 1)));
    assert_eq!(program.pipes.len(), 1);
    let pipe = &program.pipes[0];
    assert_eq!(pipe.source(), (6, 1));
    assert_eq!(pipe.dest(), (9, 1));
    assert_eq!(pipe.cells.len(), 4);
    assert_eq!(program.output_pipe, Some(0));
    assert_eq!(program.input_pipe, None);
}

#[test]
fn footprint_is_the_bounding_box_squared() {
    // 13 wide, 3 tall: max(w, h)² = 169, not w × h.
    assert_eq!(program(HELLO).footprint(), 169);
}

#[test]
fn pipe_bends_at_arrowheads() {
    // The terminal arrowhead doubles as the final bend — no extra bend arrow before it.
    let source = "     +-+
     |O|
     +-+
+---+ ^
|@sH|>^
+---+";
    let program = program(source);
    assert_eq!(program.pipes.len(), 1);
    assert_eq!(program.pipes[0].cells, vec![(5, 4), (6, 4), (6, 3)]);
    // The arrowhead points north even though the last hop ran east.
    assert_eq!(program.pipes[0].entry_dir, NORTH);
    assert_eq!(program.pipes[0].entry(), (6, 2));
}

#[test]
fn the_side_a_pipe_lands_on_is_the_port() {
    let program = program(THREE_PORT_DISPLAY);
    assert_eq!(program.displays.len(), 1);
    let display = &program.displays[0];
    assert_eq!((display.width, display.height), (3, 1));
    assert_eq!(program.rooms[display.room as usize].kind, RoomKind::Display);
    // Pipes are numbered in reading order of their first cell: ADDR (7,3), DATA (4,6), SWAP (7,9).
    assert_eq!((display.addr, display.data, display.swap), (Some(0), Some(1), Some(2)));
    let names: Vec<&str> = display.ports().map(|(port, _)| port.as_str()).collect();
    assert_eq!(names, vec!["ADDR", "DATA", "SWAP"]);
}

#[test]
fn a_display_holds_no_little_man_and_no_walkable_cells() {
    let program = program(THREE_PORT_DISPLAY);
    // Three men, all in ordinary rooms; the display's interior is not somewhere a man can step.
    assert_eq!(program.spawns.len(), 3);
    assert_eq!(program.room_of[program.index(7, 6)], Program::NO_ROOM);
    assert_eq!(op(&program, 7, 6, EAST), Op::Nop);
}

#[test]
fn display_load_errors() {
    // A pipe into the right-hand wall — that side takes no pipe.
    assert!(error_of("+==+  +--+\n:  :<<|@ |\n+==+  +--+").contains("right side"));
    // A pipe into the top-right corner.
    assert!(error_of("+==+<<+--+\n:  :  |@ |\n+==+  +--+").contains("corner"));
    // Two rooms both feeding the left-hand wall: two DATA pipes.
    let two_data = "\
+--+  +====+
|@ |>>:    :
+--+  :    :
      :    :
+--+  :    :
|@ |>>:    :
+--+  +====+";
    assert!(error_of(two_data).contains("two pipes attach to the DATA side"));
    // A display only ever consumes, so a pipe leaving one carries nothing.
    assert!(error_of("+==+  +--+\n:  :>>|@ |\n+==+  +--+").contains("flows out of the display"));
    assert!(error_of("+==+\n:@ :\n+==+").contains("driven by pipes, not by a man"));

    let wide = format!("+{0}+\n:{1}:\n+{0}+", "=".repeat(65), " ".repeat(65));
    assert!(error_of(&wide).contains("caps at 64x64"));
}

#[test]
fn pipe_traps() {
    let trap = |pipe: &str| error_of(&format!("+---+     +-+\n|@sH|{pipe}|O|\n+---+     +-+"));
    // Body running into the wall: end with an arrowhead pointing into the room.
    assert!(trap(">----").contains("body glyph into the wall"));
    // An arrowhead pointing back along the flow.
    assert!(trap(">--<>").contains("back along the flow"));
    // A wrong body glyph is a load error, not a bend.
    assert!(trap(">-|->").contains("expected an arrowhead"));
}

#[test]
fn single_cell_pipe_is_a_load_error() {
    assert!(error_of("+---+ +-+\n|@sH|>|O|\n+---+ +-+").contains("at least 2"));
}

#[test]
fn two_men_in_one_room() {
    assert!(error_of("+----+\n|@  @|\n+----+").contains("multiple '@'"));
}

#[test]
fn man_outside_a_room() {
    assert!(error_of("+----+\n|    |\n+----+\n@").contains("not inside a room"));
}

#[test]
fn two_pipes_on_the_output_room() {
    let source = "\
+---+     +-+     +---+
|@sH|>--->|O|<---<|Hs@|
+---+     +-+     +---+";
    assert!(error_of(source).contains("more than one pipe"));
}

#[test]
fn literals_load_in_both_directions() {
    let program = program(&one_room("`123`"));
    // `@` is at x=1, so the literal spans x=2..6 and closes at x=6 walked east, x=2 walked west.
    assert_eq!(op(&program, 6, 1, EAST), Op::Load(123));
    assert_eq!(op(&program, 2, 1, WEST), Op::Load(321));
    // A digit inside a literal is not a single-digit load along that axis, but is across it.
    assert_eq!(op(&program, 3, 1, EAST), Op::Nop);
    assert_eq!(op(&program, 3, 1, SOUTH), Op::Load(1));
}

#[test]
fn literal_ignores_spaces() {
    assert_eq!(op(&program(&one_room("`1 2 3`")), 8, 1, EAST), Op::Load(123));
}

#[test]
fn literal_must_fit_64_bits_in_both_directions() {
    assert!(error_of(&one_room("`9999999999999999999`")).contains("64 bits"));
}

#[test]
fn unmatched_backtick() {
    assert!(error_of(&one_room("`12")).contains("unmatched backtick"));
}

#[test]
fn a_bad_span_between_backticks_is_an_error_on_the_other_axis_too() {
    // Server-confirmed 2026-07-25 from `history-lesson`: both backticks here pair *horizontally*,
    // and the column still fails. Pairing on one axis does not excuse the other.
    let source = "\
+-------+
|@`72`s |
| s`72`s|
| `72`s |
+-------+";
    assert!(error_of(source).contains("expected a digit or a space between backticks"));
}

#[test]
fn backticks_in_different_rooms_never_pair() {
    // Server-confirmed 2026-07-25: a backtick in one room and one in another, with walls between,
    // is fine — a literal belongs to a room and cannot straddle a wall.
    let source = "\
+-----+
|@`7`v|
+-----+
+-----+
|@`7`v|
+-----+";
    assert!(load_program(source).is_ok());
}

#[test]
fn crossing_literals_share_a_backtick() {
    // A corner backtick opens a horizontal and a vertical literal at once.
    let source = "\
+-----+
|@`12`|
|    3|
|    4|
|    `|
+-----+";
    let program = program(source);
    assert_eq!(op(&program, 5, 1, EAST), Op::Load(12)); // east, closing at (5,1)
    assert_eq!(op(&program, 2, 1, WEST), Op::Load(21)); // west, closing at (2,1)
    assert_eq!(op(&program, 5, 4, SOUTH), Op::Load(34)); // south, closing at (5,4)
    assert_eq!(op(&program, 5, 1, NORTH), Op::Load(43)); // north, at the shared corner
}

#[test]
fn nearest_pipe_is_resolved_per_cell() {
    // `s` targets the pipe nearest the instruction — moving it one cell can retarget it.
    let layout = |send_at_left: bool| {
        let body = if send_at_left { "|@s   |" } else { "|@   s|" };
        format!("+---+\n|   |\n+---+\n  ^\n  ^\n+-----+    +-+\n{body}>-->|O|\n+-----+    +-+")
    };

    let left = program(&layout(true));
    let right = program(&layout(false));
    assert_eq!(left.pipes.len(), 2);
    let up = left.pipes.iter().position(|pipe| pipe.source() == (2, 4)).expect("an upward pipe");
    let sideways = 1 - up;

    // `s` at x=2 is nearest the pipe leaving upward; at x=5 it is nearest the one going right.
    assert_eq!(op(&left, 2, 6, EAST), Op::Send(up as u32));
    assert_eq!(op(&right, 5, 6, EAST), Op::Send(sideways as u32));
}
