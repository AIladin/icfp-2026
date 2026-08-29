"""Does the 5-way decode route v to the right lane, and is the mask shifted right?

Lane j emits `m << (27 * parity)` -- so one round's output identifies both the lane taken
and the shift applied. The cell/HEAD2 halves are already verified against a Python model;
this is the only piece whose behaviour is geometric.
"""

import gen
from gen import put, room, row
from lay import io_room, path_pipe
from v5rooms import CORE_HEAD

# One OUTPUT, so every lane sends to the same place: `s` is fine, the lanes just have to
# reach it, which also proves each lane is actually entered.
cs, top, xm = 3, 3, 20
room(0, 0, 14, 22)
put(1, 1, "@")
row(1, 2, CORE_HEAD)
put(1, 2 + len(CORE_HEAD), "v")
put(2, 2 + len(CORE_HEAD), "<")
put(2, cs, "v")
for k in range(5):
    r, c = top + k, cs + 2 * k
    put(r, c, ">")
    row(r, c + 1, "md")
    put(r, c + 3, " ")  # pass m' through untouched, to check the shift
    put(r, xm, "v" if k < 4 else "s")
put(top + 5, xm, "<")
put(top + 5, 1, "^")
for r in range(top, top + 5):
    put(r, 1, "^")

io_room(0, 25, "I")
path_pipe([(1, 24), (1, 23)])     # INPUT west wall -> room east wall
io_room(10, 25, "O")
path_pipe([(11, 23), (11, 24)])   # room east wall -> OUTPUT west wall

if __name__ == "__main__":
    import sys
    open(sys.argv[1], "w").write(gen.render() + "\n")
    print(gen.render())
