"""Generate deterministic gradebook stress cases with conventional expected outputs."""

import json
import random
import sys


def make_case(rng: random.Random, case_no: int) -> dict[str, object]:
    n = 16 if case_no == 0 else rng.randint(4, 16)
    k = 4 if case_no == 0 else rng.randint(1, 4)
    ids = rng.sample(range(1000, 10000), n)
    grades = {student: [rng.randint(0, 100) for _ in range(k)] for student in ids}
    roster = [str(x) for pair in ([n, k], *([student, *grades[student]] for student in ids)) for x in pair]
    rounds: list[dict[str, list[str]]] = [{"in": roster, "out": []}]

    for _ in range(10):
        incoming = ["8"]
        outgoing: list[str] = []
        for _ in range(8):
            op = rng.randint(1, 4)
            subject = rng.randrange(k)
            student = rng.choice(ids)
            if op == 1:
                incoming.extend(("1", str(student), str(subject + 1)))
                outgoing.append(str(grades[student][subject]))
            elif op == 2:
                value = rng.randint(0, 100)
                incoming.extend(("2", str(student), str(subject + 1), str(value)))
                grades[student][subject] = value
            elif op == 3:
                incoming.extend(("3", str(subject + 1)))
                outgoing.append(str(sum(row[subject] for row in grades.values()) // n))
            else:
                incoming.extend(("4", str(subject + 1)))
                best = min(ids, key=lambda sid: (-grades[sid][subject], sid))
                outgoing.append(str(best))
        rounds.append({"in": incoming, "out": outgoing})
    return {"name": f"stress {case_no:02}", "rounds": rounds}


def main() -> None:
    rng = random.Random(0x6B00)
    json.dump([make_case(rng, i) for i in range(20)], sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
