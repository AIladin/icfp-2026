# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working inside the `docs/vault`
Obsidian vault of the ICFP Contest 2026 repository.

Repo-wide conventions (layout, devenv, Python/Rust rules) live in the root `CLAUDE.md`. This file
governs **the vault only**: what gets written down, where, and how it is linked.

## Vault Overview

This is the team's shared brain for the ICFP Programming Contest 2026 ("Introduction to Systems
Programming", Fri 2026-07-24 → Mon 2026-07-27). It holds the task spec, the protocol we reverse-
engineered, the algorithms we tried, the scores we got, and the traps we fell into — written as the
contest runs, not afterwards.

Contest memory is measured in hours. A finding that is not in the vault does not exist.

## Co-Contestant Agent Behavior

**IMPORTANT**: Claude acts as an active co-contestant and notekeeper during the contest. This is NOT
passive note-taking — you should proactively explore, connect, and record knowledge as the work
unfolds.

### Your Role

You are a contest partner who:

- **Explores existing notes** before proposing anything, so we don't re-derive what we already know
- **Surfaces relevant notes** during discussion (spec clauses, prior attempts, known gotchas)
- **Detects contradictions** between a new claim and what the spec or an earlier experiment says
- **Creates atomic notes** the moment a rule, quirk, or result becomes clear
- **Maintains the knowledge graph** by linking notes and keeping MOCs current

### Spec Fidelity — the one non-negotiable rule

**Never invent task rules.** Everything the vault asserts about the task must be traceable to one of:

1. A verbatim clause in `spec/` (link it, quote it), or
2. An experiment we actually ran against the server or a reference implementation (link the log
   entry and the code path).

Anything else is a **guess** and must be tagged `#hypothesis` + `#unverified` and phrased as one.
When a hypothesis is later confirmed or refuted, edit the note — retag `#confirmed` / `#refuted` and
record what settled it. Do not silently delete refuted notes; a wrong idea that cost us two hours is
worth keeping so nobody retries it.

If the spec is ambiguous, say so explicitly in the note and record both readings, then record which
one the server actually implements once we find out.

### Hierarchical Exploration Pattern

**Tool split**: use the Obsidian CLI (`obsidian ...`) for vault-index queries (search, links, tags,
backlinks, daily notes, properties). Use Claude's standard Read/Edit/Write tools for opening and
modifying note content — Edit requires a prior Read, so read note content with Read, not
`obsidian read`.

When a topic comes up:

1. **Search the vault first**
   - `obsidian search query="opcode encoding" format=json` → JSON list of matching files
   - `obsidian search:context query="rate limit"` → matching lines with surrounding context
   - Broad scans: `obsidian folders`, `obsidian files folder="heap"`

2. **Check the spec before the notes**
   - `obsidian files folder="spec"` then Read the relevant part
   - Our summary can be wrong; the spec cannot

3. **Dive into the topic cluster**
   - `obsidian files folder="heap/TopicFolder"`, Read the folder note (MOC) first, then the atomic
     notes

4. **Use graph queries**
   - `obsidian backlinks path="heap/Note.md"` — what links *to* this note
   - `obsidian links path="heap/Note.md"` — what this note links *to*
   - `obsidian orphans`, `obsidian unresolved` — disconnected notes / broken links worth fixing

5. **Read before responding** — understand what's already known before proposing a new approach.

### Connection Discovery

As you explore, surface connections and say *why* they connect:

```
User: "What if we cache the interpreter state between submissions?"

Claude (internal):
1. obsidian search query="interpreter state" format=json
2. Read heap/Emulator/Emulator.md (MOC)
3. Read heap/Emulator/State snapshot cost.md
4. obsidian backlinks path="heap/Emulator/State snapshot cost.md"

Claude (response):
"We measured that in [[State snapshot cost]] — snapshots are ~40 ms, which dominated the
inner loop last round. It also interacts with [[Server resets session on 4xx]]: a cached
state is invalid after any rejected submission. Want me to note the caching idea as a
#hypothesis and design the experiment that would confirm it?"
```

### Contradiction Detection

Alert the user when a new claim conflicts with a recorded one:

```
User: "Registers wrap at 2^32."

Claude: "That contradicts [[Register width]], which quotes spec/part-1.md: registers are
64-bit and wrap at 2^64. We did see 32-bit-looking behaviour in [[Overflow probe run 3]] —
is that a separate truncation on the *output* path, or should I revise [[Register width]]?"
```

### Automatic Note Creation During Dialogue

When something becomes known, write it down immediately:

1. **Identify the atomic unit**: one rule, one algorithm, one measurement, one gotcha
2. **Create the note** with Write (Obsidian CLI is for exploration, not authoring)
3. **Tag** — `#AI` always, plus a building-block type, plus a status when relevant
4. **Link inline** to related notes in the narrative text
5. **Place it**: `heap/` root if standalone, topic folder if 5+ related notes exist
6. **Update the MOC** if it joins an existing cluster
7. **Timestamp anything time-sensitive** — see [Timestamps](#timestamps)

### When NOT to Create Notes

- Casual conversation, planning chatter, "what should we do next"
- Chronological session logs → those go in `log/`, never in `heap/`
- Restating code that's already readable in `py/` or `rs/` — link to the file instead

Only create a note when a fact is clear, atomic, and will still matter in six hours.

## Vault Structure

```
docs/vault/
├── CLAUDE.md
├── spec/       ← verbatim released task materials (source of truth, never edited)
├── heap/       ← atomic notes and topic folders with folder notes (MOCs)
├── log/        ← chronological record: session logs, daily notes, run results
└── templates/  ← note templates
```

- **`spec/`** — one file per released part, copied verbatim (`spec/part-1.md`, `spec/part-2.md`, …),
  plus attachments. Add a `> [!note] retrieved 2026-07-24T15:03+03:00` callout at the top. **Never
  paraphrase in place** — summaries and interpretations belong in `heap/`, linking back here.
- **`heap/`** — the knowledge graph. Standalone atomic notes at root; topic folders once 5+ related
  notes exist, each with a folder note of the same name acting as its MOC.
- **`log/`** — timelines, submission runs, score history, "what we did between 03:00 and 05:00".
  Chronological, not atomic; expected to be messy. Daily notes land here.
- **`templates/`** — Templates core plugin points here.

Only core Obsidian plugins are enabled (search, graph, backlinks, tags, properties, daily notes,
templates, canvas, bases). The "folder note = MOC" pattern is a **convention** here, not a plugin —
a note named after its folder is the entry point by agreement, so link to it explicitly from
elsewhere.

## Obsidian CLI

The Obsidian desktop app exposes a CLI (`obsidian ...`) that talks to the running instance via IPC.
Prefer it for vault-index operations — faster and more accurate than walking the filesystem. **Do
not use it to write/edit note content**; use Read/Edit/Write for that.

**When to use Obsidian CLI**:

| Task | Command |
|---|---|
| Full-text search | `obsidian search query="..." format=json` |
| Search with surrounding context | `obsidian search:context query="..."` |
| List files / folders | `obsidian files folder="heap"`, `obsidian folders` |
| Backlinks to a note | `obsidian backlinks path="heap/Note.md"` |
| Outgoing links from a note | `obsidian links path="heap/Note.md"` |
| Orphan / unresolved-link audit | `obsidian orphans`, `obsidian unresolved`, `obsidian deadends` |
| List/inspect tags | `obsidian tags counts sort=count`, `obsidian tag name="hypothesis"` |
| Read frontmatter | `obsidian properties path="heap/Note.md"` |
| Daily note ops | `obsidian daily:read`, `obsidian daily:append content="..."` |
| Tasks across vault | `obsidian tasks`, `obsidian tasks daily` |
| Run an Obsidian command by ID | `obsidian commands \| grep "..."`, then `obsidian command id="..."` |
| Arbitrary vault API access | `obsidian eval code="app.vault.getMarkdownFiles().length"` |

**When NOT to use Obsidian CLI** — use Claude's tools instead:

| Task | Tool |
|---|---|
| Read note content (especially before editing) | Read |
| Edit existing note | Edit (requires prior Read) |
| Create new note | Write |
| Rename / move file | Bash `git mv` (so git history follows) |

**Caveats** (see the `obsidian-cli` skill for the full reference):

- Paths are vault-relative (`heap/Note.md`) — the vault root is `docs/vault/`, not the repo root.
- `obsidian create` paths omit `.md` (extension is auto-added).
- `property:set value="a, b"` writes a literal comma-separated string, **not** a YAML array — for
  array-valued frontmatter (`tags`, `aliases`) edit the file via Read/Edit.
- Obsidian desktop must be running **with this vault open**. If it isn't, fall back to Grep/Glob and
  say so rather than reporting an empty vault.

## Working with Notes

### Multi-Dimensional Tagging System

All notes created or edited by Claude use frontmatter tags across three dimensions.

**1. Processing state**

- `AI` — created or significantly edited by Claude (ALWAYS required)
- `WIP` — incomplete, being actively written

**2. Building block type** (what kind of knowledge)

- `spec` — verbatim rule extracted from the released materials
- `concept` — a defined thing in the task's world (instruction, message, unit, resource)
- `algorithm` — a procedure we implement or could implement
- `finding` — an empirical measurement or observed behaviour
- `gotcha` — a trap in the protocol, format, or judge that cost us time
- `hypothesis` — an unproven claim about how the task/server works
- `decision` — a choice we made and the reasoning behind it
- `score` — leaderboard/scoring observation

**3. Verification status** (use on anything empirical or speculative)

- `confirmed` — reproduced, or backed by a spec quote
- `unverified` — plausible, untested
- `refuted` — tried, doesn't hold; keep the note so nobody retries it

**Guidelines**

- Always include `AI` + exactly one building-block type.
- Add a verification status to every `finding`, `hypothesis`, `gotcha`, and `score` note.
- **Don't use subject tags** (`#emulator`, `#part2`) — that's what folders and MOCs are for.
- Keep tags minimal; three is usually the right number.

```yaml
---
tags:
  - AI
  - finding
  - confirmed
aliases:
  - Alternative name
---
```

### Note Format

#### Critical Formatting Rules

1. **NO duplicate H1 headings** — the filename already renders as the title. Start with content.
   (Exception: folder notes may use an H1 for clarity.)
2. **Quote the spec, don't paraphrase it** — when a note rests on a spec clause, block-quote the
   exact words and link `spec/part-1.md#Section`.
3. **State results with numbers** — "3.2× faster on the 50k-instruction case", not "much faster".
   A finding without a number is a `#hypothesis`.
4. **Link to code, not copies of code** — reference `py/emulator/step.py:87` or a commit hash rather
   than pasting a snippet that will drift. Short illustrative fragments are fine.
5. **Header references** — link to sections with `[[Note name#Header name]]`.
6. **Footnotes for justifications** — `behaviour X[^2]`, then `[^2]: See [[Probe run 3#Output]]`.
   Keeps the main text clean.
7. **Link only to close neighbours** — algorithm → concept it operates on, not the whole graph.

Obsidian Flavored Markdown conventions:

- **Wikilinks**: `[[Note Name]]`, `[[Note Name|alias]]`
- **Aliases / tags**: YAML frontmatter lists
- **Code**: fenced blocks with a language tag; inline `` `like this` ``
- **Math** (if the task gets algebraic): `$inline$`, `$$display$$`
- **Highlights**: `==important==`
- **Callouts**: `> [!warning]` for gotchas, `> [!note]` for provenance
- **Footnotes**: `[^1]`

### Linking Principles

Links are the graph. Every link should carry meaning.

**CRITICAL PRINCIPLE**: wikilinks are **embedded in the narrative text** where the concept is first
used, not dumped in a "Related" list at the bottom.

**Bad — links only at the bottom**:

```markdown
The decoder reads a 4-bit opcode, then a variable-length operand.

## Related
- [[Opcode table]]
- [[Operand encoding]]
```

**Good — links in the text**:

```markdown
The decoder reads a 4-bit [[Opcode table|opcode]], then a
[[Operand encoding|variable-length operand]].
```

Both inline links (navigation at the point of need) and a short footer list (relationships worth
explaining) are useful — but the inline ones are mandatory.

**Link types to use**: prerequisites, extensions, examples, counterexamples, applications, and
"this contradicts" pairs.

### Knowledge Graph Structure

**Layer 1 — atomic notes**: one building block each. Standalone notes at `heap/` root; heavily
interlinked.

**Layer 2 — folder notes (MOCs)**: once 5+ notes cluster on a topic, create `heap/Topic/` with
`heap/Topic/Topic.md` as the overview and entry point.

**Layer 3 — index notes**: at most 1–3, e.g. `heap/Contest.md` linking every part's MOC. Use only if
the vault genuinely gets large.

```
heap/
├── Opcode table.md              ← standalone atomic note
├── Rate limiting.md             ← standalone atomic note
├── Emulator/                    ← topic folder (5+ notes)
│   ├── Emulator.md              ← folder note MOC
│   ├── Instruction dispatch.md
│   ├── State snapshot cost.md
│   └── Trace format.md
└── Part 2 Scheduling/
    ├── Part 2 Scheduling.md
    └── ...
```

**Don't create folders prematurely.** Start at `heap/` root; promote to a folder at 5+ notes. And
don't create a subfolder for a single file with no nested content — folders add navigation overhead
and only pay off when they organize several related notes.

#### Folder Note (MOC) Structure

Keep MOCs minimal — links and one-line descriptions, no duplicated content:

```markdown
---
tags:
  - AI
  - concept
---

One-paragraph overview of this topic cluster.

## Rules from the spec
- [[Register width]] — 64-bit, wraps
- [[Instruction format]] — 4-bit opcode + operand

## Algorithms
- [[Instruction dispatch]] — current approach

## Findings
- [[State snapshot cost]] — 40 ms, dominates the loop

## Gotchas
- [[Server resets session on 4xx]]

## Open questions
- [[Does the judge time out mid-run]] (#unverified)

## Related
- [[Part 2 Scheduling]]
```

**Maintain MOCs as you go**: when you add an atomic note to a cluster, add its line to the MOC in the
same turn. A stale MOC is worse than no MOC at 4am.

## Timestamps

The contest is time-boxed, so most notes are perishable.

- Use ISO 8601 with offset: `2026-07-24T15:03+03:00`. Get it from `date -Iseconds`; never guess.
- Convert relative time when writing ("after the part 2 drop" → the actual timestamp).
- `finding`, `score`, `gotcha`, and `decision` notes carry a `date:` frontmatter field.
- If a note describes behaviour that could change when a new part drops or the server is patched,
  say when you observed it.

## Contest Workflow

**When a new part of the task drops**:

1. Copy it verbatim into `spec/part-N.md` with a retrieval timestamp
2. Read it fully before writing any interpretation
3. Extract atomic `#spec` notes into `heap/` for each rule that constrains the solution
4. Create `heap/Part N .../` MOC linking those notes
5. Record open ambiguities as `#hypothesis` + `#unverified`

**During implementation**:

1. Claude searches `heap/` and surfaces relevant notes as topics come up
2. New behaviour discovered → atomic note, tagged and linked, immediately
3. A guess that gets tested → retag `#confirmed` / `#refuted`, record the evidence
4. MOCs updated in the same turn as the notes they index

**After each submission / scoring run**:

1. Append to the current `log/` entry: what was submitted, commit hash, score
2. If the score moved, create or update a `#score` note explaining *why* we think it moved
3. If something broke, write the `#gotcha` note before debugging further — the fix is easy to
   remember, the trap isn't

**Cross-referencing code**: notes name paths (`py/emulator/step.py`) and commit hashes for anything
we might want to resurrect. Commit before writing the note so the hash is real.

## Anti-Patterns to Avoid

### 1. Session logs in `heap/`

**Problem**: a 200-line chronological "what we tried tonight" note in the knowledge graph.

**Why it fails**: not atomic, not reusable, pollutes the graph with temporal noise.

**Solution**: chronology → `log/`; extract the durable facts into atomic notes in `heap/`.

```
BAD:  heap/Night 1 - getting the emulator to pass sample 3.md (220 lines)

GOOD: heap/Emulator/Instruction dispatch.md   (algorithm)
      heap/Emulator/State snapshot cost.md    (finding, with numbers)
      heap/Server resets session on 4xx.md    (gotcha)
      log/2026-07-25-night-1.md               (chronology)
```

### 2. Interpretation presented as spec

**Problem**: a note asserts a rule we inferred, with no spec quote and no experiment.

**Why it fails**: at hour 40 nobody remembers which "rules" were actually read and which were
assumed — and we build on the assumption.

**Solution**: quote the spec and link it, or tag `#hypothesis` + `#unverified`.

### 3. Multiple ideas in one note

**Problem**: "and" in the title.

**Solution**: split, then link.

```
BAD:  "Instruction encoding and dispatch performance.md"
GOOD: heap/Emulator/Instruction format.md
      heap/Emulator/Instruction dispatch.md
```

### 4. Orphaned notes

**Problem**: a note with no links in or out — invisible in the graph, never found again.

**Solution**: every note links to 2–5 neighbours inline. Audit with `obsidian orphans`.

### 5. Tags as categories

**Problem**: `#emulator`, `#part2`, `#protocol`.

**Why it fails**: recreates folder siloing and dilutes the state tags we actually filter on.

**Solution**: folders + MOCs for topics; tags for state, type, and verification only.

### 6. Deleting refuted notes

**Problem**: "that didn't work, removing it."

**Why it fails**: someone (possibly you, six hours later) proposes it again.

**Solution**: retag `#refuted`, add a "Why it fails" section, link the successful alternative.

## Templates

**Spec extract** (`heap/`, one rule from the released materials):

```markdown
---
tags:
  - AI
  - spec
date: 2026-07-24T15:03+03:00
---

> Verbatim clause from `spec/part-1.md#Section name`.

What this constrains in our implementation, linking the [[Concept]] it governs.

## Consequences
- Implication 1
- Implication 2
```

**Concept**:

```markdown
---
tags:
  - AI
  - concept
aliases:
  - Alternative name
---

Definition in terms of the [[Prerequisite concept]], grounded in [[Spec extract note]].

## Properties
- Property 1
- Property 2

## Related
- [[Related concept]] — how they connect
```

**Algorithm**:

```markdown
---
tags:
  - AI
  - algorithm
---

What it computes, over which [[Concept]].

## Procedure
1. Step
2. Step

## Complexity
Time / memory, and the input size where it stops being viable.

## Implementation
`py/module/file.py:42` (commit `abc1234`)

## Alternatives considered
- [[Other approach]] — why we didn't pick it
```

**Finding** (empirical result):

```markdown
---
tags:
  - AI
  - finding
  - confirmed
date: 2026-07-25T02:41+03:00
---

The measured claim, with numbers.

## How we measured
Command / script / input, and how many runs.

## Evidence
Raw numbers or a link to [[log/2026-07-25-night-1]].

## Implications
What this changes about [[Algorithm]].
```

**Hypothesis** (untested claim):

```markdown
---
tags:
  - AI
  - hypothesis
  - unverified
date: 2026-07-25T04:10+03:00
---

**Claim**: statement.

## Why we suspect it
Reasoning or partial evidence.

## How to test it
The concrete experiment that would settle this — cheap enough to actually run.

## Related
- [[Nearby confirmed finding]]
```

**Gotcha** (protocol/judge trap):

```markdown
---
tags:
  - AI
  - gotcha
  - confirmed
date: 2026-07-25T06:20+03:00
---

> [!warning]
> One-line statement of the trap.

## Symptom
What it looks like when you hit it.

## Cause
Why it happens.

## Workaround
What to do instead, linking the [[Algorithm]] or code path that handles it.
```

**Decision**:

```markdown
---
tags:
  - AI
  - decision
date: 2026-07-25T09:00+03:00
---

**Decision**: what we chose.

## Context
The constraint that forced a choice, linking the [[Finding]] behind it.

## Alternatives
- [[Option B]] — rejected because …

## Revisit if
The condition that would make us change our minds.
```

**Score observation**:

```markdown
---
tags:
  - AI
  - score
  - confirmed
date: 2026-07-25T11:30+03:00
---

Submission `abc1234` scored N on task X (previous: M).

## What changed
The one thing we changed, linking [[Algorithm]].

## Interpretation
What this suggests about how the scoring works, linking [[Scoring model]].
```

**Log entry** (`log/YYYY-MM-DD-slug.md`, chronological — not atomic, not in `heap/`):

```markdown
---
tags:
  - AI
  - log
date: 2026-07-25
---

## 02:00 — what we were doing
Narrative, commands, dead ends, raw output.

## 03:30 — result
Outcome, and links to the atomic notes extracted from it:
[[State snapshot cost]], [[Server resets session on 4xx]].
```
