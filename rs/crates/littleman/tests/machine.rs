//! Instruction semantics: the edge cases that silently produce wrong output.
//!
//! A port of `py/libs/runner/tests/test_machine.py`.

mod common;

use common::{ListIo, NullIo, THREE_PORT_DISPLAY, program, walk};
use littleman::{Machine, NoTrace, Port, Program, RunErrorKind, Screen, load_program};

const INT64_MIN: i64 = i64::MIN;
const INT64_MAX: i64 = i64::MAX;

#[test]
fn hands_and_addition() {
    let man = walk("3M4+");
    assert_eq!((man.a, man.b), (7, 3));
}

#[test]
fn swap() {
    let man = walk("3M5W");
    assert_eq!((man.a, man.b), (3, 5));
}

#[test]
fn division_is_floored_with_the_remainder_in_b() {
    // Python semantics, not C: -7 / 2 is -4 remainder 1.
    let man = walk("2M7N/");
    assert_eq!((man.a, man.b), (-4, 1));
}

#[test]
fn division_by_zero_keeps_the_dividend() {
    let man = walk("5/");
    assert_eq!((man.a, man.b), (0, 5));
}

#[test]
fn modulo_takes_the_divisors_sign() {
    assert_eq!(walk("2NM7%").a, -1);
}

#[test]
fn xor_is_not_complement() {
    assert_eq!(walk("3M5~").a, 6);
}

#[test]
fn shift_left() {
    assert_eq!(walk("1M1{").a, 2);
}

#[test]
fn shift_left_out_of_range_is_zero() {
    assert_eq!(walk("`64`M1{").a, 0);
}

#[test]
fn shift_right_negative_count_is_zero() {
    assert_eq!(walk("1NM8}").a, 0);
}

#[test]
fn shift_right_over_63_sign_fills() {
    assert_eq!(walk("`64`M8N}").a, -1);
}

#[test]
fn arithmetic_wraps_silently() {
    assert_eq!(walk(&format!("1M`{INT64_MAX}`+")).a, INT64_MIN);
}

#[test]
fn backpack_writes() {
    assert_eq!(walk("5b").bp, 5);
    assert_eq!(walk("5bm").bp, 4);
    assert_eq!(walk("5b]").bp, 2);
    // `]` is arithmetic, so it is sign-preserving.
    assert_eq!(walk("1Nb]").bp, -1);
}

#[test]
fn x_turns_by_the_sign_of_a() {
    let stop_at = |expression: &str| {
        let source = format!("+-----+\n|   H |\n|@{expression}XH|\n|   H |\n+-----+");
        let program = program(&source);
        let mut machine = Machine::new(&program, NullIo);
        machine.run(10_000).expect("should not fault");
        let man = &machine.men[0];
        assert!(man.stopped);
        (man.x, man.y)
    };
    assert_eq!(stop_at("1."), (4, 3)); // A > 0: clockwise, east -> south
    assert_eq!(stop_at("1N"), (4, 1)); // A < 0: counter-clockwise, east -> north
    assert_eq!(stop_at("0."), (5, 2)); // A = 0: straight on
}

#[test]
fn receive_blocks_until_the_value_arrives() {
    let program = program("+-+  +----+\n|I|>>|@rH |\n+-+  +----+");
    let mut machine = Machine::new(&program, ListIo(vec![42]));
    machine.run(100).expect("should not fault");
    assert_eq!(machine.men[0].a, 42);
}

#[test]
fn q_counts_the_nearest_incoming_pipe_without_blocking() {
    let program = program("+-+    +----+\n|I|>-->|@qH |\n+-+    +----+");
    let mut machine = Machine::new(&program, ListIo(vec![1, 2]));
    machine.run(100).expect("should not fault");
    // One value has shifted off the source cell and the next has been fed in behind it.
    assert_eq!(machine.men[0].bp, 2);
}

