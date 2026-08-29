"""Ephemeral pipes: a design marked with `b` / `B` must run exactly like the routed program.

The premise of the feature is that nothing about execution is special-cased — the markers become
real pipe cells and the ordinary loader takes it from there. These tests hold that line: the
synthesised grid *is* the hand-drawn one, tick for tick.
"""

import pytest
from littleman import ephemeral, load_program, run_free
from littleman.ephemeral import EphemeralError, synthesise

# Two relay rooms between I and O, each doubling the value it receives. Every pipe is 2 cells, so
# the marked version below can synthesise to exactly this grid.
ROUTED = "\n".join(
    [
        "+-+",
        "|I|",
        "+-+",
        " v",
        " v",
        "+------+",
        "|>@rM+v|",
        "|^.H.s<|",
        "+------+",
        " v",
        " v",
        "+------+",
        "|>@rM+v|",
        "|^.H.s<|",
        "+------+",
        " v",
        " v",
        "+-+",
        "|O|",
        "+-+",
    ]
)

# The same program as it leaves a designer's hands: no pipes, just attachments and their labels.
MARKED = "\n".join(
    [
        " +-+",
        " |I|",
        " +-+",
        " 1b",
        " 1B",
        " +------+",
        " |>@rM+v|",
        " |^.H.s<|",
        " +------+",
        " 2b",
        " 2B",
        " +------+",
        " |>@rM+v|",
        " |^.H.s<|",
        " +------+",
        " 3b",
        " 3B",
        " +-+",
        " |O|",
        " +-+",
    ]
)

# The same design in the letter-pair form: lowercase starts a pipe, uppercase ends it, and the
# letter is the pipe's name — no label cell at all.
PAIRED = "\n".join(
    [
        " +-+",
        " |I|",
        " +-+",
        "  a",
        "  A",
        " +------+",
        " |>@rM+v|",
        " |^.H.s<|",
        " +------+",
        "  c",
        "  C",
        " +------+",
        " |>@rM+v|",
        " |^.H.s<|",
        " +------+",
        "  z",
        "  Z",
        " +-+",
        " |O|",
        " +-+",
    ]
)

# One pipe written the old way (`b1`/`B1`), the next two as letter pairs, in one file.
MIXED = MARKED.replace(" 2b", "  c").replace(" 2B", "  C").replace(" 3b", "  z").replace(
    " 3B", "  Z"
)

# One room sending to two, with the `s` exactly 5 cells from each `b`: a nearest-pipe tie that a
# repack would resolve the other way round, with no load error and no crash.
AMBIGUOUS = "\n".join(
    [
        " +------+ ",
        " |@..s..| ",
        " |......| ",
        " +------+ ",
        "  ab   bc ",
        "  aB   Bc ",
        "  +-+ +-+ ",
        "  |@| |@| ",
        "  +-+ +-+ ",
    ]
)


# Two rooms with a blank row between the markers, so a route has somewhere to detour when the
# pipe is asked for more capacity than the shortest path gives it.
DELAY = "\n".join(
    [
        " +---+ ",
        " |@H | ",
        " +---+ ",
        " 1b    ",
        "       ",
        " 1B    ",
        " +---+ ",
        " |@H | ",
        " +---+ ",
    ]
)


def _normalise(source: str) -> str:
    return "\n".join(line.rstrip() for line in source.strip("\n").split("\n"))


def test_synthesised_grid_is_the_routed_one() -> None:
    """Adjacent markers give the minimum 2-cell pipe, which is what the hand drawing used."""
    assert _normalise(synthesise(MARKED).source) == _normalise(ROUTED)


def test_marked_and_routed_run_identically() -> None:
    routed = run_free(load_program(ROUTED), [3], max_ticks=2_000)
    marked = run_free(synthesise(MARKED).program, [3], max_ticks=2_000)
    assert routed.output == [12]
    assert marked.output == routed.output
    assert marked.ticks == routed.ticks
    assert marked.error == routed.error


