---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-27T13:30+03:00
---

> [!warning]
> A lane's `r`/`s` resolves to the **nearest marker in Manhattan distance**, and a marker on the *south*
> wall gets closer the deeper the lane sits. Past a computable row, a ring lane silently starts talking
> to the input pipe instead of the ring.

## Symptom

A new lane added 500 rows below a working one deadlocks. `--logic-trace` shows the ring completely
backed up -- 351 of 352 words in the two legs, `relay.ring_out>ram.ring_in=190/190`, and RAM blocked on
a send it can never complete. Every `r` in the lane returns a value; none of them come from the ring.

## Cause

`binding_intent` (`rs/crates/packer/src/library.rs:369`) measures from the instruction cell to the port
*marker* cell, in the room's own box. For RAM those candidates are the ring's `Q` on the **west** wall at
row 300 and the round input's `F` on the **south** wall at row `H + 2`. For a cell at `(col, y)`:

```
d(Q) = col + 1 + (y - 300)
d(F) = (100 - col) + (H + 2 - y)
```

The ring wins only while `col + y < (H + 402) / 2` — **1750 at H = 3100**. The mask lane's blocks at
`col 46, y 1400` clear it by 300; the same blocks at `y 1900` lose by 150, and every one of them receives
from the input pipe.

This is the *row* term that [[Alternating pipe parity gives a lane its own up and down]] relies on
cancelling. Two markers on opposite walls at one row cancel it and leave binding by column alone — but a
marker on a *perpendicular* wall never cancels, so it dominates any lane far enough from the row it
shares with its partner.

## Workaround

Give the second lane its **own columns in the same row band**, not the same columns further down. It
cannot stack anyway: a rotator is 42 columns wide and reaches 258 rows above its spine
([[Rotate a drum by walking the count's bits]]), so a lane below the first needs ~600 clear rows and only
~240 fit above the binding limit.

Then check the band against every *other* lane's spine row — see
[[A dive corridor is blank, so nothing objects until run time]].

## Related

- [[Only a single-digit payload preserves B]] — the other rule that decides where a drum's words live
- [[A drum's ring length is free]] — why `H` is large enough for this to bite in the first place