#[test]
fn send_blocks_on_a_full_pipe() {
    // A pipe nobody drains backs up, and the sender spins on `s` until the step cap.
    let program = program("+-----+  +-+\n|@>5sv|>>| |\n| ^  <|  +-+\n+-----+");
    let mut machine = Machine::new(&program, NullIo);
    machine.run(100).expect("should not fault");
    assert_eq!(machine.tick, 100);
    assert!(machine.men[0].blocked);
    assert_eq!(machine.pipes.contents(0).collect::<Vec<_>>(), vec![Some(5), Some(5)]);
}

#[test]
fn output_is_emitted_before_a_wall_error() {
    // A value in the output pipe survives the man walking into a wall on the very next step.
    //
    // The wall error fires at the *execution* phase of the following tick, and I/O is phase 2 — so
    // the emit beats it. Confirmed against the server: an 8x8 `triangle` with no `H` scores 832.
    let source = "\
+-+   +---+
|I|>->|@rs|
+-+   +---+
        v
        v
       +-+
       |O|
       +-+";
    let program = program(source);
    let mut machine = Machine::new(&program, ListIo(vec![5]));
    let error = machine.run(100).expect_err("should walk into a wall");
    assert_eq!(error.kind, RunErrorKind::Wall);
    assert_eq!(machine.output, vec![5]);
}

#[test]
fn a_pipe_cell_backing_onto_a_wall_is_not_a_second_pipe() {
    // The second cell of a tight 2-cell pipe may back onto another room without being a new start.
    //
    // Walking a candidate is speculative: it is only fatal if no other pipe claims its cell. This
    // is the layout that makes an 8x8 `triangle` possible.
    let source = "\
+------+
|@rM*+v|
|s/W2M<|
+------+
+-+>^ v
|I|+-+<
+-+|O|
   +-+";
    let program = program(source);
    assert_eq!(program.pipes.len(), 2);
    assert!(program.pipes.iter().all(|pipe| pipe.cells.len() == 2));
}

/// The same tie as the test above — one cell is both "interior to a long pipe" and "a legal start
/// out of the room behind it" — resolved the other way, because here the candidate comes FIRST in
/// reading order. The scan claims cells as it goes, so the candidate wins. `{}` is the interior of
/// the room under the bend: blank makes it ordinary, `O` makes it the output room.
// NB: no `\` line continuation here — it would eat the leading spaces and shift the whole grid.
const GREEDY: &str = "     +---+
     |   |
     +---+
      ^
 >----^
 |  +-+
 |  |{}|
 ^  +-+
+---+
|@s |
+---+";

#[test]
fn an_earlier_candidate_start_takes_the_cell_from_a_longer_pipe() {
    let program = program(&GREEDY.replace("{}", " "));
    let mut starts: Vec<(i32, i32, usize)> =
        program.pipes.iter().map(|p| (p.cells[0].0, p.cells[0].1, p.cells.len())).collect();
    starts.sort();
    assert_eq!(starts, vec![(1, 7, 10), (6, 4, 2)]);
}

#[test]
fn a_pipe_that_only_a_greedy_scan_sees_can_reject_the_program() {
    // `memory/banked2-sbs` died on exactly this: the room below the bend was the output room, and
    // the server rejected a grid both local runners had accepted.
    let error = match load_program(&GREEDY.replace("{}", "O")) {
        Err(error) => error.to_string(),
        Ok(_) => panic!("the greedy scan should have found a pipe leaving the output room"),
    };
    assert!(error.contains("output room at (4,5) has a pipe flowing out of it"), "{error}");
}

// -------------------------------------------------------------------------------------------
// The LM-75
// -------------------------------------------------------------------------------------------

/// Deliver one value to each named port and let the display consume them.
///
/// Straight into the destination cells, skipping the men entirely: the point is the device, and
/// driving three ports from three rooms with chosen values would be a program, not a fixture.
fn feed(machine: &mut Machine<'_, NullIo, NoTrace>, values: &[(Port, i64)]) {
    let display = machine.program.displays[0].clone();
    for &(port, value) in values {
        let index = match port {
            Port::Addr => display.addr,
            Port::Data => display.data,
            Port::Swap => display.swap,
        };
        machine.pipes.put_dest(index.expect("port is wired") as usize, value);
    }
}

