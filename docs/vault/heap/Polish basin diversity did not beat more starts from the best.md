# Polish basin diversity did not beat more starts from the best

Stage-one islands do finish in distinct coordinate states, but spending half the fixed polish jobs
on those near-best states did not improve packing versus starting every polish island from the
single global-best floorplan.

## Experiment

The temporary implementation:

- collected each stage-one island's best `Floorplan`;
- realized and deduplicated exact `State`s;
- assigned half the polish jobs to the global best;
- distributed half across distinct near-best states;
- kept jobs and wall-clock budgets unchanged.

Commands used `--jobs 4 --seconds 3 --polish 3 --keep 1` with fixed seeds and the same release
binaries/room library.

### Sudoku validity

Eight seeds:

- all-global polish: `55, 49, 54, 53, 52, 53, 52, 52`
- diverse polish: `50, 53, 54, 53, 52, 51, 52, 52`

Median moved only from 52.5 to 52.0, while the best result regressed from 49 to 50. An alternative
basin won within the diverse run for only one seed, and that run was worse than the corresponding
all-global run (`53` versus `49`).

### Memory banked2

Three seeds:

- all-global polish: `39, 40, 41`
- diverse polish: `39, 41, 41`

An alternative basin won within one diverse run, but again lost to the corresponding all-global
allocation (`41` versus `40`).

Across all eleven paired runs there were seven ties, two improvements and two regressions. Distinct
stage-one states existed (normally three or four), so absence of diversity was not the issue. The
opportunity cost of taking polish chains away from the best stage-one state erased any benefit.

## Decision

Remove the experiment rather than retain a speculative 3-global/1-alternative split. Exact state
difference also overstates true basin diversity, and assigning alternatives to different island RNG
and temperature streams confounds attribution. If revisited, it needs a larger paired benchmark and
a basin-distance definition tied to topology, not exact coordinates.
