"""stage1: drawing engine sandbox -- CONST rooms feed P/Q with hardcoded constants."""

import sys

sys.path.insert(0, "/tmp/claude-1000/-home-ailadin-projects-icfp-2026/ae2fa534-4cad-4238-b35e-775bb9a1bdce/scratchpad/plotter")
from canvas import Canvas, hline, vline

SCR = "/tmp/claude-1000/-home-ailadin-projects-icfp-2026/ae2fa534-4cad-4238-b35e-775bb9a1bdce/scratchpad/plotter/"

c = Canvas(110, 70)

# ---------------- display (62,14)-(95,39) ----------------
c.display(62, 14, 95, 39)

# ---------------- EMIT: mask -> ADDR, then 15 -> DATA ; box (34,4)-(53,7) ----------------
c.room(34, 4, 53, 7)
c.text(35, 5, "@`1023`M")
c.text(46, 5, ">r&s  v")
c.text(46, 6, "^s`51`<")   # walked west this loads 15

# ---------------- P ; box (10,46)-(18,55) ----------------
c.room(10, 46, 18, 55)
c.text(11, 47, ">sd0s v")
c.text(13, 48, "m")
c.text(12, 49, "vX+v")
c.text(12, 50, "v< v")
c.text(12, 51, ">srv")
c.text(11, 52, "^<<<<")
c.text(11, 53, "@")
c.put(17, 53, "v")
c.text(11, 54, "^rMrbr<")

# ---------------- Q ; box (30,46)-(38,51) ----------------
c.room(30, 46, 38, 51)
c.text(31, 47, ">r+smdv")
c.put(31, 48, "^")
c.put(36, 48, "<")
c.text(31, 49, "^ Mrbr<")
c.text(31, 50, "@")
c.put(37, 50, "^")

# ---------------- const stubs: (3,4)-(9,12) ----------------
c.room(10, 58, 34, 61)
c.text(11, 59, "@8s`12320`s`4227`s")
c.put(29, 59, "v")
c.put(29, 60, "^")

c.room(80, 44, 106, 47)
c.text(81, 45, "@6s`4063`Ns")
c.put(92, 45, "v")
c.put(92, 46, "^")

# ---------------- pipes ----------------
c.pipe(vline(11, 45, 8) + hline(8, 12, 33) + vline(33, 7, 5), final=(1, 0))       # P -> EMIT
c.pipe(vline(50, 3, 2) + hline(2, 51, 70) + vline(70, 3, 13), final=(0, 1))       # ADDR
c.pipe(vline(47, 8, 20) + hline(20, 48, 61), final=(1, 0))                        # DATA
c.pipe(vline(16, 45, 44) + hline(44, 17, 75) + vline(75, 43, 40), final=(0, -1))  # SWAP
c.pipe(hline(51, 19, 29) + vline(29, 50, 47), final=(1, 0))                       # PQ
c.pipe(vline(36, 52, 63) + hline(63, 35, 9) + vline(9, 62, 49), final=(1, 0))     # QP
c.pipe(vline(16, 57, 56), final=(0, -1))                                          # SP
c.pipe(hline(45, 79, 39) + vline(39, 46, 49), final=(-1, 0))                      # SQ

open(SCR + "stage1.man", "w").write(c.render())
print("written")
