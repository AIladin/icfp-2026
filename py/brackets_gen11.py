"""Correctness experiment: base-3 stack room for the brackets pipeline.

This deliberately spacious handoff proves room logic and depth-32 safety before
any packing work.  It reuses D and N from brackets_gen10 unchanged.
"""

from __future__ import annotations

import subprocess

from brackets_gen10 import Canvas, ROOT, build_d_body, build_n_body


def build_c3_body() -> list[str]:
    """Base-3 C room; spacious first layout with independent branch returns."""
    g = [[" "] * 17 for _ in range(16)]

    def put(r: int, c: int, ch: str) -> None:
        assert g[r][c] == " ", (r, c, g[r][c], ch)
        g[r][c] = ch

    # All accepted branches return along row 1, descend column 4 and enter
    # the common r/X head heading east.
    put(1, 4, "v")
    for r in range(2, 8):
        put(r, 4, "v")
    put(8, 4, ">")
    put(8, 7, "r")
    put(8, 8, "X")

    # Spawn seeds N with verdict 0, then joins the head from below.
    put(9, 0, "@")
    put(9, 1, "0")
    put(9, 2, "s")
    put(9, 3, ">")
    put(9, 4, "^")

    # Push (+code): S <- 3*S+t, verdict 0.  Return around the east edge.
    for r, ch in zip(range(9, 15), "+++M0s", strict=True):
        put(r, 8, ch)
    put(15, 8, ">")
    for c in range(9, 16):
        put(15, c, ">")
    put(15, 16, "^")

    # Pop (-code): first form S-t and branch on its sign.
    put(7, 8, "+")
    put(6, 8, "X")
    # S-t < 0: mismatch or empty. Negate to the positive offence verdict.
    put(6, 7, "N")
    put(6, 6, "s")
    put(6, 5, "H")
    # S-t == 0: exact match emptying the stack; explicitly clear B.
    put(5, 8, "0")
    put(4, 8, "M")
    put(3, 8, "0")
    put(2, 8, "s")
    put(1, 8, "<")
    for c in range(5, 8):
        put(1, c, "<")
    # S-t > 0: quotient/remainder in base 3; remainder is the verdict.
    for c, ch in zip(range(9, 15), "M3W/Ws", strict=True):
        put(6, c, ch)
    put(6, 15, ">")
    put(6, 16, "^")

    # Both long accepted returns share the east edge and top row.
    for r in range(2, 15):
        if g[r][16] == " ":
            put(r, 16, "^")
    put(1, 16, "<")
    for c in range(5, 16):
        if g[1][c] == " ":
            put(1, c, "<")

    # End sentinel (code 0).  Positive stack => n+1 offence; empty => -1.
    put(8, 9, "W")
    put(8, 10, "X")
    put(9, 10, "s")
    put(10, 10, "H")
    put(8, 11, "1")
    put(8, 12, "N")
    put(8, 13, "s")
    put(8, 14, "H")

    return ["".join(row) for row in g]


def build_handoff() -> str:
    cv = Canvas()
    cv.room(2, 2, ["I"])
    cv.room(2, 10, build_d_body())
    cv.room(13, 10, build_c3_body())
    cv.room(34, 10, build_n_body())
    cv.room(36, 30, ["O"])

    # Ephemeral handoff markers, one pair per unambiguous chain edge.
    cv.put(3, 4, "a")
    cv.put(3, 8, "A")
    cv.put(10, 11, "c")
    cv.put(11, 11, "C")
    cv.put(30, 11, "e")
    cv.put(32, 11, "E")
    cv.put(36, 17, "f")
    cv.put(37, 28, "F")
    return cv.render()


def main() -> None:
    out = ROOT / "programs" / "brackets-v13-base3-handoff.man"
    out.write_text(build_handoff())
    print(f"wrote {out}")
    subprocess.run(["lmr", "check", str(out), "--ephemeral-pipes"], check=False)


if __name__ == "__main__":
    main()
