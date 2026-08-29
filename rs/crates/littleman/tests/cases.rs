//! End-to-end: whole programs judged the way the server judges them.
//!
//! A port of `py/libs/runner/tests/test_cases.py`.

mod common;

use common::{one_pixel_display, one_room, program};
use littleman::{
    CaseIo, DEFAULT_MAX_TICKS, Frame, Io, Round, Stage, TestCase, run_case, run_free, score,
};

const HELLO: &str = "\
+----+    +-+
|@3sH|>-->|O|
+----+    +-+";

/// `3` into the backpack, then a loop that sends `5` once per pass and falls out when it empties.
const BACKPACK_LOOP: &str = "\
+-----+
|@3bv |  +-+
|vs5< |>>|O|
|> maH|  +-+
+-----+";

/// Reads a value and sends it straight back out, forever — one round per lap.
const ECHO: &str = "\
+-+  +-----+  +-+
|I|>>|@>rsv|>>|O|
+-+  | ^  <|  +-+
     +-----+";

fn strings(values: &[i64]) -> Vec<String> {
    values.iter().map(|value| value.to_string()).collect()
}

fn case(name: &str, rounds: &[(&[i64], &[i64])]) -> TestCase {
    TestCase {
        name: name.to_string(),
        rounds: rounds
            .iter()
            .map(|(inputs, out)| Round { inputs: strings(inputs), out: strings(out), frames: None })
            .collect(),
    }
}

fn frame_case(name: &str, frames: &[&[&str]]) -> TestCase {
    TestCase {
        name: name.to_string(),
        rounds: vec![Round {
            inputs: Vec::new(),
            out: Vec::new(),
            frames: Some(
                frames.iter().map(|rows| rows.iter().map(|r| r.to_string()).collect()).collect(),
            ),
        }],
    }
}

fn frame(rows: &[&str]) -> Frame {
    rows.iter().map(|row| row.to_string()).collect()
}

#[test]
fn hello_passes_after_the_output_pipe_drains() {
    // The man halts on tick 4 with the value still in flight; the pipe keeps ticking.
    let program = program(HELLO);
    let result = run_case(&program, &case("hello", &[(&[], &[3])]), DEFAULT_MAX_TICKS);
    assert!(result.passed, "{}", result.detail);
    assert_eq!(result.output, vec![3]);
    assert_eq!(result.ticks, 6);
}

#[test]
fn wrong_output_fails_immediately() {
    let program = program(HELLO);
    let result = run_case(&program, &case("hello", &[(&[], &[4])]), DEFAULT_MAX_TICKS);
    assert!(!result.passed);
    assert_eq!(result.error.as_deref(), Some("output-mismatch"));
    assert_eq!(result.output, vec![3]);
}

#[test]
fn backpack_loop_repeats_the_body() {
    let program = program(BACKPACK_LOOP);
    let result = run_case(&program, &case("thrice", &[(&[], &[5, 5, 5])]), DEFAULT_MAX_TICKS);
    assert!(result.passed, "{}", result.detail);
    assert_eq!(result.output, vec![5, 5, 5]);
}

#[test]
fn rounds_run_against_one_continuous_program() {
    let program = program(ECHO);
    let case = case("echo", &[(&[1], &[1]), (&[2], &[2])]);
    let result = run_case(&program, &case, DEFAULT_MAX_TICKS);
    assert!(result.passed, "{}", result.detail);
    assert_eq!(result.output, vec![1, 2]);
    assert_eq!(result.rounds_done, 2);
}

#[test]
fn round_input_is_withheld_until_the_round_is_answered() {
    let mut io = CaseIo::new(vec![
        Stage { inputs: vec![1], out: vec![1], frames: Vec::new() },
        Stage { inputs: vec![2], out: vec![2], frames: Vec::new() },
    ]);
    assert_eq!(io.take(), Some(1));
    assert_eq!(io.take(), None); // round 2 is gated on round 1's output
    assert!(io.emit(1, 5));
    assert_eq!(io.take(), Some(2));
    assert!(!io.emit(2, 9)); // the case is passed, so the run stops
    assert!(io.passed);
    assert_eq!(io.pass_tick, 9);
}

#[test]
fn a_round_expecting_no_output_unlocks_the_next_immediately() {
    let mut io = CaseIo::new(vec![
        Stage { inputs: vec![1], out: Vec::new(), frames: Vec::new() },
        Stage { inputs: vec![2], out: vec![2], frames: Vec::new() },
    ]);
    assert_eq!(io.take(), Some(1));
    assert_eq!(io.take(), Some(2));
}

#[test]
fn wall_error_is_reported_with_the_cell() {
    let program = program("+--+\n|@ |\n+--+");
    let result = run_case(&program, &case("walk", &[(&[], &[1])]), DEFAULT_MAX_TICKS);
    assert_eq!(result.error.as_deref(), Some("wall"));
    assert_eq!(result.cell, Some((3, 1)));
}

#[test]
fn bad_op_is_reported() {
    let program = program(&one_room("?"));
    let result = run_case(&program, &case("op", &[(&[], &[1])]), DEFAULT_MAX_TICKS);
    assert_eq!(result.error.as_deref(), Some("bad-op"));
    assert!(result.detail.contains("'?'"), "{}", result.detail);
}

