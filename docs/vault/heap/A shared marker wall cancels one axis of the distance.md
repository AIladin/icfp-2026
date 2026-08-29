---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26
---

When **every** marker an `s` or `r` can bind to sits on the *same* wall of the room, the Manhattan
distance to each of them carries the *same* perpendicular term, and that term cancels. Only the
coordinate **along** the wall decides the binding — however tall or wide the room grows.

## Why it matters

It is the difference between separating ports by tens of cells and separating them by two or three.
On `pathfinder`, SEQ has six pipes and all six markers are on its north wall, so ports are herded
into per-pipe column bands. Those bands were 140 columns wide, sized as if the 200-row height of the
room entered the comparison. It never did:

$$d = |p_x - m_x| + (p_y - (y_0-1))$$

and the second term is identical for every marker on that wall. Rescaling the bands to a third of
SEQ's width took the room from **828x211 to 128x181** and, because a band switch pads with `.` cells
the little man then has to *walk*, it cut ticks at the same time.

The same argument shrank two more rooms in the same session:

| room | markers | old separation | needed |
| --- | --- | --- | --- |
| SEQ | 6, all north | 140-col bands | ~1/3 of the width |
| FLG | `q`, `u`, both south | 12 nop cells | 2 |
| DRAW | `a`, `m`, `k`, all south | 15 and 32 cells | 3 |

DRAW is the extreme case: its three `s` cells are on three adjacent rows and the markers drop
straight south, so the rows differ by one and **any** column gap is decisive.

## The condition, precisely

It holds per *direction*: `s` ranks only outgoing pipes and `r` only incoming
([[Room handoff markers]]), so the wall has to be shared only within one of those two sets. A room
whose outgoing markers are all south and whose incoming markers are all north gets the cancellation
twice, independently.

It fails the moment one marker moves to another wall — then the perpendicular terms differ and the
full two-dimensional comparison is back. That is what forced FLG's `f` to keep a real margin while
`q` and `u` needed almost none.

## Evidence

`py/pf/build.py` prints the whole table under `--audit`: every `r`/`s`, the marker it binds to, and
the margin to the runner-up. Footprint 727,609 -> 39,601 over the session, with
[[A lane needs five rows, not six]] and [[Padding a room's arms is paid by every token]].
