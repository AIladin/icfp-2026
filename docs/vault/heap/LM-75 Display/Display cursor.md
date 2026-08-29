---
tags:
  - AI
  - spec
---

The cursor is the position in the **next** buffer ([[Display buffers]]) where the following pixel
will be drawn. It starts at `(0, 0)`, the upper-left corner.

- A DATA write paints at the cursor, then advances it: next column if possible, otherwise the next
  row, otherwise **wraps to the upper-left corner**. Drawing past the end is not an error; it wraps.
- An ADDR write sets the cursor from a single integer: `row * width + column`, both counted from 0,
  where `width` is the display's **interior** width. On a 4×4 display, `6` is row 1 column 2 and `15`
  is the bottom-right.
- A SWAP write of `0` homes the cursor; a SWAP of `1` leaves it exactly where it is.

Out-of-bounds or negative ADDR values are [[Display errors|errors]] that end the program.

## Consequences

- **Raster order is free, random access costs a pipe.** Sequential fills need no ADDR traffic at all,
  which is why the textbook's "simple program, complex image" example works: just stream DATA.
- The wrap-around means a program that streams `width * height` pixels lands back at the origin, so a
  full-frame loop needs no explicit repositioning.
- ADDR is a *multiply* away from `(row, col)`: the producing little man must compute
  `row * width + column` itself with [[Arithmetic instructions|`*` and `+`]], and the width is baked
  into the program as a constant. **Changing the display size means editing every ADDR computation.**
