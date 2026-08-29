---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-26T14:15+03:00
---

`lmp`'s seeder tries **`COMBINATIONS = 16`** variant combinations, full stop
(`rs/crates/packer/src/seed.rs:50`). Its Latin sweep guarantees that every variant of every
instance has been tried at least once only within `max(variants per instance)` samples, and past
that it is seeded pseudo-random over the product space.

So **a big variant library makes seeding worse, not better.**

## Evidence

On `little-little-little-man`, `room_variants.py --limit 400` on the four wide rooms produced a
product space of about 10^20 combinations. Sixteen samples out of that never included the pin set
the pipe graph wanted, and every seed attempt failed with contested cells. Replacing it with about
ten curated variants per type — `py/lllm_rooms.py` — seeded on the first try and packed to
229x244, a 12.9x cut on the score.

## Consequences

- Keep each instance's variant list to **roughly ten**, and use `variants = [...]` in the
  `.eman.toml` to name them rather than letting the library default to everything.
- Spread the ten over **walls before offsets**. Sorting variant names and taking an even spread
  picks ten that differ in one offset, which gives the seeder nothing: on LLLM that silently
  dropped every `j`-east ROT and the design stopped seeding at all. `py/lllm_rooms.py` picks
  farthest-first over the *wall signature*, then fills the remaining slots with offsets inside
  each signature.
- When one room's wall is forced (see [[A room whose sends span it has only one pin wall]]), pin
  it in the netlist. Every combination spent on a variant that cannot work is one of sixteen.

## Related

- [[Packing a design with lmp]] — the designer loop this sits inside
- [[Read the packed aspect to choose the next pin wall]] — which wall to offer, once you know you
  can only offer a few
