# docs

Repository documentation is organized into four main groups:

- [`specs/`](./specs/) — long-term canonical truth
- [`plan/`](./plan/) — active, completed, and archived implementation plans
- [`reference/`](./reference/) — non-normative background material
- root `docs/*.md` — stable handoff and directly operational docs that still need a root entrypoint

## Root docs currently kept at top level
- [`project-handoff.md`](./project-handoff.md) — stable documentation entrypoint
- [`session-handoff-2026-04-19-ui-recovery.md`](./session-handoff-2026-04-19-ui-recovery.md) — current temporary handoff
- [`macos-release.md`](./macos-release.md) — operational release instructions

## Migration note
Some legacy files are still duplicated at older paths while downstream users switch over.
New entrypoints should prefer `specs/`, `plan/`, and `reference/`.