def test_pipes_carry_their_labels() -> None:
    result = synthesise(MARKED)
    assert sorted(result.labels.values()) == ["1", "2", "3"]
    assert not result.warnings
    assert any("'s' at" in line for line in result.report)


def test_minimum_length_lengthens_the_route() -> None:
    """A delay line needs capacity, so a pipe can be asked for more than the shortest route."""
    result = synthesise(DELAY, min_lengths={"1": 5})
    assert [len(pipe.cells) for pipe in result.program.pipes] == [5]


def test_ambiguous_send_warns_and_names_both_pipes() -> None:
    result = synthesise(AMBIGUOUS)
    ambiguous = [w for w in result.warnings if "AMBIGUOUS" in w]
    assert len(ambiguous) == 1
    # Coordinates are the synthesised grid's, which is trimmed back to its content box.
    assert "'s' at (4,1)" in ambiguous[0]
    assert "'a'" in ambiguous[0] and "'c'" in ambiguous[0]


def test_two_pipes_on_one_side_warn() -> None:
    result = synthesise(AMBIGUOUS)
    assert any("south side" in w for w in result.warnings)


def test_unpaired_marker_is_an_error() -> None:
    lonely = MARKED.replace(" 3B", "  ")
    with pytest.raises(EphemeralError, match="1 'b' and 0 'B'"):
        synthesise(lonely)


def test_a_bare_b_is_the_letter_pair_b_and_needs_its_own_B() -> None:
    """Dropping a label turns that end into the letter-pair pipe `b`, which is then unmatched."""
    with pytest.raises(EphemeralError, match=r"pipe '1' has 0 'b' and 1 'B'"):
        synthesise(MARKED.replace(" 1b", "  b"))


def test_marker_touching_two_rooms_is_an_error() -> None:
    tight = "\n".join([" +-+", " |@|", " +-+", "1b", " +-+", " |@|", " +-+"])
    with pytest.raises(EphemeralError, match="touches two room walls"):
        synthesise(tight)


def test_a_program_without_markers_says_so() -> None:
    with pytest.raises(EphemeralError, match="nothing to synthesise"):
        synthesise(ROUTED)


# --------------------------------------------------------------------------- letter pairs


def test_letter_pairs_synthesise_the_routed_grid() -> None:
    assert _normalise(synthesise(PAIRED).source) == _normalise(ROUTED)


def test_letter_pairs_run_identically_to_the_routed_program() -> None:
    routed = run_free(load_program(ROUTED), [3], max_ticks=2_000)
    paired = run_free(synthesise(PAIRED).program, [3], max_ticks=2_000)
    assert paired.output == routed.output == [12]
    assert paired.ticks == routed.ticks
    assert paired.error == routed.error


def test_letter_pairs_are_named_by_their_lowercase_letter() -> None:
    result = synthesise(PAIRED)
    assert sorted(result.labels.values()) == ["a", "c", "z"]
    assert not result.warnings


def test_both_forms_may_share_one_file() -> None:
    result = synthesise(MIXED)
    assert _normalise(result.source) == _normalise(ROUTED)
    assert sorted(result.labels.values()) == ["1", "c", "z"]


def test_pipe_length_takes_a_letter() -> None:
    delay = DELAY.replace(" 1b", "  a").replace(" 1B", "  A")
    result = synthesise(delay, min_lengths={"a": 5})
    assert [len(pipe.cells) for pipe in result.program.pipes] == [5]


def test_unmatched_letter_is_an_error() -> None:
    with pytest.raises(EphemeralError, match=r"pipe 'a' has 1 'a' and 0 'A'"):
        synthesise(PAIRED.replace("  A", "   "))


def test_two_lowercase_of_one_letter_is_an_error() -> None:
    with pytest.raises(EphemeralError, match=r"pipe 'a' has 2 'a' and 1 'A'"):
        synthesise(PAIRED.replace("  z\n", "  a\n"))


