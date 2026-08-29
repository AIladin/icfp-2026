"""Score a .man against cases.json, printing one compact line."""

import json
import subprocess
import sys

S = "/tmp/claude-1000/-home-ailadin-projects-icfp-2026/ae2fa534-4cad-4238-b35e-775bb9a1bdce/scratchpad/sudoku-validity"
CASES = f"{S}/cases.json"


def run(path, tool="lmr"):
    p = subprocess.run(
        [tool, "test", path, "-c", CASES, "--json"], capture_output=True, text=True
    )
    if not p.stdout.strip():
        return None, p.stderr.strip()[:400]
    d = json.loads(p.stdout)
    return d, None


def main():
    path = sys.argv[1]
    tool = sys.argv[2] if len(sys.argv) > 2 else "lmr"
    d, err = run(path, tool)
    if d is None:
        print("ERROR:", err)
        return
    bad = [r["case"] for r in d["results"] if not r["passed"]]
    ticks = [r["ticks"] for r in d["results"]]
    rounds = [len(r["expected"]) for r in d["results"]]
    per = [round(t / n, 1) for t, n in zip(ticks, rounds)]
    print(f"footprint={d['footprint']} score={d['score']:.0f} fail={bad}")
    print("ticks", ticks)
    print("per-round", per)
    if bad:
        for r in d["results"]:
            if not r["passed"]:
                o, e = r["output"], r["expected"]
                i = next((k for k in range(min(len(o), len(e))) if o[k] != e[k]), min(len(o), len(e)))
                print(f"  {r['case']}: idx {i} got {o[i:i+3]} want {e[i:i+3]} lens {len(o)}/{len(e)}")
                print(f"    error={r.get('error')}")
                break


if __name__ == "__main__":
    main()
