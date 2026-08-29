"""Failure modes, split the way the contest splits them.

A ``LoadError`` is structural and is caught before any tick runs — the server reports these as
``loadError`` with no test case run at all. A ``RunError`` happens mid-run and ends the whole
program; its ``kind`` is one of the three names the language reference uses, or ``display``.
"""


class LittlemanError(Exception):
    """Base for everything this package raises."""


class LoadError(LittlemanError):
    """The program is structurally invalid: it would never start."""


class RunError(LittlemanError):
    """A fatal mistake mid-run: wall, bad-op, no-pipe, or display. Ends the whole program.

    ``display`` is the LM-75's own validation — a bad ADDR, colour or SWAP value. The reference does
    not name it alongside the other three, but it ends the run the same way.
    """

    def __init__(self, kind: str, detail: str, cell: tuple[int, int] | None = None) -> None:
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail
        self.cell = cell
