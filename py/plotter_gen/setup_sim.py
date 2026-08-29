"""Simulate the SETUP man: registers A,B, an input pipe, and one FIFO echo queue.

Ops are written as a list of (mnemonic, arg) so the tick count is the list length
(literals count as len(str)+2 cells for the backticks, 1 for a single digit).
Branches are expressed with ('X', {'+': [...], '-': [...], '0': [...]}) -- the three arms.
"""

from collections import deque


class M:
    def __init__(self, inp):
        self.A = 0
        self.B = 0
        self.inp = deque(inp)
        self.Q = deque()
        self.out = []          # values pushed to the "result" pipe
        self.ticks = 0

    def run(self, prog):
        for op, arg in prog:
            self.ticks += cost(op, arg)
            if op == "ri":
                self.A = self.inp.popleft()
            elif op == "r":
                self.A = self.Q.popleft()
            elif op == "s":
                self.Q.append(self.A)
            elif op == "o":
                self.out.append(self.A)
            elif op == "M":
                self.B = self.A
            elif op == "W":
                self.A, self.B = self.B, self.A
            elif op == "+":
                self.A = self.A + self.B
            elif op == "-":
                self.A = self.A - self.B
            elif op == "*":
                self.A = self.A * self.B
            elif op == "N":
                self.A = -self.A
            elif op == "{":
                self.A = self.A << self.B
            elif op == "}":
                self.A = self.A >> self.B
            elif op == "L":
                self.A = arg
            elif op == "X":
                key = "+" if self.A > 0 else ("-" if self.A < 0 else "0")
                self.run(arg[key])
            else:
                raise ValueError(op)
        return self


def cost(op, arg):
    if op == "L":
        return 1 if 0 <= arg <= 9 else len(str(arg)) + 2
    if op == "X":
        return 1  # arms costed inside
    return 1