fn view<'a>(machine: &'a Machine<'_, NullIo, NoTrace>) -> &'a Screen {
    &machine.screens[0]
}

fn display_machine(program: &Program) -> Machine<'_, NullIo, NoTrace> {
    Machine::new(program, NullIo)
}

#[test]
fn data_advances_the_cursor_and_wraps() {
    let program = program(THREE_PORT_DISPLAY);
    let mut machine = display_machine(&program);
    for colour in [1, 2, 3] {
        feed(&mut machine, &[(Port::Data, colour)]);
        machine.display_step().expect("valid colour");
    }
    assert_eq!(view(&machine).next, vec![1, 2, 3]);
    // Past the last pixel is back to the upper-left, not an error.
    assert_eq!(view(&machine).cursor, 0);
    feed(&mut machine, &[(Port::Data, 4)]);
    machine.display_step().expect("valid colour");
    assert_eq!(view(&machine).next, vec![4, 2, 3]);
}

#[test]
fn addr_positions_the_cursor() {
    let program = program(THREE_PORT_DISPLAY);
    let mut machine = display_machine(&program);
    feed(&mut machine, &[(Port::Addr, 2)]);
    machine.display_step().expect("valid address");
    assert_eq!(view(&machine).cursor, 2);
    feed(&mut machine, &[(Port::Data, 9)]);
    machine.display_step().expect("valid colour");
    assert_eq!(view(&machine).next, vec![0, 0, 9]);
}

#[test]
fn swap_zero_clears_next_and_swap_one_preserves_it() {
    let program = program(THREE_PORT_DISPLAY);
    let mut machine = display_machine(&program);
    feed(&mut machine, &[(Port::Data, 5)]);
    machine.display_step().expect("valid colour");
    feed(&mut machine, &[(Port::Swap, 1)]);
    machine.display_step().expect("valid swap");
    assert_eq!(view(&machine).current, vec![5, 0, 0]);
    assert_eq!(view(&machine).next, vec![5, 0, 0]);
    assert_eq!(view(&machine).cursor, 1); // preserved

    feed(&mut machine, &[(Port::Swap, 0)]);
    machine.display_step().expect("valid swap");
    assert_eq!(view(&machine).current, vec![5, 0, 0]);
    assert_eq!(view(&machine).next, vec![0, 0, 0]);
    assert_eq!(view(&machine).cursor, 0);
}

#[test]
fn a_tick_can_address_draw_and_present_in_that_order() {
    // > The display processes ADDR first, then DATA, then SWAP. — language-reference
    let program = program(THREE_PORT_DISPLAY);
    let mut machine = display_machine(&program);
    feed(&mut machine, &[(Port::Addr, 2), (Port::Data, 7), (Port::Swap, 1)]);
    machine.display_step().expect("all three are valid");
    assert_eq!(machine.frames, vec![vec!["007".to_string()]]);
    // The DATA write advanced off the end and wrapped.
    assert_eq!(view(&machine).cursor, 0);
}

#[test]
fn the_display_validates_every_value() {
    let program = program(THREE_PORT_DISPLAY);
    let bad = |port: Port, value: i64| {
        let mut machine = display_machine(&program);
        feed(&mut machine, &[(port, value)]);
        machine.display_step().expect_err("out of range")
    };
    let addr_high = bad(Port::Addr, 3);
    assert_eq!(addr_high.kind, RunErrorKind::Display);
    assert!(addr_high.detail.contains("outside a 3x1 display"));
    assert!(bad(Port::Addr, -1).detail.contains("outside a 3x1 display"));
    assert!(bad(Port::Data, 16).detail.contains("not one of the 16 colours"));
    assert!(bad(Port::Swap, 2).detail.contains("neither 0 nor 1"));
}

#[test]
fn a_program_that_never_loads_is_not_a_machine() {
    assert!(
        load_program("+--+\n|@?|\n+--+").is_ok(),
        "an unknown glyph is a run error, not a load error"
    );
}
