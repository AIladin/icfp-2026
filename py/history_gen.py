"""Emit the `history-lesson` program: 2810 fixed characters, scored on footprint alone.

There is no input and ticks are free, so the whole problem is "how many bits fit in a cell".
The only way to get a number out of the grid is a numeric literal, and the densest one is
`` ` `` + 18 digits + `` ` `` + `s` -- 21 cells carrying just under 60 bits, i.e. **~2.85
bits per cell**. Everything else is a rounding error, so the program is one enormous room
full of literals plus a ten-cell decoder.

DATA is a boustrophedon of literals. Each 21-cell block is one chunk; a chunk is 9 characters
packed base-91 (the text lives entirely in ASCII 32..122), little-endian so that `% 91` peels
off the character to emit next.

Two layout facts do all the work:

- Walking west, a block's cells are visited in the mirror order, so a westbound row lays out
  as `s` `` ` `` digits `` ` `` and each block still loads before it sends. Rows therefore
  need no phase correction and no wasted block at the fold.
- **Backticks pair on both axes independently**, so those two mirrored patterns must not put a
  backtick and an `s` in the same column: `s` between two backticks is a load error even when
  both of them already pair horizontally. Offsetting the westbound blocks by one column lines
  every column up as backtick-over-backtick, backtick-over-digit or digit-over-`s`, all legal.
  That one spare column is the whole difference between a 88x88 grid and this 89x89 one.

DEC is the whole decoder:

    A = V, B = 91, BP = 9
    /   A = V/91, B = V%91      W   A = char, B = quotient
    s   emit                    `91` W   A = quotient, B = 91 again
    m a loop nine times, then fall through to the next chunk

The `` `91` `` reload is what removes the need for scratch memory: after `W` the quotient is
already parked in B, so loading the constant into A and swapping restores both registers at
once. ADD is a separate room that only adds 32, because that offset cannot be applied while
B is busy holding the quotient.
"""

from __future__ import annotations

from memory_gen import Canvas

BASE, OFF = 91, 32  # text is ASCII 32..122, so `c - 32` is a base-91 digit
DIGITS = 18  # 91**9 < 10**18, and 10**18 - 1 still fits a signed 64-bit word
PER_CHUNK = 9
BLOCK = DIGITS + 3  # ` + digits + ` + s
CHUNKS_PER_ROW = 4
ROWS = 79

# the blocks, a turn cell at each end, and one spare column that offsets the westbound
# blocks by one so that no column carries a backtick in one direction and an `s` in the other
W_INT = BLOCK * CHUNKS_PER_ROW + 3
DATA_W, DATA_H = W_INT + 2, ROWS + 2
PIPE_COL = 5
DEC_Y = DATA_H + 2  # two cells of pipe between DATA's floor and DEC's ceiling


def chunks(text: str) -> list[int]:
    """Pack `text` little-endian, PER_CHUNK characters to a chunk, padded with spaces."""
    pad = -len(text) % PER_CHUNK
    text += " " * pad
    out = []
    for i in range(0, len(text), PER_CHUNK):
        v = 0
        for ch in reversed(text[i : i + PER_CHUNK]):
            v = v * BASE + (ord(ch) - OFF)
        out.append(v)
    return out


def data_room(c: Canvas, values: list[int]) -> None:
    """One room, ROWS boustrophedon rows, CHUNKS_PER_ROW literals each."""
    c.room(0, 0, DATA_W, DATA_H)
    need = ROWS * CHUNKS_PER_ROW
    values = values + [0] * (need - len(values))

    for i in range(ROWS):
        y, east = i + 1, i % 2 == 0
        row = values[i * CHUNKS_PER_ROW : (i + 1) * CHUNKS_PER_ROW]
        for j, v in enumerate(row):
            digits = f"{v:0{DIGITS}d}"
            if east:
                # visited left to right: open, digits, close, send
                c.text(2 + j * BLOCK, y, "`" + digits + "`s")
            else:
                # visited right to left: the same four parts, mirrored into the grid
                c.text(W_INT - (j + 1) * BLOCK, y, "s`" + digits[::-1] + "`")

        # folds: enter each row on the side the previous one ended, leave on the other
        c.put(1 if east else W_INT, y, "@" if i == 0 else ">" if east else "<")
        c.put(W_INT if east else 1, y, "H" if i == ROWS - 1 else "v")


def dec_room(c: Canvas, x0: int, y0: int) -> None:
    """Nine divisions per chunk; `a` is the counter test and the fold in one cell."""
    c.room(x0, y0, 15, 5)
    c.text(x0 + 1, y0 + 1, "@>9b`91`Mr  v")  # BP = 9, B = 91, A = the chunk
    c.text(x0 + 13, y0 + 2, "</Ws`91`Wma^", dx=-1)  # the lane runs west
    c.put(x0 + 3, y0 + 3, ">")  # loop fold, laid west to east under the lane
    c.put(x0 + 13, y0 + 3, "^")


def add_room(c: Canvas, x0: int, y0: int) -> None:
    """B = 32 forever; the base-91 digit that arrives is turned into ASCII and passed on."""
    c.room(x0, y0, 9, 5)
    c.text(x0 + 1, y0 + 1, "@`32`Mv")
    c.text(x0 + 7, y0 + 2, "<r+s v", dx=-1)
    c.put(x0 + 2, y0 + 3, ">")
    c.put(x0 + 7, y0 + 3, "^")


def build(text: str) -> str:
    c = Canvas()
    data_room(c, chunks(text))

    dec_x, add_x = 0, 17
    dec_room(c, dec_x, DEC_Y)
    add_room(c, add_x, DEC_Y)
    mid = DEC_Y + 2

    c.room(add_x + 11, DEC_Y + 1, 3, 3)
    c.put(add_x + 12, mid, "O")

    c.pipe([(PIPE_COL, DATA_H - 1), (PIPE_COL, DEC_Y)])
    c.pipe([(dec_x + 14, mid), (add_x, mid)])
    c.pipe([(add_x + 8, mid), (add_x + 11, mid)])
    return c.render()


if __name__ == "__main__":
    import sys

    print(build(sys.stdin.read()), end="")
