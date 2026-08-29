"""Replay the accepted lmr-validated deletions from the interrupted LLLM shrink run."""

from pathlib import Path

SOURCE = Path("../programs/lllm-16215808236-227x223.man")
OUT = Path("../programs/little-little-little-man/baseline-partial-shrunk.man")
ROW_OUT = Path("../programs/little-little-little-man/baseline-row-shrunk.man")
ROWS = [217,216,215,214,213,212,211,210,209,208,207,180,178,176,174,172,166,165,164,163,162,161,157,156,152,144,143,139,129,127,111,108,104,103,100,54,53,49,48,46,44,43,42,41,40,39,38,37,36,35,33,32,23,22,21,20,19,18,14,13]
COLS = [223,222,207,205,203,201,198,196,195,194,193,191,181,176,175,173,172,171,170,149,148,147,146,143,131,130,129,120,119,118,117,116,115,114,113,112,111,110,109,108]

lines = SOURCE.read_text().splitlines()
width = max(map(len, lines))
grid = [list(line.ljust(width)) for line in lines]
for row in ROWS:
    del grid[row]
ROW_OUT.write_text("\n".join("".join(row).rstrip() for row in grid) + "\n")
for col in COLS:
    for row in grid:
        del row[col]
OUT.write_text("\n".join("".join(row).rstrip() for row in grid) + "\n")
print(f"wrote {OUT}: {len(grid)}x{len(grid[0])}")
