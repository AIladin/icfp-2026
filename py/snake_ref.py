"""Reference Snake, used to check what the five public cases actually exercise.

Not part of any program -- it exists so the generator's BLOCKS can be designed
against real numbers instead of against a reading of the spec.
"""

import json
import sys

DIRS = {2: (0, -1), 3: (1, 0), 4: (0, 1), 5: (-1, 0)}


def play(tokens: list[int]) -> tuple[list[list[str]], dict[str, int]]:
    """Replay a case's flat input.  Returns the frames and a feature tally."""
    seen = {"grow": 0, "wall": 0, "self": 0, "onto_tail": 0, "maxlen": 1, "ticks": 0}
    it = iter(tokens)
    sx, sy = next(it), next(it)
    body = [(sx, sy)]                     # tail first, head last
    dx, dy = 1, 0
    fruit: tuple[int, int] | None = None
    over = False
    frames = [render(body, fruit, over)]

    for v in it:
        if v == 1:
            fruit = (next(it), next(it))
            frames.append(render(body, fruit, over))
            continue
        if v in DIRS:
            dx, dy = DIRS[v]
            continue
        if v != 0:
            raise ValueError(f"bad round token {v}")

        seen["ticks"] += 1
        hx, hy = body[-1]
        nx, ny = hx + dx, hy + dy
        if not (0 <= nx < 16 and 0 <= ny < 16):
            seen["wall"] += 1
            over = True
        elif (nx, ny) == fruit:
            seen["grow"] += 1
            body.append((nx, ny))
            fruit = None
        elif (nx, ny) in body[1:]:
            seen["self"] += 1
            over = True
        else:
            if (nx, ny) == body[0] and len(body) > 1:
                seen["onto_tail"] += 1
            body = body[1:] + [(nx, ny)]
        seen["maxlen"] = max(seen["maxlen"], len(body))
        frames.append(render(body, fruit, over))
        if over:
            break
    return frames, seen


def render(body, fruit, over) -> list[str]:
    g = [[0] * 16 for _ in range(16)]
    if fruit is not None:
        g[fruit[1]][fruit[0]] = 9
    for x, y in body:
        g[y][x] = 9 if over else 10
    return ["".join(f"{c:x}" for c in row) for row in g]


def main() -> None:
    cases = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "cases-snake.json"))
    for c in cases:
        toks = [int(v) for r in c["rounds"] for v in r["in"]]
        want = [f for r in c["rounds"] for f in r["frames"]]
        got, seen = play(toks)
        ok = "OK " if got == want else "BAD"
        print(f"{ok} {c['name']:<24} frames={len(got):>3}/{len(want):<3} {seen}")


if __name__ == "__main__":
    main()
