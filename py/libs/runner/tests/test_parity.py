"""The Rust runner must agree with the Python one, field for field.

The Python runner is the oracle: `triangle` is server-confirmed 19/19 from two structurally
different programs, and `palette` matches all 16 frames the server ships. So the cheapest way to
trust `littleman.fast` is to run both over the same inputs and diff the `RunResult`s.

Two layers here:

* the real programs in `programs/`, against the real cases in `tests/data/`
* a seeded fuzz over random small grids, which is where a port actually drifts — load rules are
  quiet about being wrong

Error *messages* are compared too, because they were ported verbatim; if that ever becomes a
maintenance drag, drop `detail` from `SAME` and keep `error` and `cell`.
"""

import json
import random
from dataclasses import asdict
from pathlib import Path

import pytest
import littleman_rs
from icfp_api.models import TestCase
from littleman import ephemeral, fast, load_program, run_case, run_free
from littleman.errors import LoadError
from littleman.ephemeral import EphemeralError, pipe_graph, synthesise
from test_ephemeral import SPRAWL, XORSHIFT_CHAIN

ROOT = Path(__file__).resolve().parents[4]
PROGRAMS = ROOT / "programs"
DATA = Path(__file__).parent / "data"

# Every field of a RunResult. `frames` only keeps the last few, but both sides keep the same few.
SAME = (
    "case", "passed", "ticks", "output", "expected", "matched", "rounds_done",
    "error", "detail", "cell", "frames", "expected_frames", "matched_frames", "frame_count",
)  # fmt: skip


def cases(slug: str) -> list[TestCase]:
    payload = json.loads((DATA / slug).with_suffix(".json").read_text())
    return [TestCase.model_validate(item) for item in payload]


def compare(source: str, case: TestCase, max_ticks: int = 5_000_000) -> None:
    """Both runners over one program and one case; every field must match."""
    python = asdict(run_case(load_program(source), case, max_ticks=max_ticks))
    rust = asdict(fast.run_case(fast.load_program(source), case, max_ticks=max_ticks))
    for field in SAME:
        assert rust[field] == python[field], f"{field}: rust {rust[field]!r} != py {python[field]!r}"


@pytest.mark.parametrize(
    ("program", "slug"),
    [
        ("triangle.man", "triangle"),
        ("triangle-9x9.man", "triangle"),
        ("triangle-2room.man", "triangle"),
        ("palette.man", "palette"),
        # The big one: a 35x35 delay-line drum, 55 177 ticks on its worst case.
        ("memory.man", "memory"),
    ],
)
def test_the_real_programs_agree(program: str, slug: str) -> None:
    source = (PROGRAMS / program).read_text()
    for case in cases(slug):
        compare(source, case)


def test_a_display_program_commits_the_same_frames() -> None:
    """The one case with real expected frames behind it — 16 of them, from the server."""
    source = (PROGRAMS / "palette.man").read_text()
    result = fast.run_case(fast.load_program(source), cases("palette")[0])
    assert result.passed, result.detail
    assert result.matched_frames == 16
    assert result.frame_count == 16


def _both_load(source: str, name: str):
    """Load on both runners, asserting they agree about *rejection* as well as about parsing.

    Not every file under `programs/` loads, and that is the point rather than an accident: some are
    kept precisely because the server rejected them (`matmul-REJECTED-*`, the `banked2-sbs` family
    that a greedy pipe scan reads as a pipe leaving the output room). A load error is a verdict the
    two runners have to agree on too, so compare it instead of assuming it away.
    """
    try:
        python = load_program(source)
    except LoadError as error:
        with pytest.raises(LoadError) as caught:
            fast.load_program(source)
        assert str(caught.value) == str(error), name
        return None, None
    return python, fast.load_program(source)


def test_free_runs_agree() -> None:
    # A short cap on purpose: with no expected output several of these never halt, and the point is
    # that both runners agree tick for tick, not how long Python takes to reach 5 000 000.
    for program in sorted(PROGRAMS.rglob("*.man")):
        python_program, rust_program = _both_load(program.read_text(), program.name)
        if python_program is None:
            continue
        python = asdict(run_free(python_program, [987], max_ticks=50_000))
        rust = asdict(fast.run_free(rust_program, [987], max_ticks=50_000))
        for field in SAME:
            assert rust[field] == python[field], f"{program.name} {field}"


