---
name: contract-ledger
description: Use CONTRACT.md as the only task ledger. Check one task out, change only its owned paths, run its acceptance check, and check it in with a one-line verified result in the same commit. Use for build, claim, resume, complete or review requests.
---

# Contract ledger (Markdown)

[CONTRACT.md](../../../CONTRACT.md) is the **only** task ledger. [SPEC.md](../../../SPEC.md) defines the product. Read both before beginning work. Follow the task sections in **document order**, not numeric order, because H-09/H-10 precede the H-04 backend gate.

## Before work: find a task

A task starts with a heading `### H-XX — Title`, and has explicit **Status**, **Owner**, **Started at**, **Owns**, **Notes**, **Definition of done**, and **Result** fields. Its status is one of `todo`, `in_progress`, `blocked`, `done`. If the work is not covered, propose a new section and wait for teammate approval. Do not make up a task or edit another task.

## Check out

Change **only** the selected task's fields (keeping each on one line):

```markdown
**Status:** `in_progress`

**Owner:** `developer or agent + teammate`

**Started at:** `2026-10-17 09:00`
```

The timestamp above is **only a formatting example**. Run `date "+%Y-%m-%d %H:%M"` and use the actual returned time. Never check out another person's `in_progress` task without agreement. Each person/agent may hold only one active task.

## Work

Modify files listed under this task's **Owns** only (besides its own section of `CONTRACT.md`). Keep tests and task-specific documentation alongside the code, not as an afterthought. If a new dependency requires an unowned file, stop and request reassignment.

## Check in

1. Run the task's **Definition of done** as written. Quote the real output; if it fails, leave the task in progress or blocked.
2. Change only `**Status:** \`done\`` and `**Result:** \`one-line verified outcome\`` in the selected task section; preserve all other fields.
3. Stage explicit owned paths and ledger together, for example: `git add app/qc.py tests/test_qc.py docs/statistics.md CONTRACT.md`, then commit only after the human approves the diff **or** has already granted scoped standing YES for this one-shot run. In standing-approval mode the orchestrator still logs and inspects the diff and must pass the task's tests/review before committing; pushing and merging are limited to the exact branches permitted in the invoking prompt. Never bypass host prompts, protections or secret-handling rules.
4. To inspect ledger structure and task states run `bash .claude/skills/superagent/scripts/check.sh`. **Do not use a YAML parser.**

## Invariants

The H-04 backend gate must be `done` with real passing tests before H-05 frontend starts. Never claim completion without the executed checks. Keep `CONTRACT.md` as Markdown, not a YAML code block.
