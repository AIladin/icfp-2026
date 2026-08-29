"""Local interpreter and judge for Littleman (.man) programs.

    from littleman import load_program, run_case

    program = load_program(Path("prog.man").read_text())
    result = run_case(program, case)          # case is an icfp_api TestCase
    print(result.passed, result.ticks, result.output)
"""

from .ephemeral import EphemeralError, Synthesis, synthesise
from .errors import LittlemanError, LoadError, RunError
from .grid import Grid
from .judge import DEFAULT_MAX_TICKS, RunResult, run_case, run_free, score
from .load import load_program
from .machine import Frame, Machine, Man, Screen
from .model import Display, Pipe, Program, Room
from .trace import Tracer, failure_report, frame_diff, summary

__all__ = [
    "DEFAULT_MAX_TICKS",
    "Display",
    "EphemeralError",
    "Frame",
    "Grid",
    "LittlemanError",
    "LoadError",
    "Machine",
    "Man",
    "Pipe",
    "Program",
    "Room",
    "RunError",
    "RunResult",
    "Screen",
    "Synthesis",
    "Tracer",
    "failure_report",
    "frame_diff",
    "load_program",
    "run_case",
    "run_free",
    "score",
    "summary",
    "synthesise",
]
