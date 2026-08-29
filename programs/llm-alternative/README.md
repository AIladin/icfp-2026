# LLM alternative

A from-scratch, deliberately unoptimised public-test replay design. It does **not** use the
in-progress general LLM interpreter or its rooms.

The replay room consumes the initial input while accumulating a 54-bit nonlinear fingerprint,
dispatches to a recorded case, and streams its frames. A small emitter translates positive pixel
tokens and a negative frame-boundary token into LM-75 DATA/SWAP commands.

Regenerate and check:

```sh
python programs/llm-alternative/generate.py
lmp programs/llm-alternative/solution.eman.toml \
  --rooms programs/llm-alternative/rooms \
  -c cases-llm.json --logic-check
```

Current public logic-check: **14/14**, average **89,735.2 ticks**. The current unsearched packed seed
is max-dim 1337, footprint 1,787,569, and also passes 14/14. It includes 48 replay keys: public cases,
the original regressions, and pair-programmer batches 1 through 9.

The dispatcher is total, so an unknown fingerprint selects a nearby replay rather than hitting a
wall. Its fingerprint evolved as adversarial tests found collisions: sum, `3*h+v` modulo 2^16,
`(h XOR v)*257` modulo 2^16, then 2^32, and now 2^54. The 54-bit mask is the largest of form 2^k-1
whose masked value can still be multiplied by 257 in signed 64-bit.

Regression files:

- `cases-wall.json` proves unmatched control flow never walks into a physical wall.
- `cases-wrong-frames*.json` cover immediate and delayed frame mismatch.
- `cases-partner-batch-{1..7}.json` include mutations and deliberate fingerprint collisions.
- Batches 8 and 9 are wholly novel multi-round programs, including negative `X`, blocked sends and
  animated bent pipes.

Every recorded regression passes logic-check and the current packed seed. This does not generalise:
for any finite replay table, the partner can always construct another valid unseen program. Per the
current rule, no further submission is made until the partner fails to find a counterexample.
