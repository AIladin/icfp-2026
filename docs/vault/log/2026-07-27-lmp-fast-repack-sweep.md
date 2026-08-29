---
tags:
  - AI
  - log
date: 2026-07-27
---

# Fast `lmp` repack sweep after band compaction

One-shot supervisor sweep requested after [[lmp band compaction]] landed. The sweep excluded
`little-little-man`. It used only existing solution-shaped netlists, one job per run, and wrote to
`/tmp/lmp-repack` so no preserved artifact could be overwritten:

```bash
lmp <design> -c <cases> -o /tmp/lmp-repack/<task>.man \
  --seconds 5 --polish 1 --compact-seconds 5 --keep 1 --jobs 1
```

## Results

| Task/netlist | Result | Compaction | Comparison with verified fallback |
|---|---|---|---|
| Brackets `v30-sentinel-narrow` | 20x18, local 89,289, 9/9 | 20→20; no accepted cut | Worse than safe 17x17 local 75,429 and numerical fallback local 56,997 |
| History `four/direct` | 103x102, local 3,562,385,501, 1/1 | 105→103; 3 accepted passes | Far worse than 81x81 fallback |
| Memory `banked2-sbs` | 28x35, local 4,704,175, 7/7 | 35→35; no accepted cut | Worse than 30x30 fallback local 3,344,400 |
| Reverse `ring4` | 18x18, local 42,242, 8/8 | 18→18; no accepted cut | Worse than hand-packed 15x15 local 29,138 |
| Sort `v4` | 19x22, local 949,746, 7/7 | 22→22; no accepted cut | Worse than hand-packed 16x16 local 389,632 |
| Sudoku `sudoku.eman` | 56x51, local 36,126,720, 6/6 | 61→56; 13 accepted passes | Dramatic pack improvement, but far worse than 21x21 fallback local 1,858,521 |
| LLLM `v5` | no seed | not reached | Existing single-layer conflict remains |
| Snake `inc` | no seed | not reached | Existing exact short-pipe seed conflict remains |
| TCP `fan` | no seed | not reached | Existing parallel-lane single-layer conflict remains |

History `combined.eman.toml` and `folded.eman.toml` refer to room types no longer present in their
nearest room library, so they were not runnable exact designs. The `four/direct` netlist was the
runnable History control.

No exact solution netlist exists for the latest hand-generated Triangle, Pathfinder, Matmul,
Plotter, Gradebook, numerical Brackets, server-winning Reverse, server-winning Sort, or server-winning
Sudoku layouts. Subset-sum has only the known seeding-bug probe, not a complete winner netlist.

## Verdict

Band compaction is effective on arrangement-bound old packs (History 105→103 and Sudoku 61→56), but
none of the swept outputs beats the corresponding preserved server fallback. No server submission
was made. Do not repeat this broad sweep without a new exact winner netlist or a materially changed
compactor.
