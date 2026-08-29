---
tags:
  - AI
  - concept
date: 2026-07-25T21:40+03:00
---

A **room library** turns a room from a block of characters inside one program into a reusable
component with a contract. `rooms/<type>/interface.toml` declares the ports a room type has;
`rooms/<type>/<variant>.room` is one implementation of that contract, marked up with
[[Room handoff markers]]. A `.eman.toml` netlist names instances and wires their ports, and `lmp`
compiles the two into a packed `.man` — see [[Packing a design with lmp]] for the workflow.

The point is that a room type can have **several variants that differ only in where their pins
sit**, and the packer picks between them. Which wall a pipe leaves by is a layout decision, not a
logic one, and this is what makes it one.

## `interface.toml` — the contract

```toml
description = "folds the five cell bits and the carry into the 0/1 answer"   # optional

[ports]
from_decode = "A"
from_cell5  = "B"
from_cell1  = "F"
out         = "y"
```

- **A port maps to one ASCII letter, and the letter's case is the direction** — lowercase means
  outgoing (a pipe *begins* here), uppercase means incoming (a pipe *ends* here). Same convention as
  the handoff markers, because it is the same convention.
- **Letters are local to the room type.** Two types may both use `a`. The packer builds the router's
  endpoint pairs from placements and port offsets and never stamps a letter into an assembled grid,
  so a design is not limited to 24 pipes.
- **`v` and `V` are reserved** — the router draws `v` as an arrowhead.
- Every variant must carry **exactly** these markers, one each. A missing, extra, duplicated or
  wrong-cased marker is a library load error naming the file and the letter.

## `.room` — one variant

The room box plus its port letters on the cells immediately outside the wall:

```
   A              B
+------------------+
|>@rrrM1+M2W/b`27`v|
|^v           {rM*<|
|^ >mds         v  |c
|^   >mds       v  |d
|^              <  |
+------------------+
                 h
```

Which wall and offset each letter sits on **is what varies between variants** — that is the entire
reason the format exists. `rooms/input/` ships `east.room`, `north.room`, `south.room` and
`west.room`: identical logic, four different pin walls.

Load also records, per variant:

- **the pad** each wall needs (2 where a pin sits, for the marker cell and its exit cell; 1
  otherwise, because two room boxes sharing a border is not a grid the room finder can read),
- **the binding intent**: for every interior `s`/`r`/`q`, which port it must resolve to, by the
  loader's own nearest-pipe rule. An exact tie is refused at load time — a tie is one repack away
  from a silently re-pointed send, which is exactly the failure
  [[The server can build a different pipe graph]] describes.

## `.eman.toml` — the netlist

```toml
problem = "sudoku-validity"

[rooms]
decode = "sudoku-decode"                                    # any variant, packer's choice
tail   = { type = "shuttle", variants = ["vertical-first"] } # pinned to one

[[pipes]]
from = "decode.bit1"     # must be an outgoing port
to   = "cell1.feed"      # must be an incoming port
min  = 257               # optional minimum length, for a delay line
```

Pipes are identified by their endpoints, never by letters. Every port of every instance must be
wired exactly once — an unwired port is a marker with no pipe, which is a mis-binding waiting to
happen, so the loader rejects it.

## What this does and does not buy

It buys **fast iteration**: change a room's logic once and every design using it picks the change
up, and `lmp --check` says in seconds whether it still wires up and still passes. It does not
replace [[Prefer manual packing]] — the hand-packed `sudoku-validity` is still 27 against the
packer's 44 — but it does mean nobody hand-packs a design whose *logic* is wrong, which is the same
gap [[Ephemeral pipes prove the logic, not the layout]] closes for a single marked `.man`.

The lever the library has and hand-packing does not is **variant count**. The packer can only
re-face a pin by substituting a variant, so a room type with one variant is a fixed constraint on
every layout that uses it. On the sudoku pilot, ten of the thirteen types ship exactly one variant,
and the search's own accounting says topology moves are rejected 95–99% of the time — the rooms are
holding the layout still. More variants per type is the next real win.

## Variant count is a Goldilocks number, not "more is better"

The paragraph above says more variants per type is the next real win. Two days of using the packer
in anger says that is only true up to about ten: [[lmp tries sixteen variant combinations]] and
past that the sweep is sampling a product space it cannot cover. On `little-little-little-man`,
four hundred variants per wide room *stopped the design seeding altogether* and ten curated ones
seeded first try, for a 12.9x score cut.

How many you can even have is a property of the room, not of the generator:
[[A room whose sends span it has only one pin wall]] — a 153x97 RAM whose six sends span 152
columns has **zero** legal re-pinnings, while a 10x12 ROT has 583. When a wall is forced, pin it in
the netlist so the sixteen combinations are not spent on variants that cannot work; when a room is
too wide to have options, the fix is to narrow the room
([[Column zones only need to beat the row term]]).
