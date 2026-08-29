---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-26T12:25+03:00
---

> [!warning]
> `@` is a **no-op when you step on it**, not a turn. A loop whose return path walks back
> onto the spawn cell has no instruction there to restart it, and the man ping-pongs
> between whatever sits above and below forever.

## Symptom

A [[Step limit|step cap]] with no output at all, and a trace that shows one man
oscillating over three cells:

```
t=00212 (135,9)  S  A=3 B=1000 BP=0 '@'
t=00213 (135,10) N  A=3 B=1000 BP=0 '^'
t=00214 (135,9)  N  A=3 B=1000 BP=0 '@'
t=00215 (135,8)  S  A=3 B=1000 BP=0 'v'
```

The other men are all blocked on `r`, because the oscillating one is the only producer.
Nothing in the report points at the real cell — it looks like a slow program.

## Cause

The natural way to draw a one-man service loop is a column that collects every return
path and feeds it back into the code row:

```
 v      <- returns from above
 v
 @      <- "and here it starts again"
 ^      <- returns from below
 ^
```

The `@` reads as the loop's entry point because that is where the man *begins*, but
[[language-reference#Little Men|the spec only says]] it is where he spawns. Walking over
it later does nothing, so a man arriving from the `v` continues south onto the `^` and is
sent straight back.

`snake`'s HUB and DRAW rooms were both drawn this way. All four of HUB's return paths
(ring echo, draw prefix, input, input×16) ended in that bounce, which deadlocked the
whole machine before the first frame.

## Workaround

The join cell must be a real `>`, and the `@` needs its own stub that *feeds into* it.
Since a man always spawns heading **east** ([[Rotating a room breaks its spawn]]), the
stub is a couple of cells:

```
 @v     <- spawns east, immediately turns down column 2
  |
 >      <- THE JOIN: every return path restarts here
 ^
 <      <- stub rejoins the return column
```

`py/snake_gen3.py:hub` is the worked example. Costs two cells and one extra column.

## Related

- [[Men stop on contact]] — the other way a man silently stops being a producer
- [[Blocking]] — what every *other* man looks like while this one spins
