//! `Y` (Split): two copies, creation order, and the four ways a little man can die.
//!
//! A port of `py/libs/runner/tests/test_split.py`, assertion for assertion.

mod common;

use common::{NullIo, program};
use littleman::machine::MAX_MEN;
use littleman::model::{EAST, NORTH, SOUTH, WEST};
use littleman::{Machine, Man, NoTrace, Outcome, Program, RunErrorKind, load_program};

/// A man walks east into the `Y` and is replaced by a south-bound and a north-bound copy, each
/// landing on an `H`.
const PLAIN: &str = "+-----+
|   H |
|@..Y |
|   H |
+-----+";

fn run_source(source: &str) -> (Program, Vec<Man>, Vec<i64>) {
    let program = program(source);
    let (men, output) = {
        let mut machine = Machine::new(&program, NullIo);
        machine.run(10_000).expect("should not fault");
        (machine.men.clone(), machine.output.clone())
    };
    (program, men, output)
}

fn men_of(source: &str) -> Vec<Man> {
    run_source(source).1
}

fn error_of(source: &str) -> littleman::RunError {
    let program = program(source);
    let mut machine = Machine::new(&program, NullIo);
    machine.run(10_000).expect_err("should fault")
}

#[test]
fn a_split_replaces_the_man_with_two_copies() {
    let men = men_of(PLAIN);
    assert_eq!(men.len(), 2);
    let placed: Vec<(i32, i32, u8)> = men.iter().map(|man| (man.x, man.y, man.dir)).collect();
    assert_eq!(placed, vec![(4, 3, SOUTH), (4, 1, NORTH)]);
    assert!(men.iter().all(|man| man.stopped));
}

/// > the copy born to the right takes over the splitting man's place in that order; the copy born
/// > to the left becomes the newest little man — split#Y, precisely
///
/// Walking east, right is south. So `men[0]` is the south-bound copy even though the north-bound
/// one is earlier in reading order.
#[test]
fn the_right_copy_takes_the_splitters_place_and_the_left_copy_is_newest() {
    let men = men_of(PLAIN);
    assert_eq!(men[0].dir, SOUTH);
    assert_eq!(men[1].dir, NORTH);
}

#[test]
fn both_copies_inherit_a_b_and_the_backpack() {
    let men = men_of(
        "+---------+
|        H|
|@7M3+5bWY|
|        H|
+---------+",
    );
    assert_eq!(men.len(), 2);
    for man in &men {
        // 7 -> A, M -> B=7, 3 -> A, + -> A=10, 5 -> A, b -> BP=5, W -> A=7 B=5.
        assert_eq!((man.a, man.b, man.bp), (7, 5, 5));
    }
}

/// > The tick after they were born, the copies execute the instruction they were born on and then
/// > move. — split#Y, precisely
///
/// The birth cells here hold `4` and `6`; if a newborn moved on the tick he was born he would step
/// straight past the digit and A would still be the splitter's.
#[test]
fn a_copy_executes_its_birth_cell_on_the_next_tick() {
    let men = men_of(
        "+-----+
|   H |
|   4 |
|@..Y |
|   6 |
|   H |
+-----+",
    );
    let mut values: Vec<i64> = men.iter().map(|man| man.a).collect();
    values.sort_unstable();
    assert_eq!(values, vec![4, 6]);
}

/// > If the birth cell is a wall, the program halts with an error. — split#Y, precisely
///
/// A wall here is anything that is not room interior, exactly as it is for a step: the room's own
/// border, another room, a pipe, or blank paper. So `Y` needs three cells across the heading — a
/// corridor one cell wide can never hold one, and the right-hand birth is the one that reports.
#[test]
fn a_birth_into_a_wall_is_an_error() {
    let error = error_of("+---+\n|@Y |\n+---+");
    assert_eq!(error.kind, RunErrorKind::Wall);
    assert_eq!(error.cell, Some((2, 2)));
    assert!(error.detail.contains("split into the wall at (2,2)"), "{}", error.detail);
}

/// A `Y` always stands on room interior, so its four neighbours are interior or its own border.
/// There is therefore no reachable "outside the room but not a wall" case.
#[test]
fn a_birth_cell_is_never_outside_the_room_without_being_a_wall() {
    let program = program(PLAIN);
    let width = program.grid.width();
    for (x, y) in program.rooms[0].interior_cells() {
        for (dx, dy) in [(1, 0), (0, 1), (-1, 0), (0, -1)] {
            let (nx, ny) = (x + dx, y + dy);
            let interior = program.room_of[(ny * width + nx) as usize] != Program::NO_ROOM;
            assert!(interior || program.rooms[0].on_border(nx, ny));
        }
    }
}

/// > two men arriving on the same cell in the same tick — split#Y, precisely
///
/// The copies are born facing away, turn straight back with `v` / `^`, and meet on the `Y`.
const HEAD_ON: &str = "+---+
|   |
| v |
|@Y |
| ^ |
|   |
+---+";

#[test]
fn two_copies_walking_into_each_other_both_die() {
    assert!(men_of(HEAD_ON).is_empty());
}

