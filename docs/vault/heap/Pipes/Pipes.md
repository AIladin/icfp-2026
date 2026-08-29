---
tags:
  - AI
  - concept
---

A pipe is a unidirectional connection between two [[Room|rooms]] — the only way little men
communicate, the only way a program does I/O, and the only storage larger than a man's three
registers. A room may have arbitrarily many pipes attached.

## Rules from the spec

- [[Pipe drawing rules]] — arrowheads, body glyphs, where a pipe starts and ends
- [[Pipe timing and capacity]] — one value per cell, one cell per tick; capacity = latency = length
- [[Send and receive]] — `s` `S` `r` `R` `U`, and what each blocks on
- [[Nearest pipe resolution]] — Manhattan distance from the instruction, reading-order tie-break
- [[Send and receive rank different pipes]] — one pipe in and one out is unambiguous at any room size

## Gotchas

- [[Pipe drawing traps]] — the four documented load errors
- [[A terminal arrowhead may also be a bend]] — the last arrowhead can turn, so the entry
  direction is not the direction of the last hop

## Consumers

- [[Input and output rooms]] — I/O is just a pipe to a special room
- [[LM-75 Display]] — the pipe's *side* selects ADDR / DATA / SWAP

## Design notes

Pipes carry three separable roles that would be distinct mechanisms in a normal machine:
**communication** (room to room), **storage** (a pipe is a FIFO you can park values in), and
**timing** (length is latency, and back-pressure is the only flow control). Any design decision about
pipe layout is really a decision about all three at once.

## Related

- [[Little Man]] — the execution model
- [[Blocking]] — the only synchronisation primitive

## Laying pipe logic into a room
- [[Column zones only need to beat the row term]] — how far apart same-wall pins actually need to be
- [[A room whose sends span it has only one pin wall]] — when a room has no re-pinning at all
- [[An If arm is a copy of its body]] — why pipe *handling* code blows a room up if written naively
