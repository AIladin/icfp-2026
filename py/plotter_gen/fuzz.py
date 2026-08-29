"""Feed many rounds of endpoints through the assembled program and diff every committed frame
against the reference Bresenham.  The public cases only cover 21 segments; private ones do not."""

import json
import subprocess
import sys

W, H = 32, 24


def reference(x0, y0, x1, y1):
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    px = []
    while True:
        px.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return px
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def frame_of(seg):
    on = set(reference(*seg))
    return ["".join("f" if (x, y) in on else "0" for x in range(W)) for y in range(H)]


def case_file(path, name, segs):
    """Rounds are gated on the frame, so the only faithful harness is `lm test` with a cases file."""
    rounds = [
        {"in": [str(v) for v in s], "out": [], "frames": [frame_of(s)]} for s in segs
    ]
    with open(path, "w") as fh:
        json.dump([{"name": name, "rounds": rounds}], fh)


def check(prog, segs, runner="lmr", tmp="/tmp/plotfuzz.json"):
    case_file(tmp, "fuzz", segs)
    out = subprocess.run(
        [runner, "test", prog, "-c", tmp, "--json"],
        capture_output=True, text=True, timeout=600,
    )
    r = json.loads(out.stdout)["results"][0]
    if r["passed"]:
        return []
    i = r["rounds_done"]
    return [(segs[i] if i < len(segs) else None, f"round {i}: {r['error']} {r['detail'][:60]}")]


def main() -> None:
    prog = sys.argv[1]
    runner = sys.argv[2] if len(sys.argv) > 2 else "lmr"
    corners = [(0, 0), (31, 0), (0, 23), (31, 23), (15, 11)]
    cases: list[list[tuple[int, int, int, int]]] = []
    cases.append([(a[0], a[1], b[0], b[1]) for a in corners for b in corners])
    cases.append([(x, 5, x, 5) for x in range(0, 32, 3)])          # zero length
    cases.append([(0, y, 31, y) for y in range(0, 24, 5)])          # horizontal ->
    cases.append([(31, y, 0, y) for y in range(0, 24, 5)])          # horizontal <-
    cases.append([(x, 0, x, 23) for x in range(0, 32, 7)])          # vertical v
    cases.append([(x, 23, x, 0) for x in range(0, 32, 7)])          # vertical ^
    cases.append([(15, 11, x, y) for x, y in [(16, 12), (14, 10), (16, 10), (14, 12), (16, 11), (15, 12)]])
    rng = 12345
    rnd = []
    for _ in range(24):
        vals = []
        for lim in (W, H, W, H):
            rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
            vals.append(rng % lim)
        rnd.append(tuple(vals))
    cases.append(rnd)

    total = 0
    for segs in cases:
        bad = check(prog, segs, runner)
        total += len(bad)
        for seg, why in bad:
            print("FAIL", seg, why)
    print("segments:", sum(len(c) for c in cases), "failures:", total)


if __name__ == "__main__":
    main()
