---
tags:
  - AI
  - spec
  - confirmed
date: 2026-07-25T16:47+03:00
---

> `Y` splits the little man in two. The copies are born on the cells to his left and his right —
> left and right relative to his heading as he enters the `Y` — each heading away from the `Y`. The
> original man does not continue past the `Y`; only the two copies remain.
>
> — [[split#Y, precisely]]

`Y` is the first instruction that changes the **number** of little men in a room. Until now a room's
man count was fixed at load time by its single `@`, and [[One persistent register per room]] rested
on that. It no longer holds: a room can now hold as many workers as it can fit, all sharing the
room's cells and its pipes.

## The mechanics that matter

**Both copies inherit A, B and the backpack.** A split is a free duplication of state — no send, no
receive, no drum. Two men can carry the same value down two different lanes for the cost of one cell.

**The copies are born already placed and act on the next tick.** They execute the instruction they
are born on and then move, so the two birth cells are ordinary program text, not a prologue. A `Y`
with an instruction either side is a two-way fork, not a fork plus two wasted ticks.

**Heading determines the geometry.** Left and right are relative to the entering heading, and each
copy heads *away* from the `Y`. A man walking east splits into a north-bound copy and a south-bound
copy; the original does not continue east. So `Y` turns one east-bound lane into two perpendicular
lanes and consumes the original — it is a T-junction, not a branch that keeps going straight.

**Creation order is specified, and it is not what you would guess.** The right-hand copy *takes over
the splitting man's slot* in the order; the left-hand copy goes to the back, after every other man.
Since men act in creation order every tick, this fixes who wins a race — and races are now possible
in a way they never were before. See [[Tick order]].

## Death is cheap and is not an error

Four distinct ways for men to die, none of which end the program:

- a birth cell already holding a man — **both** die, the newborn and the occupant
- two men arriving on the same cell in the same tick
- two adjacent men swapping cells in the same tick (moving *through* each other)
- two `Y`s spawning onto the same cell

Only two things are errors: **a birth cell that is a wall**, and exceeding **65536 live men**.

That asymmetry is the design lever. A collision is a *usable primitive* — a way to retire a worker
without a halt, a way to gate one lane on another's arrival — while a wall birth is a hard failure.
Read it as: population may shrink freely, but it may never be born into stone.

## What this opens up

The obvious use is parallelism: [[Rooms run concurrently|per-item cost is MAX across rooms, not
SUM]], and that argument now applies *within* a room. A scan that costs one man N ticks can be split
across k men.

A split can also be the body of a counter: [[A Y loop spawns one worker per count]] emits one
state-carrying worker per backpack decrement.

The subtler use is that a `Y` plus a collision is a **synchronisation primitive**, which the language
previously lacked outside of blocking pipe ops. Two men that must meet can be made to annihilate.

## Implemented, and it reads as written

Both runners execute `Y` as of 2026-07-25T17:15+03:00 — `py/libs/runner/src/littleman/machine.py`
(`_split`, `_birth`, `_overlaps`, `_swaps`) and `rs/crates/littleman/src/machine.rs`, landed
together with matching tests (`tests/test_split.py`, `crates/littleman/tests/split.rs`) and parity
fixtures. Nothing above needed correcting: right of a heading is `dir + 1` clockwise, so an
east-bound man really does become a south-bound `men[0]` and a north-bound `men[1]`, and a copy born
onto a digit loads it on the next tick rather than walking past.

What the spec does *not* say, and what the runners chose, is in
[[Where the split spec runs out]] — read it before building on a race.

## Server-confirmed 2026-07-26

> [!note] Re-read against the live spec and the runners on 2026-07-26T02:3x
> Every clause above still matches `spec/split.md` and
> `py/libs/runner/src/littleman/machine.py` word for word — nothing here needed correcting.

**The judge runs `Y` the way we do.** `programs/sudoku-validity/v8-26x24.man` contains a `Y`
whose two copies are the whole mask computation, and it scored **20/20 on the server**
(submission `045c24b3-ab9b-4954-9b81-7769d33cf293`, 3,367,798). That exercises, on the
judge, in one program:

- both copies inheriting A and B (they carry `A = c` and `B = K` into two different lanes),
- copies executing the cell they are born on (each birth cell is a `>` that turns them),
- **creation order fixing a race** — the two men send into the same pipe and the receiver
  decodes the round by arrival order ([[Y buys back the concurrency a room merge spends]]),
- **a birth onto an occupant killing both, and it not being an error** — the lane that has no
  next round parks on `H`, and the following round's copy annihilates with it, which is the
  only reason the population does not grow by one man per round.

Local ticks predicted the server's within 1.4% (4,928 against 4,981.9), so the split is not
costing anything the runners do not model either.

> [!warning] Still unexercised
> Nothing above tests the 65536 limit, a wall birth, or two `Y`s spawning onto one cell.
