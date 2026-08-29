---
tags:
  - AI
  - spec
  - confirmed
date: 2026-07-24T15:40+03:00
---

Every problem is graded against both public and private cases.

- **Public** — shown in full on the problem page and in the editor's test-cases tab, which also runs
  them and submits your work. Same data as `publicTestData` from the [[Contest API]].
- **Private** — never shown, and per [[grading#Public & private test cases]] they are

  > intended to exercise the same behavior as the public cases - **no hidden tricks**. They exist to
  > make it difficult to hardcode output for each test case.

## Why it matters

- **Passing a private case is the eligibility gate for scoring at all** ([[Ranking and points]]).
  A hardcoded solution scores exactly zero, not partial credit.
- The organisers' "no hidden tricks" promise means the public cases are a **representative sample**:
  a genuine solution to the public cases should carry over. It also means failures on private cases
  point at edge cases in the same behaviour (empty input, extreme values, longer
  [[Rounds|rounds]]) rather than at some undisclosed rule.
- Since private cases are never shown, the only signal is `casesPassed`/`casesTotal` from a
  submission ([[Contest API]]). Local testing against public cases is necessary but never sufficient
  — budget submissions for probing.
