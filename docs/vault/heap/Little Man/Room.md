---
tags:
  - AI
  - concept
aliases:
  - Rooms
---

A rectangle drawn with `+` at the corners, `-` on horizontal borders and `|` on vertical ones. It is
the only place a little man may exist, and he can never leave it.

- A man spawns at every `@` **inside** a room; at most one `@` per room.
- Rooms may not overlap or nest.
- Stepping onto a border is a `wall` [[Runtime errors|error]].
- A room's interior is its entire address space: all control flow is the man walking his own grid.

Special rooms:

- **[[Input and output rooms|I/O rooms]]** — 3×3 (walls included) with a single interior `I` or `O`.
- **[[Display pipes|LM-75 display]]** — drawn with `+`, `:`, `=`; not a room a man can enter.

Rooms talk to each other only through [[Pipes]] — and that is the *only* interaction between men,
since [[Men stop on contact|no two men can ever touch]].

## Design consequence

The room is the unit of concurrency: one man, one program counter, three registers
([[Little man state]]). Anything that needs parallelism or a second "thread" needs a second room and
a pipe between them — which also means anything that needs more than three live values needs to park
them in a pipe or in a neighbouring room.
