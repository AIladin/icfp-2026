# littleman-runner

A local interpreter and judge for Littleman (`.man`) programs — the machine described in
`docs/vault/spec/language-reference.md`.

```fish
cd py
uv run lm check prog.man                      # structure + every load error
uv run lm run   prog.man --input "42"         # run and print what it emits
uv run lm test  prog.man --problem triangle   # judge against the public cases
```

LM-75 displays are supported: `lm check` names the ports it found, `lm test` judges committed frames
against a problem's expected frames, and `lm run --frames --pixels` draws them. See `CLAUDE.md` for
the semantics decisions and the list of spec ambiguities this runner resolves by assumption.
