"""The program text as a rectangular character grid.

> Short source lines are padded with spaces to the longest line's width.
> — language-reference#Odds and ends
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Grid:
    rows: tuple[str, ...]
    width: int
    height: int

    @classmethod
    def parse(cls, source: str) -> "Grid":
        lines = source.replace("\t", " ").split("\n")
        # A trailing newline is an editor artefact, not a row of the program.
        while lines and not lines[-1].strip():
            lines.pop()
        width = max((len(line) for line in lines), default=0)
        rows = tuple(line.ljust(width) for line in lines)
        return cls(rows, width, len(rows))

    def at(self, x: int, y: int) -> str:
        """The character at a cell; space outside the grid, so the edge needs no special case."""
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.rows[y][x]
        return " "

    def content_box(self) -> tuple[int, int, int, int]:
        """Bounding box (x0, y0, x1, y1) of non-space content; (0, 0, -1, -1) when empty."""
        xs_min, xs_max, ys_min, ys_max = self.width, -1, self.height, -1
        for y, row in enumerate(self.rows):
            stripped = row.rstrip()
            if not stripped:
                continue
            ys_min, ys_max = min(ys_min, y), max(ys_max, y)
            xs_min = min(xs_min, len(row) - len(row.lstrip()))
            xs_max = max(xs_max, len(stripped) - 1)
        if ys_max < 0:
            return (0, 0, -1, -1)
        return (xs_min, ys_min, xs_max, ys_max)

    def footprint(self) -> tuple[int, int]:
        """(width, height) of the content bounding box — the term the score squares."""
        x0, y0, x1, y1 = self.content_box()
        return (max(x1 - x0 + 1, 0), max(y1 - y0 + 1, 0))

    def excerpt(self, x: int, y: int, radius: int = 3) -> str:
        """A small window around a cell, for error messages."""
        lines = []
        for row_y in range(max(y - radius, 0), min(y + radius + 1, self.height)):
            marker = ">" if row_y == y else " "
            lines.append(f"{marker}{row_y:>4} |{self.rows[row_y]}")
        lines.append(f"      {' ' * x}^ ({x},{y})")
        return "\n".join(lines)
