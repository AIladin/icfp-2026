---
tags:
  - AI
  - llm
  - hypothesis
  - in-progress
date: 2026-07-26
---

# LLM rooms must load before they can route

The current `little-little-man/v1.eman.toml` is blocked before placement. After rebuilding `lmp`,

```bash
lmp programs/little-little-man/v1.eman.toml -c cases-llm.json \
  --logic-check --ticks 50000000
```

fails while loading the direct first-variant composition:

```
expected a digit or a space between backticks, but found '>' at (255, 413)
```

This is not synthetic-pipe timing. The component rooms themselves expose it:

- `rooms/llm-ram/v0.room`: first bad vertical literal span contains `r` at local `(5,16)`.
- `rooms/llm-cpu/v0.room`: first bad vertical literal span contains `>` at local `(7,136)`.
- CPU has 4,700 backticks and 4,750 non-digit cells inside the current sequential vertical pairs;
  this is structural, not one typo.
- The same CPU load failure exists in the original 752x795 pre-pipe room from commit `505882e`, so
  routing and the later pipe implementation did not introduce it.

This follows [[Backtick pairing is sequential per axis]]: every horizontal literal delimiter is
also considered in its column, independently. `llm_asm.Seq` stacks independently compiled boxes;
the boxes reuse literal columns and their delimiters pair through later control flow.

## Hypotheses under test

1. **Fill accidental vertical spans only on dead geometry.** Replacing a non-digit with a digit is
   legal only when no little man can cross it. This is practical for RAM's six offending cells, but
   not blindly for CPU: its offenders include 1,486 `s`, 780 `>`, 691 `v`, 510 `M`, 445 `W` and
   397 `r`, i.e. much of the executable CFG.
2. **Insert empty guard literals in blank cells — confirmed.** The useful formulation is parity,
   not local pairing: at every instruction cell, the number of preceding delimiters on each axis
   must be even. Scan each column and insert a delimiter in a blank row whenever the next instruction
   would be inside an accidental literal; then scan rows and repair their parity the same way. Prefer
   wholly blank rows, and otherwise the candidate row with the longest blank run around the column.
   Two vertical passes and one horizontal pass repaired CPU with **2,227 added delimiters** and RAM
   with **10**, without overwriting an instruction. Both repaired rooms pass `lmr check` standalone.
   The delimiters occupy formerly blank cells, but that alone is not enough: a walked closing
   delimiter can load the digits of a new vertical literal. A direction-aware CFG audit found one
   reachable non-empty vertical close at CPU `(135,577)`; forcing an adjacent empty pair moved it
   once to `(135,668)`. Fourteen additional parity guards eliminate both. The final static audit has
   zero reachable non-empty vertical closes in CPU and RAM, while horizontal literal effects are
   unchanged.
3. **Reset pairing at room boundaries.** The server and both runners reset literal scanning for each
   room. Splitting the CPU at top-level stages would solve parsing, but requires token handoff and a
   RAM-bus arbiter because every stage currently talks to the one RAM bus. Do not do this unless a
   direct literal-layout repair fails.
4. **Reuse the proven memory drum/head.** RAM's storage is already a 352-token ring and can likely be
   expressed using the server-confirmed `memory-*` room results instead of repairing the current RAM.
   This does not by itself solve CPU's literals.

## Routing state, only after load is fixed

The prior concrete `--check` did not finish its layered fallback. The hand hint still leaves nine
contested cells, principally the six north-facing RAM ports:

- `ram.bus_out > cpu.bus_in` vs `ram.ring_out > relay.ring_in`
- `ram.bus_out > cpu.bus_in` vs `relay.ring_out > ram.ring_in`
- `ram.disp > disp.cmd` vs `ram.ring_out > relay.ring_in`

Do not spend another ten-minute routing attempt until `--logic-check` is green. With all rooms now
loadable and the reachable-literal audit clean, the one-case check still reaches the real cap:

```text
logic check passes only 0/1 cases; first failure after 50000000 ticks: step cap
```

This is now a runtime/deadlock question, not a parser error. The synthetic checker makes every pipe
at least 256 cells, including the request/response bus; that may make this ring-RAM architecture
slower than a concrete layout, but the milestone remains a green 50M logic check as requested. A
green design must then pass concrete `--check`, `lmr test`, and `icfp submit --wait`.