def test_footprint_and_summary_agree() -> None:
    for program in sorted(PROGRAMS.rglob("*.man")):
        python_program, rust_program = _both_load(program.read_text(), program.name)
        if python_program is None:
            continue
        assert rust_program.footprint() == python_program.footprint()


def test_a_load_error_is_the_ordinary_one() -> None:
    with pytest.raises(LoadError, match="not inside a room"):
        fast.load_program("+----+\n|    |\n+----+\n@")


# ------------------------------------------------------------------------------------------------
# Fuzz
# ------------------------------------------------------------------------------------------------

# Instructions, pipe glyphs, room glyphs and display glyphs, weighted toward things that make a
# grid *nearly* valid — a uniformly random grid is almost always the same two load errors.
ALPHABET = "  ..@@HMW+-*N/%&|~{}><^vXbmad]xqsSrRU0123456789`:=+-|"


def random_grid(rng: random.Random) -> str:
    """A small room with random junk inside, sometimes with a second box or a pipe stub."""
    width = rng.randint(3, 9)
    height = rng.randint(3, 6)
    rows = ["+" + "-" * width + "+"]
    for _ in range(height):
        body = "".join(rng.choice(ALPHABET) for _ in range(width))
        rows.append("|" + body + "|")
    rows.append("+" + "-" * width + "+")
    if rng.random() < 0.5:
        # A stub hanging off the right-hand wall: pipes are where the load rules get interesting.
        stub = "".join(rng.choice(">-<^v|") for _ in range(rng.randint(1, 4)))
        row = rng.randint(1, height)
        rows[row] += stub
    if rng.random() < 0.4:
        rows += ["", "+-+", "|O|", "+-+"] if rng.random() < 0.5 else ["", "+=+", ": :", "+=+"]
    return "\n".join(rows)


def test_random_grids_agree(subtests: object = None) -> None:
    """500 random grids: both runners must agree on loading, and then on the whole verdict."""
    rng = random.Random(20260724)
    case = TestCase.model_validate({"name": "fuzz", "in": ["3"], "out": ["3"]})
    agreed_loads = 0

    for index in range(500):
        source = random_grid(rng)
        note = f"seed 20260724, grid {index}:\n{source}"

        try:
            python_program = load_program(source)
        except LoadError as error:
            with pytest.raises(LoadError) as caught:
                fast.load_program(source)
            assert str(caught.value) == str(error), note
            continue

        rust_program = fast.load_program(source)
        agreed_loads += 1
        assert rust_program.footprint() == python_program.footprint(), note

        # A short cap: a random grid that loops forever is common and uninteresting, and both
        # runners must agree that it hit the cap at the same tick.
        python = asdict(run_case(python_program, case, max_ticks=3000))
        rust = asdict(fast.run_case(rust_program, case, max_ticks=3000))
        for field in SAME:
            assert rust[field] == python[field], f"{field} — {note}"

    # If almost everything failed to load the fuzz is testing nothing; this is the canary.
    assert agreed_loads > 50, f"only {agreed_loads} of 500 grids loaded — the alphabet is too wild"


# Everything a man can execute, minus `H` so he keeps going, weighted toward arithmetic and toward
# the digits that feed it. `V` and the turn arrows are in: a turn that ends in a wall is a verdict
# the two runners still have to agree on.
BODY = "0123456789012345678`+-*/%&|~{}NNMMWWbmad]xssrqSRU.  ><^vV"


def random_line(rng: random.Random) -> str:
    """One room of random instructions on a wire, so what the man computes comes out as output.

    The `wall` error at the far end is deliberate — with no `H` the run ends there, and
    `Output survives the wall error` says everything already in the pipe still lands.
    """
    body = "".join(rng.choice(BODY) for _ in range(rng.randint(6, 18)))
    width = len(body) + 2
    return "\n".join(
        [
            f"+-+  +{'-' * width}+    +-+",
            f"|I|>>|@{body} |>-->|O|",
            f"+-+  +{'-' * width}+    +-+",
        ]
    )


