---
name: skill-maintenance
description: >
  Keeps this monorepo's skills, the `flutter-conventions` rules, and the
  troubleshooting reference (`.claude/troubleshooting/`) accurate as they're
  used. Retro mode runs at the end of every skill run (per `CLAUDE.md`) and
  fixes whatever the run showed was missing, wrong, or stale. Sweep mode
  reads recent session transcripts for skill failures, workarounds, and user
  corrections, and folds them in. Lint mode runs static checks (frontmatter,
  length, dead paths and links, cross-skill references). Use Sweep when the
  user says "sweep the transcripts", "update the skills from recent
  sessions", "skill maintenance"; Lint for "lint the skills", "check the
  skills"; Retro for "what should we update in the skill?" or at the end of
  any skill run.
---

# Skill maintenance

Skills improve by being used. Every run that hits a wrong path, a missing
step, a workaround, or a user correction should leave the skill better for
the next run. This skill is how.

## What it maintains

| Kind of knowledge | Where it goes |
|---|---|
| How a skill does its job (steps, decisions, defaults, scope) | That skill's `SKILL.md` (or a sibling file it links) |
| A sub-project-only rule for a shared skill | That submodule's `.claude/skills/<skill>/SKILL.md` add-on file |
| A Dart/Flutter code rule | `flutter-conventions` (`SKILL.md`, `tests.md`, `firestore-protos.md`) |
| Error → cause → fix, tool or API quirks | `.claude/troubleshooting/<area>.md` (see its README) |
| User preferences and project state | Memory, not the repo |
| Collaboration preferences for every task | `.claude/CLAUDE.md` |

Never put the same fact in two places; link instead. A skill keeps the
decision tables it acts on (e.g. `build-and-upload-release`'s retry
categories); the troubleshooting reference holds the incidents and
environment quirks behind them.

**In scope:** every skill under `.claude/skills/` that's a real folder
(including `app-store-screenshots`, which the user has customized), the
submodule add-on skills, and `anglers-log/.claude/skills/anglers-log-polls`.
**Out of scope:** the symlinked third-party Firebase skills
(`.claude/skills/firebase-*` → `.agents/skills/`), and anything under a
skill's `template/` that's scaffolded into user projects (edit those only
when the template itself is the subject).

## Policy (the user's standing decisions)

- **Apply changes automatically**, then list them in the run's final
  report. Don't ask first. The exceptions:
  - A change that widens what a skill is pre-authorized to do (posting,
    pushing, merging, spending, deleting, submitting) or narrows a safety
    check: propose it and wait for a yes.
  - A change that reverses something the user explicitly asked for in a
    past session: ask.
- **Commit as you go** in the repo that holds the file, one commit per
  coherent change, with the session's attribution line. Stage only the
  files you changed, by path (never `git add -A` / `.`), and never stage
  submodule pointer changes in the root repo. Don't push unless the user
  asks. In a submodule, commit only if it's on its default branch;
  otherwise leave the edit uncommitted and say so.
- **If a file already has uncommitted changes you didn't make**, don't
  commit over them: leave your edit uncommitted and tell the user, so they
  decide how to split it.
- **Never commit secrets.** Skill folders hold gitignored keys and state
  (`*.p8`, `config.json`, `state.json`). Don't remove ignore rules, and
  check `git status` before committing.

## Retro mode (end of every skill run)

Before the final report of any skill run, ask:

1. **Did a step fail, or need a workaround or a retry?** → fix the step,
   and add a troubleshooting entry for the error and its fix.
2. **Did the user correct me, or add a preference?** → encode it in the
   skill (or memory, if it's a personal preference rather than procedure).
3. **Was anything stale?** A path, command, flag, ID, version, file
   layout, or example that no longer matches reality → fix it.
4. **Did I have to rediscover something** the skill should have told me
   (a per-app hurdle, a tool quirk)? → add it where it belongs (table
   above).
5. **Did the skill's instructions conflict** with each other, another
   skill, or `CLAUDE.md`? → resolve it in the more specific place, and
   link from the other.

If none apply, do nothing and say nothing. Otherwise make the edits, run
Lint on the touched skills (`python3 .claude/skills/skill-maintenance/scripts/lint_skills.py <skill> …`),
commit, and add one line to the final report:
`🔧 Skill updates: <skill>: <what changed>; troubleshooting/<file>: <entry>`.

**Good edits:**
- State the rule and, in a clause, why ("…, because X happened"). Dates and
  build numbers go in the troubleshooting entry, not in the skill's steps.
- Edit the existing section the knowledge belongs in; don't append a
  "Lessons learned" list to the end.
- Remove or rewrite what turned out to be wrong; don't leave both versions.
- Keep skills under ~500 lines. When a skill grows past that, move a mode,
  a big table, or a template into a sibling file and link it.
- Refer to other skills by section name, not step number, so renumbering
  doesn't break the reference.

## Sweep mode (recent transcripts)

Catches what Retro missed, and sessions that weren't skill runs at all.

1. Get the digest. With no window given, use the checkpoint:
   ```bash
   python3 .claude/skills/skill-maintenance/scripts/sweep_transcripts.py \
     --checkpoint --out <scratchpad>/sweep.md
   ```
   `--since YYYY-MM-DD` overrides it. The digest lists, per session, the
   skills run, failed tool calls with their commands, and the user's
   messages. It skips sessions with neither a skill nor an error.
2. Read it in chunks. For each session, look for:
   - a failure followed by a different command that worked (a fix worth
     recording);
   - the user correcting, redirecting, or adding a preference during a
     skill run;
   - a skill step that was skipped, reordered, or done differently than
     written.
   Skip noise: exploratory `grep`/`ls` misses, expected test failures
   mid-TDD, permission denials, and one-off typos. When a digest line isn't
   enough to tell what fixed something, read that part of the transcript
   (`~/.claude/projects/<project>/<session id>.jsonl`).
3. Check each candidate against the current files. It may already be
   fixed, or the code may have moved on since.
4. Apply and commit per the Policy, grouped by skill or troubleshooting
   file.
5. Update the checkpoint: write
   `{"lastSweep": "<YYYY-MM-DDTHH:MM>"}` (the time the sweep started) to
   `.claude/skills/skill-maintenance/state.json`. It's gitignored.
6. Report: sessions read, changes made per file, and candidates rejected
   (one line each, with why).

## Lint mode

```bash
python3 .claude/skills/skill-maintenance/scripts/lint_skills.py [skill …]
```

Checks frontmatter (name matches the folder, description ≤ 1024 chars),
`SKILL.md` length (> 500 lines warns), that backticked repo paths and
Markdown links exist, cross-skill `Step N` references (they must resolve,
and warn because numbers are brittle), and fixed `/tmp/` paths. Fix every
ERROR. Fix WARNs when touching that skill anyway, or when the user asks.
When a check produces a false positive, improve the script rather than
ignoring it.
