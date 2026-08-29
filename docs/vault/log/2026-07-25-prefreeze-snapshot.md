---
tags:
  - AI
  - score
  - confirmed
date: 2026-07-25T12:25:11+03:00
---

Reference snapshot taken just before the lightning-round scoreboard freeze (~13:00 Kyiv,
lightning ends 15:00). During the freeze `icfp standings` stops updating, so a static `best`
does **not** mean rivals stopped and a static rank does **not** mean a submission failed —
compare against these numbers, and trust only `icfp submit --wait` / `icfp status` results.

```
triangle  rank 1/198  score 832  best 832  tied for the lead
memory  rank 14/114  score 26,890,632  best 9,547,949  2.82x off
reverse-a-list  rank 33/117  score 148,346  best 67,308  2.20x off
sort-numbers  rank 19/80  score 786,785  best 316,351  2.49x off
history-lesson  rank 19/99  score 7,225  best 5,929  1.22x off
brackets  rank 16/66  score 275,860  best 67,230  4.10x off
tcp  rank 5/53  score 804,500  best 340,160  2.37x off
plotter  rank 1/49  score 6,321,946  best 6,321,946  tied for the lead
gradebook  rank 2/40  score 200,067,214  best 81,537,120  2.45x off
matmul  rank 7/41  score 48,508,544  best 16,766,880  2.89x off
sudoku-validity  rank 14/49  score 3,750,085  best 1,517,824  2.47x off
subset-sum  rank 4/36  score 6,152,068,609  best 499,423,781  12.32x off

overall  rank 5/201  22.41 points
```
