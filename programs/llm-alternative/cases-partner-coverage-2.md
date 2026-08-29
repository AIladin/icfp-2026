# Partner coverage suite 2

`cases-partner-coverage-2.json` extends coverage beyond the first suite with comparator rotation from
a non-east heading, per-man registers, queue ordering, simultaneous-send contention, pipe freezing,
per-man nearest binding and a nearest-distance tie. Every program was built from scratch.

## Validation

```sh
cd py
uv run python llm_model.py ../programs/llm-alternative/cases-partner-coverage-2.json
# 70/70 frames

cd ..
lmr test programs/llm-alternative/solution.man \
  -c programs/llm-alternative/cases-partner-coverage-2.json
# passed 0/11; footprint 1787569
```

| ID | Case | Reference | Current replay | Ticks |
| --- | --- | ---: | ---: | ---: |
| 2.01 | positive X from south | 6/6 | 0/6 | 15,767 |
| 2.02 | negative X from south | 6/6 | 0/6 | 16,097 |
| 2.03 | independent per-man registers | 5/5 | 0/5 | 14,732 |
| 2.04 | capacity-three FIFO | 17/17 | 0/17 | 22,567 |
| 2.05 | simultaneous send contention | 5/5 | 0/5 | 21,503 |
| 2.06 | all halted freezes pipe | 5/5 | 0/5 | 18,439 |
| 2.07 | wall stop freezes pipe | 5/5 | 0/5 | 20,167 |
| 2.08 | two men choose outgoing pipes | 5/5 | 0/5 | 21,721 |
| 2.09 | two men choose incoming pipes | 5/5 | 0/5 | 22,169 |
| 2.10 | equidistant outgoing tie | 5/5 | 0/5 | 20,647 |
| 2.11 | zero value through pipe | 6/6 | 0/6 | 17,463 |

## Coverage matrix

| ID | Rooms / men / pipes | Primary semantics | Checked invariant |
| --- | ---: | --- | --- |
| 2.01 | 1 / 1 / 0 | `X` with A>0 while heading south | clockwise turn is west; A=3 |
| 2.02 | 1 / 1 / 0 | `X` with A<0 while heading south | counter-clockwise turn is east; A=-3 |
| 2.03 | 1 / 2 / 0 | independent A/B state | final `(A,B)` values are `(5,2)` and `(-7,8)` |
| 2.04 | 2 / 2 / 1 | length-three capacity and FIFO | receiver consumes exactly 1, 2, 3 |
| 2.05 | 2 / 3 / 1 | two `s` on one head in one tick | later man's 7 wins; receiver arithmetic reaches zero |
| 2.06 | 2 / 1 / 1 | all men halted | in-flight 9 remains frozen in pipe cell 2 |
| 2.07 | 2 / 2 / 1 | global wall stop | wall freezes both men and an in-flight pipe value |
| 2.08 | 3 / 4 / 2 | nearest outgoing per man | left/right men independently deliver 4/7 |
| 2.09 | 3 / 4 / 2 | nearest incoming per man | left/right receivers independently obtain 4/7 |
| 2.10 | 3 / 3 / 2 | equal-distance outgoing tie | first parsed (left) pipe wins |
| 2.11 | 2 / 2 / 1 | zero versus empty pipe cell | zero transits, is received, and takes X's straight arm |

Schedules include both one-tick traces and mixed `k` values up to 5. Together, coverage suites 1 and
2 contain 23 novel programs and 193 reference-validated frames.
