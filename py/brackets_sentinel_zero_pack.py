"""Hand-place the seeded-sentinel brackets pipeline in a 17x17 square."""

import argparse
from pathlib import Path

from brackets_decoder_seed_gen import build as build_decoder
from brackets_stack3_sentinel_zero_gen import build as build_stack

ROOT = Path(__file__).resolve().parent.parent


class Canvas:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], str] = {}

    def put(self, row: int, col: int, ch: str) -> None:
        assert len(ch) == 1
        old = self.cells.get((row, col))
        assert old is None or old == ch, (row, col, old, ch)
        self.cells[row, col] = ch

    def room(self, row: int, col: int, body: list[str]) -> None:
        height = len(body)
        width = len(body[0])
        assert all(len(line) == width for line in body)
        self.put(row - 1, col - 1, "+")
        self.put(row - 1, col + width, "+")
        self.put(row + height, col - 1, "+")
        self.put(row + height, col + width, "+")
        for c in range(width):
            self.put(row - 1, col + c, "-")
            self.put(row + height, col + c, "-")
        for r, line in enumerate(body):
            self.put(row + r, col - 1, "|")
            self.put(row + r, col + width, "|")
            for c, ch in enumerate(line):
                if ch != " ":
                    self.put(row + r, col + c, ch)

    def render(self) -> str:
        max_row = max(row for row, _ in self.cells)
        max_col = max(col for _, col in self.cells)
        lines = []
        for row in range(max_row + 1):
            line = "".join(self.cells.get((row, col), " ") for col in range(max_col + 1))
            lines.append(line.rstrip())
        return "\n".join(lines) + "\n"


def build() -> str:
    canvas = Canvas()
    counter = ["vM+1< ", " Hs0Xv", "> @r^W", "   Hs<"]

    canvas.room(1, 1, ["O"])
    canvas.room(1, 6, counter)
    canvas.room(4, 1, ["I"])
    canvas.room(7, 1, build_decoder())
    canvas.room(7, 7, build_stack())

    # counter -> output, two cells
    canvas.put(1, 3, "<")
    canvas.put(1, 4, "<")

    # input -> decoder, three cells; unchanged from v23
    canvas.put(4, 3, ">")
    canvas.put(4, 4, "v")
    canvas.put(5, 4, "v")

    # decoder -> stack around the stack's south-west corner, three cells
    canvas.put(15, 4, "v")
    canvas.put(16, 4, ">")
    canvas.put(16, 5, ">")

    # stack -> counter through the counter's east clearance, three cells
    canvas.put(5, 13, "^")
    canvas.put(4, 13, "|")
    canvas.put(3, 13, "<")

    text = canvas.render()
    assert len(text.splitlines()) == 17
    assert max(map(len, text.splitlines())) == 17
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "programs" / "brackets" / "v27-sentinel-zero-17x17.man",
    )
    args = parser.parse_args()
    assert args.out.name != "brackets.man", "refusing to overwrite the live fallback"
    args.out.write_text(build())
    print(f"wrote {args.out} (17x17)")


if __name__ == "__main__":
    main()