def test_random_instruction_lines_agree() -> None:
    """400 random instruction sequences, judged on what they emit.

    This is the half of the fuzz that exercises the *machine* rather than the loader: real
    arithmetic on real values, with `s` / `r` / `q` moving them over pipes. Registers are not
    observable from a `RunResult`, so the output pipe is the microscope.
    """
    rng = random.Random(20260725)
    ran = 0
    emitted = 0

    for index in range(400):
        source = random_line(rng)
        note = f"seed 20260725, line {index}:\n{source}"
        try:
            python_program = load_program(source)
        except LoadError as error:
            with pytest.raises(LoadError) as caught:
                fast.load_program(source)
            assert str(caught.value) == str(error), note
            continue

        ran += 1
        python = asdict(run_free(python_program, [7, -3, 5, 0, 987], max_ticks=3000))
        rust = asdict(fast.run_free(fast.load_program(source), [7, -3, 5, 0, 987], max_ticks=3000))
        emitted += len(python["output"])
        for field in SAME:
            assert rust[field] == python[field], f"{field} — {note}"

    assert ran > 300, f"only {ran} of 400 lines loaded"
    assert emitted > 100, f"only {emitted} values emitted — the fuzz is not reaching the pipes"


# Instructions that make a splitting room interesting: turns to bring copies back at each other,
# `Y` often enough that a grid usually reaches several, digits so the copies carry distinct values,
# and `s` so who-goes-first shows up in the output. No `H`, so a run ends on a wall or a collision.
SPLIT_BODY = "><^v..  ssH0123456789+*MWXbdxr"