#[test]
fn pipe_instruction_without_a_pipe() {
    let program = program(&one_room("s"));
    let result = run_case(&program, &case("pipe", &[(&[], &[1])]), DEFAULT_MAX_TICKS);
    assert_eq!(result.error.as_deref(), Some("no-pipe"));
}

#[test]
fn step_cap_ends_the_run() {
    let program = program(HELLO);
    let result = run_case(&program, &case("hello", &[(&[], &[3])]), 2);
    assert_eq!(result.error.as_deref(), Some("step-cap"));
}

#[test]
fn a_committed_frame_is_judged_against_the_expected_one() {
    let program = program(&one_pixel_display(2));
    let result = run_case(&program, &frame_case("lit", &[&["1"]]), DEFAULT_MAX_TICKS);
    assert!(result.passed, "{}", result.detail);
    assert_eq!(result.matched_frames, 1);
    assert_eq!(result.frames, vec![frame(&["1"])]);
    // The pixel and the swap both land on tick 4: the display draws before it presents.
    assert_eq!(result.ticks, 4);
}

#[test]
fn a_wrong_frame_fails_at_the_frame_that_differs() {
    let program = program(&one_pixel_display(2));
    let result = run_case(&program, &frame_case("dark", &[&["0"]]), DEFAULT_MAX_TICKS);
    assert!(!result.passed);
    assert_eq!(result.error.as_deref(), Some("frame-mismatch"));
    assert_eq!(result.matched_frames, 0);
    assert_eq!(result.frames, vec![frame(&["1"])]);
}

#[test]
fn a_swap_in_flight_still_commits_after_the_last_man_halts() {
    // The post-halt flush drains display pipes too, not just the output pipe.
    let program = program(&one_pixel_display(4));
    let result = run_case(&program, &frame_case("late", &[&["1"]]), DEFAULT_MAX_TICKS);
    assert!(result.passed, "{}", result.detail);
    // Both men halt on tick 4; the swap only reaches the display two ticks later.
    assert_eq!(result.ticks, 6);
}

#[test]
fn a_display_judged_case_needs_exactly_one_display() {
    let program = program(HELLO);
    let result = run_case(&program, &frame_case("palette", &[&["01"]]), DEFAULT_MAX_TICKS);
    assert!(!result.passed);
    assert_eq!(result.error.as_deref(), Some("display"));
    assert!(result.detail.contains("exactly one display"), "{}", result.detail);
}

#[test]
fn the_display_must_match_the_expected_resolution() {
    let program = program(&one_pixel_display(2));
    let result = run_case(&program, &frame_case("big", &[&["00", "00"]]), DEFAULT_MAX_TICKS);
    assert!(!result.passed);
    assert!(result.detail.contains("2x2") && result.detail.contains("1x1"), "{}", result.detail);
}

#[test]
fn output_in_a_display_judged_round_is_a_failure() {
    // > It is an error to emit any output in a display-judged program. — grading
    let mut io = CaseIo::new(vec![Stage {
        inputs: Vec::new(),
        out: Vec::new(),
        frames: vec![frame(&["0"])],
    }]);
    assert!(!io.emit(7, 1));
    let failure = io.failure.expect("a failure reason");
    assert!(failure.contains("expects no output"), "{failure}");
}

#[test]
fn frames_gate_the_next_round_of_input() {
    let mut io = CaseIo::new(vec![
        Stage { inputs: vec![1], out: Vec::new(), frames: vec![frame(&["0"])] },
        Stage { inputs: vec![2], out: Vec::new(), frames: vec![frame(&["1"])] },
    ]);
    assert_eq!(io.take(), Some(1));
    assert_eq!(io.take(), None); // round 2 is withheld until round 1's frame is committed
    assert!(io.commit(&frame(&["0"]), 5));
    assert_eq!(io.take(), Some(2));
}

#[test]
fn score_multiplies_footprint_by_average_ticks() {
    let program = program(HELLO);
    let results = vec![run_case(&program, &case("hello", &[(&[], &[3])]), DEFAULT_MAX_TICKS)];
    assert_eq!(score(&program, &results, "footprint-tick"), Some(169.0 * 6.0));
    assert_eq!(score(&program, &results, "footprint"), Some(169.0));
}

#[test]
fn score_is_none_unless_every_case_passes() {
    let program = program(HELLO);
    let results = vec![run_case(&program, &case("hello", &[(&[], &[4])]), DEFAULT_MAX_TICKS)];
    assert_eq!(score(&program, &results, "footprint-tick"), None);
}

#[test]
fn free_run_collects_output() {
    let program = program(HELLO);
    let result = run_free(&program, Vec::new(), DEFAULT_MAX_TICKS);
    assert!(result.passed, "{}", result.detail);
    assert_eq!(result.output, vec![3]);
}

#[test]
fn a_flat_case_is_lifted_into_one_round() {
    // > some problems return a flat `{"name", "in", "out"}` with no `rounds` key at all
    let cases = littleman::parse_cases(r#"[{"name": "flat", "in": ["7"], "out": ["7"]}]"#)
        .expect("valid JSON");
    assert_eq!(cases.len(), 1);
    assert_eq!(cases[0].rounds.len(), 1);
    assert_eq!(cases[0].rounds[0].inputs, vec!["7".to_string()]);
}
