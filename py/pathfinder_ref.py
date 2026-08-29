"""Reference model for `pathfinder`: BFS from the flag, downhill walk with the
up/right/down/left tie-break, frames rendered exactly as the judge expects."""

from __future__ import annotations

import json
import sys
from collections import deque

W = 16
DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))  # up, right, down, left -- priority order


def bfs_from(flag: int, wall: list[int]) -> list[int]:
    """dist[i] = steps from cell i to `flag`, or -1 if unreachable."""
    dist = [-1] * 256
    dist[flag] = 0
    q = deque([flag])
    while q:
        i = q.popleft()
        x, y = i % W, i // W
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            j = ny * W + nx
            if 0 <= nx < W and 0 <= ny < W and not wall[j] and dist[j] < 0:
                dist[j] = dist[i] + 1
                q.append(j)
    return dist


def render(wall: list[int], robot: int, flag: int | None) -> list[str]:
    px = [7 if w else 0 for w in wall]
    if flag is not None and flag != robot:
        px[flag] = 9
    px[robot] = 10
    return ["".join("%x" % px[y * W + x] for x in range(W)) for y in range(W)]


def run_case(case: dict) -> list[list[str]]:
    rounds = case["rounds"]
    vals = [int(v) for v in rounds[0]["in"]]
    wall = vals[:256]
    rx, ry = vals[256], vals[257]
    robot = ry * W + rx
    frames = [render(wall, robot, None)]
    for rnd in rounds[1:]:
        fx, fy = (int(v) for v in rnd["in"])
        flag = fy * W + fx
        dist = bfs_from(flag, wall)
        while robot != flag:
            d = dist[robot]
            x, y = robot % W, robot // W
            for dx, dy in DIRS:
                j = (y + dy) * W + (x + dx)
                if 0 <= x + dx < W and 0 <= y + dy < W and dist[j] == d - 1:
                    robot = j
                    break
            else:
                raise AssertionError("stuck")
            frames.append(render(wall, robot, flag))
    return frames


def main() -> None:
    path = sys.argv[1]
    cases = json.load(open(path))
    for case in cases:
        got = run_case(case)
        want = [f for rnd in case["rounds"] for f in rnd["frames"]]
        ok = got == want
        print(f"{case['name']:24s} frames={len(got):3d} expected={len(want):3d} {'OK' if ok else 'MISMATCH'}")
        if not ok:
            for i, (g, w) in enumerate(zip(got, want)):
                if g != w:
                    print(f"  first mismatch at frame {i}")
                    for a, b in zip(g, w):
                        print(f"   got {a}   want {b}   {'' if a == b else '<<'}")
                    break


if __name__ == "__main__":
    main()