def random_split_room(rng: random.Random) -> str:
    """A wide room full of `Y`s wired to an output pipe, so births and deaths are observable.

    This is the fuzz that covers the split rules end to end: birth placement, the creation order
    the copies inherit, wall births, and every way two men can annihilate. The output pipe is the
    microscope — which value lands first is decided by the order the men act in.
    """
    # `Y` density varies per grid: a dense room mostly dies on a wall birth, a sparse one keeps
    # several copies alive long enough to race each other to the pipe. The fuzz wants both.
    alphabet = SPLIT_BODY + "Y" * rng.randint(1, 8)
    width = rng.randint(5, 16)
    height = rng.randint(3, 10)
    rows = ["+" + "-" * width + "+"]
    for y in range(height):
        body = "".join(rng.choice(alphabet) for _ in range(width))
        rows.append("|" + ("@" + body[1:] if y == height // 2 else body) + "|")
    rows.append("+" + "-" * width + "+")
    # An output room on the right, so `s` has somewhere to go and the order men act in is visible.
    pipe_row = rng.randint(1, height)
    rows[pipe_row - 1] += "    +-+"
    rows[pipe_row] += ">-->|O|"
    rows[pipe_row + 1] += "    +-+"
    return "\n".join(rows)


def test_random_splitting_rooms_agree() -> None:
    """300 rooms packed with `Y`, judged on what they emit and how they die."""
    rng = random.Random(20260725)
    ran = 0
    split_errors = 0
    emitted = 0

    for index in range(300):
        source = random_split_room(rng)
        note = f"seed 20260725, split room {index}:\n{source}"
        try:
            python_program = load_program(source)
        except LoadError as error:
            with pytest.raises(LoadError) as caught:
                fast.load_program(source)
            assert str(caught.value) == str(error), note
            continue

        ran += 1
        python = asdict(run_free(python_program, [3, -1, 8], max_ticks=2000))
        rust = asdict(fast.run_free(fast.load_program(source), [3, -1, 8], max_ticks=2000))
        for field in SAME:
            assert rust[field] == python[field], f"{field} — {note}"
        emitted += len(python["output"])
        if python["error"] == "wall" and "split into" in (python["detail"] or ""):
            split_errors += 1

    # Canaries: a fuzz where nothing splits, or where nothing reaches the pipe, tests nothing.
    assert ran > 100, f"only {ran} of 300 split rooms loaded"
    assert split_errors > 5, f"only {split_errors} wall births — the fuzz is not splitting"
    assert emitted > 300, f"only {emitted} values emitted — the copies are not reaching the pipe"


# The split rules, one grid each — these are `tests/test_split.py`'s fixtures, run through both
# implementations. The fuzz above finds drift in bulk; these pin the rules by name, and each one is
# discriminating on its own (a runner that ignored collisions would spin to the step cap on the
# head-on grid rather than halting).
SPLIT_FIXTURES = {
    "plain": "+-----+\n|   H |\n|@..Y |\n|   H |\n+-----+",
    "inherit": "+---------+\n|        H|\n|@7M3+5bWY|\n|        H|\n+---------+",
    "birth-cell-runs-next-tick": (
        "+-----+\n|   H |\n|   4 |\n|@..Y |\n|   6 |\n|   H |\n+-----+"
    ),
    "wall-birth": "+---+\n|@Y |\n+---+",
    "head-on": "+---+\n|   |\n| v |\n|@Y |\n| ^ |\n|   |\n+---+",
    "double-spawn": "+-------+\n| HY YH |\n|  ^Y^  |\n|@  ^   |\n+-------+",
    "creation-order": (
        "+------+    +-+\n|  >5sH|    +-+\n|@ Y   |>-->|O|\n|  >9sH|    +-+\n+------+    +-+"
    ),
}


@pytest.mark.parametrize("name", sorted(SPLIT_FIXTURES))
def test_split_fixtures_agree(name: str) -> None:
    source = SPLIT_FIXTURES[name]
    python = asdict(run_free(load_program(source), [], max_ticks=10_000))
    rust = asdict(fast.run_free(fast.load_program(source), [], max_ticks=10_000))
    for field in SAME:
        assert rust[field] == python[field], f"{field} — {name}"


# ------------------------------------------------------------------------------------------------
# Ephemeral pipes: the two routers must synthesise the same grid
# ------------------------------------------------------------------------------------------------
#
# This is the parity that matters most for `--ephemeral-pipes`, because a divergence here is silent:
# both runners load, both run, and they are running *different programs*. The retry order is a
# specified xorshift precisely so this can hold — see
# `docs/vault/heap/The retry order is a specification, not a shuffle.md`.


def compare_synthesis(source: str, lengths: dict[str, int] | None = None) -> None:
    """Both routers over one design: same grid, same labels, same graph, same warnings — or the
    same error message, character for character."""
    lengths = lengths or {}
    try:
        expected = synthesise(source, min_lengths=lengths)
    except EphemeralError as error:
        with pytest.raises(Exception) as caught:  # noqa: PT011 — the Rust twin is its own type
            littleman_rs.synthesise(source, lengths)
        assert str(caught.value) == str(error), source
        return

    got_source, got_labels, got_warnings, got_report, got_graph = littleman_rs.synthesise(
        source, lengths
    )
    assert got_source == expected.source, source
    assert got_labels == expected.labels, source
    assert got_warnings == expected.warnings, source
    assert got_report == expected.report, source
    assert got_graph == pipe_graph(expected.program, expected.labels), source


EPHEMERAL_FIXTURES = {
    "two-relays": "+-+\n|I|\n+-+\n a\n\n A\n+------+\n|>@rM+v|\n|^.H.s<|\n+------+\n c\n\n C\n+-+\n|O|\n+-+",
    "legacy-labels": " +---+ \n |@ H| \n +---+ \n 1b    \n       \n 1B    \n +---+ \n |@H | \n +---+ ",
    "no-markers": "+---+\n|@ H|\n+---+",
    "unpaired": "+---+\n|@ H|\n+---+\n a",
    "reserved-v": "+---+\n|@ H|\n+---+\n V\n\n v\n+---+\n|@ H|\n+---+",
}


@pytest.mark.parametrize("name", sorted(EPHEMERAL_FIXTURES))
def test_the_two_routers_agree_on_a_fixture(name: str) -> None:
    compare_synthesis(EPHEMERAL_FIXTURES[name])


def test_the_two_routers_agree_on_a_twelve_pipe_sprawl() -> None:
    """The design the retry pool exists for: twelve pipes whose obvious routes fight each other."""
    compare_synthesis(SPRAWL)


def test_the_two_routers_agree_on_a_minimum_pipe_length() -> None:
    compare_synthesis(EPHEMERAL_FIXTURES["two-relays"], {"a": 6})


def test_the_generator_is_the_same_on_both_sides() -> None:
    """The xorshift chain itself, which is what makes every other agreement possible."""
    assert littleman_rs.xorshift_chain(ephemeral.SEED, 6) == XORSHIFT_CHAIN


def test_random_designs_route_identically() -> None:
    """60 random marker designs, routed by both. Success or failure, the answer must match.

    Kept to 60 because the *Python* router is the slow half — a design that cannot be routed pays
    for every ordering in the pool, twice over, and that is the case this fuzz is mostly generating.
    """
    rng = random.Random(20260726)
    routed = 0
    failed = 0
    for _ in range(60):
        source = random_design(rng)
        try:
            synthesise(source)
        except EphemeralError:
            failed += 1
        else:
            routed += 1
        compare_synthesis(source)
    # Canaries: a fuzz where everything routes never exercises the retry pool, and one where
    # nothing routes never exercises the router.
    assert routed > 15, f"only {routed} of 60 designs routed"
    assert failed > 8, f"only {failed} of 60 designs failed — the fuzz is too easy"


MARKER_LETTERS = "acdefghijklmnopqrstuwxyz"  # no `b` (legacy form) and no `v` (reserved)


def random_design(rng: random.Random) -> str:
    """Small rooms on a coarse lattice with markers on their walls, paired at random.

    Deliberately cramped: the interesting cases are the ones where two pipes want one corridor,
    which is where the retry order decides the outcome.
    """
    cols, rows = rng.randint(2, 3), rng.randint(2, 3)
    room_w, room_h = rng.randint(3, 6), rng.randint(1, 3)
    pitch_x = room_w + 2 + rng.randint(4, 8)
    pitch_y = room_h + 2 + rng.randint(3, 6)
    canvas = [[" "] * (cols * pitch_x + 4) for _ in range(rows * pitch_y + 4)]

    boxes = []
    for index in range(rows * cols):
        x0 = 2 + (index % cols) * pitch_x
        y0 = 2 + (index // cols) * pitch_y
        x1, y1 = x0 + room_w + 1, y0 + room_h + 1
        for x in range(x0, x1 + 1):
            canvas[y0][x] = canvas[y1][x] = "-"
        for y in range(y0, y1 + 1):
            canvas[y][x0] = canvas[y][x1] = "|"
        for cx, cy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            canvas[cy][cx] = "+"
        canvas[y0 + 1][x0 + 1], canvas[y0 + 1][x1 - 1] = "@", "H"
        boxes.append((x0, y0, x1, y1))

    sites = {}
    for index, (x0, y0, x1, y1) in enumerate(boxes):
        places = [(x, y0 - 1) for x in range(x0 + 1, x1)]
        places += [(x, y1 + 1) for x in range(x0 + 1, x1)]
        places += [(x0 - 1, y) for y in range(y0 + 1, y1)]
        places += [(x1 + 1, y) for y in range(y0 + 1, y1)]
        rng.shuffle(places)
        sites[index] = places

    used: set[tuple[int, int]] = set()
    placed = 0
    for letter in MARKER_LETTERS[: rng.randint(2, 3 * len(boxes) // 2)]:
        src, dst = rng.sample(range(len(boxes)), 2)
        ends = []
        for room, char in ((src, letter), (dst, letter.upper())):
            while sites[room]:
                cell = sites[room].pop()
                # Two markers within two cells of each other read two ways; the router refuses
                # those up front and the fuzz has better things to test.
                near = {
                    (cell[0] + dx, cell[1] + dy)
                    for dx in range(-2, 3)
                    for dy in range(-2, 3)
                }
                if not near & used:
                    ends.append((cell, char))
                    break
        if len(ends) != 2:
            continue
        for cell, char in ends:
            canvas[cell[1]][cell[0]] = char
            used.add(cell)
        placed += 1
    if placed < 2:
        # Degenerate lattice: fall back to a design that is guaranteed to have work to do.
        return EPHEMERAL_FIXTURES["two-relays"]
    return "\n".join("".join(row).rstrip() for row in canvas)