def test_a_letter_inside_a_room_is_an_instruction_not_a_marker() -> None:
    """`a` is an instruction, so an interior one must not go looking for an `A` to pair with."""
    design = "\n".join(
        [" +---+", " |@a |", " +---+", "  c  ", "  C  ", " +---+", " |@H |", " +---+"]
    )
    result = synthesise(design)
    assert sorted(result.labels.values()) == ["c"]


def test_a_letter_off_the_wall_is_an_error() -> None:
    loose = DELAY.replace("       ", "   k   ")
    with pytest.raises(EphemeralError, match="touches no room wall"):
        synthesise(loose)


def test_a_label_that_could_be_a_marker_is_an_error() -> None:
    """`ab` over `AB`: is the `a` a label for `b`, or the pipe whose other end is `A`? Refuse."""
    both_ways = "\n".join(
        [" +---+", " |@H |", " +---+", " ab  ", " AB  ", " +---+", " |@H |", " +---+"]
    )
    with pytest.raises(EphemeralError, match="reads two ways"):
        synthesise(both_ways)


def test_a_bare_b_B_pair_is_just_the_pipe_named_b() -> None:
    """With both labels gone, `b`/`B` is an ordinary letter pair and the design still runs."""
    bare = MARKED.replace(" 1b", "  b").replace(" 1B", "  B")
    result = synthesise(bare)
    assert sorted(result.labels.values()) == ["2", "3", "b"]
    assert run_free(result.program, [3], max_ticks=2_000).output == [12]


def test_a_pipe_cannot_mix_the_two_forms() -> None:
    """A `b`/`B` labelled 'a' and a bare `a` marker would be one pipe written two ways."""
    clash = AMBIGUOUS.replace(" |......| ", " |......|a")
    with pytest.raises(EphemeralError, match="mixes the labelled"):
        synthesise(clash)


# --------------------------------------------------------------------------- routing many pipes

# Four bands of a sprawl, three pipes each. In every band the leftmost pipe's shortest route runs
# straight along the corridor row over the next pipe's exit cell — the failure the human hit on a
# 21-pipe design, where taking pipes one at a time in label order let an early route steal a later
# one's only way out of its room.
SPRAWL_BAND = [
    "+--------------------+",
    "|@                   |",
    "+--------------------+",
    "   {0}    {1}      {2}",
    "",
    "",
    "",
    "          {3}      {4}",
    "  +---+  +---+  +---+",
    "  |@ H|  |@ H|  |@ H|{5}",
    "  +---+  +---+  +---+",
    "",
    "",
]
SPRAWL = "\n".join(
    line.format(*(letters := "abc def ghi jkl".split()[band]), *(c.upper() for c in letters))
    for band in range(4)
    for line in SPRAWL_BAND
)


def _old_router(monkeypatch: pytest.MonkeyPatch) -> None:
    """The router as it used to be: label order, one pipe at a time, nothing reserved."""
    monkeypatch.setattr(
        ephemeral, "_orderings", lambda pairs: [sorted(pairs, key=lambda pair: pair.label)]
    )
    monkeypatch.setattr(ephemeral, "_reservations", lambda pairs, *, ends: {})


def test_label_order_alone_loses_a_later_pipes_exit_cell(monkeypatch: pytest.MonkeyPatch) -> None:
    """The regression this feature had: pipe 'a' routes across pipe 'b''s only way out."""
    _old_router(monkeypatch)
    with pytest.raises(EphemeralError) as raised:
        synthesise(SPRAWL)
    message = str(raised.value)
    assert "pipe 'b'" in message
    assert "pipe 'a' was routed first and is sitting in it" in message


def test_a_twelve_pipe_sprawl_routes() -> None:
    """The same design, with exit cells reserved up front and pipes taken most-constrained-first."""
    result = synthesise(SPRAWL)
    assert len(result.program.pipes) == 12
    assert sorted(result.labels.values()) == list("abcdefghijkl")
    # Every pipe still leaves through the cell straight out from its own FROM marker.
    load_program(result.source)


