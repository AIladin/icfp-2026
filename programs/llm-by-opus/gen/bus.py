"""CPU-side bus macros: the cells that issue one RAM command.

Every awkward detail here is register pressure.  A little man has A, B and a write-only backpack,
so three payload words cannot be held at once, and that fixes the order of each command:

- a **mode is always a single digit**, and a single digit is the only load that does *not* clobber
  B.  That is what lets a write send its mode while the value waits in B.
- a **read sends the address twice**.  RAM needs `addr` for the first half-lap and
  `RING - 1 - addr` for the second, and it cannot derive one from the other: with `addr` in B,
  loading `RING - 1` into A needs an `M`.  Given two copies it can, though --
  `lit(RING-1) M r - N` is `RING - 1 - addr` -- so the CPU just sends `s` twice, which costs one
  cell because `s` leaves A alone.
- a **write sends value, addr, comp**.  Here the CPU must supply `comp` after all, because RAM's
  B is holding the value across the first half-lap; and the value has to go out *before*
  `lit(addr)`, which needs B as scratch.  A write therefore does **not** leave A holding the
  value, and callers that want it back must read it again.
"""

from __future__ import annotations

from gen.lay import lit
from gen.room_ram import (
    MODE_ADDR,
    MODE_MASK,
    MODE_PIPE,
    MODE_INP,
    MODE_MAP,
    MODE_NEXT,
    MODE_PUT,
    MODE_READ,
    MODE_ROT,
    MODE_RUN,
    MODE_WRITE,
    NFAST,
    RING,
)


def comp(a: int) -> int:
    return RING - 1 - a


def rd(a: int) -> str:
    """A = mem[a]."""
    return f"{lit(MODE_READ)}s{lit(a)}ssr"


def rd_at() -> str:
    """A = mem[A].  `M` parks the address in B while the single-digit mode goes out."""
    return f"M{lit(MODE_READ)}sWssr"


def wr(a: int) -> str:
    """mem[a] = A.  Does NOT leave A holding the value -- see the module docstring."""
    return f"M{lit(MODE_WRITE)}sWs{lit(a)}s{lit(comp(a))}s"


def _dsp(sel: int) -> str:
    """mode, selector, value -- three words out of one runtime value, which works only because both
    the mode and the selector are single digits and so leave B, holding the value, alone."""
    assert 0 <= sel <= 2
    return f"M{lit(MODE_ADDR)}s{sel}sWs"


def dsp_addr() -> str:
    return _dsp(0)


def dsp_data() -> str:
    return _dsp(1)


def dsp_swap() -> str:
    return _dsp(2)


def raster() -> str:
    """Paint a whole frame from the grid: RAM streams the 256 words and sends each colour to DATA.

    Leaves the ring's front where it started, because the lane's own loop is a full 256-word
    rotation -- the caller still has to `rot` past the ten fast words on either side.
    """
    return f"{lit(MODE_RUN)}s"


def inp() -> str:
    """A = the next round input value."""
    return f"{lit(MODE_INP)}sr"


# ---- streaming access.  A pop-and-push is a rotation by one, so walking the ring in order costs
# one head walk per word (~280 ticks) instead of a whole lap (~975).  The front has to be put back
# with `rot` when the pass ends, or every later random access lands on the wrong word.
def nxt() -> str:
    """A = the word at the ring's front, and advance one."""
    return f"{lit(MODE_NEXT)}sr"


def put() -> str:
    """Overwrite the word at the ring's front with A, and advance one."""
    return f"M{lit(MODE_PUT)}sWs"


def rot(n: int) -> str:
    """Rotate the ring by `n`, to put the front back at address zero."""
    return f"{lit(MODE_ROT)}s{lit(n)}s"


# ---- fast variables.  Addresses 0..9 need only a single-digit literal, and a single digit is the
# only load that leaves B intact -- see `docs/vault/heap/Only a single-digit payload preserves B.md`.
# So the interpreter's hot words live there, and everything that has to compare, subtract or classify
# keeps its operand in B across one of these reads.
def rdf(v: int) -> str:
    """A = mem[v] for v < NFAST, leaving B alone."""
    assert 0 <= v < NFAST, v
    return rd(v)


def wrf(v: int) -> str:
    """mem[v] = A for v < NFAST, leaving B alone until the value goes out."""
    assert 0 <= v < NFAST, v
    return f"M{lit(MODE_WRITE)}sWs{v}s{lit(comp(v))}s"


# > [!warning] A command's payload may not contain another command
# > A runtime-address write looks writable -- a fast read spares B, so `lit(base) M rdf(v) +` builds
# > the address and `lit(RING-1-base) M rdf(v) - N` the complement.  But `rdf` **is a bus command**,
# > so issuing it halfway through a write makes RAM read the nested read's own mode and address as
# > the outer write's address and complement.  Measured: RAM ends blocked on `r` waiting for a fourth
# > word while the CPU waits for a reply that will never come.
# >
# > The real limit is therefore: **one runtime value per command.**  A write needs value, address and
# > complement; only the value may be dynamic, and the other two have to be compile-time constants.
# > So the only way to write a *computed* address is `put`, which addresses the ring's front -- and
# > the front is exactly what a streaming pass moves.  Hence: a streaming pass may hold state only in
# > A, B and the backpack, and its restore count must be constant.


def map_read() -> str:
    """A = the word at the ring's front.  The caller MUST answer with a single `s`, which becomes the
    new value there; the front then advances by one, exactly like `nxt`/`put`."""
    return f"{lit(MODE_MAP)}sr"


def mask_row(rel: int) -> str:
    """Apply the mask in `mem[rel]` -- *front-relative* -- to the next sixteen ring words.

    RAM fetches it itself, because the CPU cannot carry a mask across the `rot` that puts the front on the
    row: `rot`'s count literal destroys A and B does not survive it either.  The fetch is a full lap, so
    the front is unchanged by it and then advances by exactly sixteen.
    """
    return f"{lit(MODE_MASK)}s{lit(rel)}s{lit(RING - 1 - rel)}s"


def pipe_row(rel: int) -> str:
    """The same command against the pipe lane: set bits become `PIPE_WORD`, clear ones keep the word."""
    return f"{lit(MODE_PIPE)}s{lit(rel)}s{lit(RING - 1 - rel)}s"