/// > If two little men are spawned on the same cell by two split instructions they both die.
///
/// Both copies of the first split turn north onto a `Y` of their own; the inner birth cells
/// coincide on (4,1) and annihilate, leaving the two outer ones on `H`.
#[test]
fn two_splits_onto_one_cell_kill_both_newborns() {
    let men = men_of(
        "+-------+
| HY YH |
|  ^Y^  |
|@  ^   |
+-------+",
    );
    let mut cells: Vec<(i32, i32)> = men.iter().map(|man| (man.x, man.y)).collect();
    cells.sort_unstable();
    assert_eq!(cells, vec![(2, 1), (6, 1)]);
    assert!(men.iter().all(|man| man.stopped));
}

/// Both copies reach an `s` on the same tick; the right (south) copy is first, so 9 leads.
///
/// This is the observable consequence of the ordering rule: the loser blocks for one tick and sends
/// on the next, so a reversed order would emit `5 9`.
#[test]
fn creation_order_decides_who_wins_a_pipe() {
    let (_, _, output) = run_source(
        "+------+    +-+
|  >5sH|    +-+
|@ Y   |>-->|O|
|  >9sH|    +-+
+------+    +-+",
    );
    assert_eq!(output, vec![9, 5]);
}

// -------------------------------------------------------------------------------------------
// Rules that need men placed by hand
//
// `Machine::can_collide` is decided from the grid — without a `Y` a program cannot put two men in
// one room, so the scan is skipped. These tests build the situation directly, so they turn it on.
// -------------------------------------------------------------------------------------------

const CORRIDOR: &str = "+-----+\n|@...H|\n+-----+";

fn staged(program: &Program, extra: Vec<Man>) -> Vec<Man> {
    let mut machine = Machine::new(program, NullIo);
    machine.men.extend(extra);
    machine.can_collide = true;
    machine.run(100).expect("should not fault");
    machine.men.clone()
}

/// > two adjacent men moving through each other (swapping cells) in the same tick
#[test]
fn two_men_swapping_cells_both_die() {
    let program = program(CORRIDOR);
    assert!(staged(&program, vec![Man::new(0, (2, 1), WEST)]).is_empty());
}

/// A stopped man still occupies his cell, so arriving on it is an ordinary collision.
#[test]
fn a_man_walking_onto_a_standing_man_kills_both() {
    let program = program(CORRIDOR);
    let mut occupant = Man::new(0, (2, 1), EAST);
    occupant.stopped = true;
    assert!(staged(&program, vec![occupant]).is_empty());
}

/// > If the birth cell is another little man (including a little man blocked on an instruction),
/// > both little men die. — split#Y, precisely
///
/// The occupant is parked on an `r` whose pipe never delivers, so he blocks forever; the splitter
/// is born onto him one tick later and both go.
#[test]
fn a_blocked_man_is_still_a_man() {
    let program = program(
        "+---+
|@H |
+---+
  v
  v
+---+
| H |
|@Y |
| r |
+---+",
    );
    let men = staged(&program, vec![Man::new(1, (2, 8), SOUTH)]);
    // Room 0's man halted; the surviving copy is the north-bound one, on the `H` at (2,6).
    let cells: Vec<(i32, i32)> = men.iter().map(|man| (man.x, man.y)).collect();
    assert_eq!(cells, vec![(2, 1), (2, 6)]);
}

#[test]
fn a_split_that_kills_everyone_still_terminates_cleanly() {
    let program = program(HEAD_ON);
    let mut machine = Machine::new(&program, NullIo);
    assert_eq!(machine.run(100).expect("should not fault"), Outcome::Halted);
    assert!(machine.men.is_empty());
    assert!(machine.tick < 100);
}

// -------------------------------------------------------------------------------------------
// The population cap
// -------------------------------------------------------------------------------------------

const CAP_ROOM: &str = "+---+\n| H |\n|@Y |\n| H |\n+---+";

/// A machine whose splitter is one of `live` men; the rest are parked and stopped.
///
/// The parked men get a cell each, off the grid — the cap is a count, and a 3x3 room cannot hold
/// 65536 men without every one of them colliding first.
fn crowd(program: &Program, live: usize) -> Machine<'_, NullIo, NoTrace> {
    let mut machine = Machine::new(program, NullIo);
    machine.men.extend((0..live - 1).map(|index| {
        let mut man = Man::new(0, (index as i32, -1), EAST);
        man.stopped = true;
        man
    }));
    machine
}

/// > The maximum number of live little men is 65536. Exceeding this limit is an error.
#[test]
fn a_split_past_the_population_cap_is_an_error() {
    let program = program(CAP_ROOM);
    let error = crowd(&program, MAX_MEN).run(10).expect_err("should fault");
    assert_eq!(error.kind, RunErrorKind::Population);
    assert!(error.detail.contains(&format!("past {MAX_MEN} live little men")), "{}", error.detail);
}

#[test]
fn a_split_that_lands_exactly_on_the_cap_is_fine() {
    let program = program(CAP_ROOM);
    let mut machine = crowd(&program, MAX_MEN - 1);
    assert_eq!(machine.run(10).expect("should not fault"), Outcome::Halted);
    assert_eq!(machine.men.len(), MAX_MEN);
}

#[test]
fn y_loads_as_an_instruction_rather_than_a_bad_op() {
    assert!(load_program(PLAIN).is_ok());
}