def test_every_pipe_keeps_its_own_exit_cell() -> None:
    """No pipe's second cell may belong to another pipe — that is the reservation, checked."""
    result = synthesise(SPRAWL)
    seconds = [pipe.cells[1] for pipe in result.program.pipes]
    assert len(set(seconds)) == len(seconds)
    for pipe in result.program.pipes:
        assert len(set(pipe.cells)) == len(pipe.cells)


# A marker sitting one cell out from another marker: `a` must leave through (2,4), and (2,4) is
# where the `C` marker is. The grid reads two ways and neither is routable, so it is refused.
EXIT_CLASH = "\n".join(
    [
        "+---+",
        "|@H |",
        "+---+",
        "  a",
        "  C",
        "+---+",
        "|@H |",
        "+---+",
        "",
        "  A",
        "+---+",
        "|@H |",
        "+---+",
        "  c",
    ]
)


def test_a_marker_on_another_markers_exit_cell_is_refused() -> None:
    with pytest.raises(EphemeralError) as raised:
        synthesise(EXIT_CLASH)
    message = str(raised.value)
    assert "reads two ways" in message
    assert "'C' marker at (2,4)" in message
    assert "'a' marker at (2,3)" in message
    assert "first segment" in message


# A pocket sealed by four rooms with a single one-cell entrance at column 3, and two pipes that both
# have to come through it. Whichever is routed first wins; no ordering saves the other.
POCKET = "\n".join(
    [
        "             ",
        "             ",
        "     m  n    ",
        "+-+ +----++-+",
        "|@| |@   ||@|",
        "| | +----+| |",
        "| |       | |",
        "| |  M  N | |",
        "| |+-----+| |",
        "| ||@    || |",
        "| |+-----+| |",
        "+-+       +-+",
    ]
)


def test_an_unroutable_design_names_the_pipe_in_the_way() -> None:
    with pytest.raises(EphemeralError) as raised:
        synthesise(POCKET)
    message = str(raised.value)
    assert "ephemeral routing failed on pipe" in message
    assert "the only corridor between them is blocked by already-routed pipe(s):" in message
    assert "'m'" in message and "'n'" in message
    # The endpoints and the cell it could not reach are all named, in the design's own coordinates.
    assert "'m' at (5,2)" in message or "'n' at (8,2)" in message
    assert "1 of 2 pipes were routed first" in message


def test_a_blocked_exit_cell_in_the_design_itself_is_named() -> None:
    """No pipe is at fault here — the exit cell is simply not blank, and the fix is in the design."""
    walled = "\n".join(
        ["+---+", "|@H |", "+---+", "  a", "  #", "", "  A", "+---+", "|@H |", "+---+"]
    )
    with pytest.raises(EphemeralError) as raised:
        synthesise(walled)
    message = str(raised.value)
    assert "cannot leave its room" in message
    assert "is (2,4), which is not blank" in message


# --------------------------------------------------------------------------- reserved letters


def test_v_and_V_cannot_name_a_pipe() -> None:
    """`v` is the arrowhead the router writes, so a `v`/`V` pair is refused by name."""
    design = PAIRED.replace("  a\n", "  v\n").replace("  A\n", "  V\n")
    with pytest.raises(EphemeralError) as raised:
        synthesise(design)
    message = str(raised.value)
    assert "RESERVED" in message
    assert "'v' and 'V'" in message
    assert "arrowhead" in message


def test_a_lone_V_against_a_wall_is_refused_too() -> None:
    """`V` is not a pipe glyph, so against a wall it can only be an attempt to name a pipe."""
    with pytest.raises(EphemeralError, match="RESERVED"):
        synthesise(PAIRED.replace("  A\n", "  V\n"))


def test_v_cannot_label_a_b_pipe_either() -> None:
    """`bv` is somebody labelling a pipe `v`; it used to be ignored, which is worse than an error."""
    with pytest.raises(EphemeralError, match="RESERVED"):
        synthesise(MARKED.replace(" 1b", " vb"))


