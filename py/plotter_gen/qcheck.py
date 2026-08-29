"""SETUP with a single FIFO: inputs are pre-seeded into the queue, results are left in it."""

import prog2 as sp
from setup_sim import cost

PROG = sp.PROG


def count(prog):
    c = {"s": 0, "r": 0, "cells": 0}
    for op, arg in prog:
        if op == "X":
            # worst arm for cells; all arms have equal push counts
            best = max(arg.values(), key=lambda a: sum(cost(o, g) for o, g in a))
            c["cells"] += 1 + sum(cost(o, g) for o, g in best)
            sub = count(best)
            c["s"] += sub["s"]
            c["r"] += sub["r"]
        else:
            c["cells"] += cost(op, arg)
            if op in c:
                c[op] += 1
    return c


def arms_equal(prog):
    for op, arg in prog:
        if op == "X":
            ns = {k: count(v)["s"] for k, v in arg.items()}
            nr = {k: count(v)["r"] for k, v in arg.items()}
            if len(set(ns.values())) > 1 or len(set(nr.values())) > 1:
                print("UNEQUAL ARMS", ns, nr)


arms_equal(PROG)
c = count(PROG)
print("cells(worst path)", c["cells"], "pushes", c["s"], "pops", c["r"])

print("K = pops-4 =", c["r"] - 4, " S-5 =", c["s"] - 5)