def test_the_two_readings_are_both_spelled_out() -> None:
    """`ab` over `AB`: the error has to say what the two readings are, not just that there are two."""
    both_ways = "\n".join(
        [" +---+", " |@H |", " +---+", " ab  ", " AB  ", " +---+", " |@H |", " +---+"]
    )
    with pytest.raises(EphemeralError) as raised:
        synthesise(both_ways)
    message = str(raised.value)
    assert "(1) labelled form" in message
    assert "(2) letter-pair form" in message
    assert "label the 'b' pipe with a digit" in message


# --------------------------------------------------------------------------- the retry order

# The retry order is a cross-language contract: `rs/crates/littleman/src/ephemeral.rs` has to
# produce the same permutations or the two routers can synthesise different pipe graphs for one
# design. These fixtures are what both sides are pinned to. See
# `docs/vault/heap/The retry order is a specification, not a shuffle.md`.
XORSHIFT_CHAIN = [
    21903399195127931,
    1084646099022742235,
    17201177773494424350,
    8549851669132419384,
    16403554352028563834,
    972527648881529992,
]
SHUFFLED_ABCDEFGH = ["fhbcegad", "cdabghef", "fdagbche", "fhgcdbea", "chgefadb", "aefcbhgd"]


def test_the_generator_is_pinned() -> None:
    """xorshift64 with shifts 13 / 7 / 17, seeded with SEED. Rust must produce this chain."""
    state = ephemeral.SEED
    chain = []
    for _ in range(len(XORSHIFT_CHAIN)):
        state = ephemeral._xorshift(state)
        chain.append(state)
    assert chain == XORSHIFT_CHAIN
    assert all(0 <= value <= 0xFFFFFFFFFFFFFFFF for value in chain)


def test_the_shuffles_are_pinned() -> None:
    """Fisher-Yates, `i` from the end down to 1, `j = next() % (i + 1)`, one generator throughout."""
    pairs = [_labelled(letter) for letter in "abcdefgh"]
    orders = ephemeral._shuffles(pairs, len(SHUFFLED_ABCDEFGH))
    assert ["".join(pair.label for pair in order) for order in orders] == SHUFFLED_ABCDEFGH


def test_no_ordering_is_offered_twice() -> None:
    """Rotations and shuffles overlap on small designs; the router must not re-route the same order."""
    pairs = [_labelled(letter) for letter in "abc"]
    orders = ephemeral._orderings(pairs)
    keys = [tuple(pair.label for pair in order) for order in orders]
    assert len(keys) == len(set(keys))


def test_the_first_three_orderings_are_the_good_guesses() -> None:
    """Tight, reversed, label — unchanged by the determinism work, which is why every real design
    that routed before still routes to the same grid."""
    # Distances chosen so the tight order is neither label order nor its reverse, and all three of
    # the good guesses survive the dedup.
    reach = {"a": 5, "b": 1, "c": 9, "d": 3}
    pairs = [_labelled(letter, distance=reach[letter]) for letter in "abcd"]
    orders = [[pair.label for pair in order] for order in ephemeral._orderings(pairs)]
    assert orders[0] == ["b", "d", "a", "c"]
    assert orders[1] == ["c", "a", "d", "b"]
    assert orders[2] == ["a", "b", "c", "d"]


def _labelled(letter: str, distance: int | None = None) -> ephemeral.Pair:
    """A `Pair` with nothing but a label and a straight-line geometry — enough to order it."""
    marker = ephemeral.Marker(
        cell=(0, 0), label=letter, room=0, direction=0, outgoing=True, legacy=False
    )
    reach = (ord(letter) - ord("a") + 1) if distance is None else distance
    return ephemeral.Pair(
        label=letter,
        start=marker,
        end=marker,
        head=(0, 0),
        tail=(0, reach),
        exit_cell=(1, 0),
        entry_cell=(0, reach),
        want=2,
    )
