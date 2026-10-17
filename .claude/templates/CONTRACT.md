# CONTRACT — New Project Task Ledger Template

**Product:** [SPEC.md](../../SPEC.md) describes the tool. **Tasks:** this Markdown ledger tracks execution and ownership. The root hackathon repo already has a filled-in `CONTRACT.md`; use that instead of this blank template unless creating a separate project.

## Rules

- Build only tasks listed here. Add a new task only after agreement.
- Check out a task by changing **Status**, **Owner**, **Started at**. Keep one active task per person/agent.
- Edit only the task's **Owns** paths. Each task has runnable **Definition of done** checks.
- Check in only after executing the check. Change **Status** to `done` and add a real one-line **Result** in the same commit as the owned work.
- Tests and documentation are produced alongside implementation, not at the end. Run `bash .claude/skills/superagent/scripts/check.sh` to inspect status.

## Tasks

### H-01 — Finalize SPEC and project decisions

**Points:** Design and scope

**Status:** `todo`

**Owner:** `unassigned`

**Started at:** `—`

**Owns:** `SPEC.md`, `docs/plan.md`

**Notes:** Confirm who uses the tool and what decisions the tool supports. Never invent unknown prompts or test data.

**Definition of done:** The team approves SPEC.md and docs/plan.md contains the intended architecture and checks.

**Result:** `—`

### H-02 — Create sample data and codebook

**Points:** Test data and documentation

**Status:** `todo`

**Owner:** `unassigned`

**Started at:** `—`

**Owns:** `data/`

**Notes:** Provide representative synthetic examples, a reproducible generator and a dataset codebook.

**Definition of done:** Data files load correctly and data/README.md documents all columns, units and expected behavior.

**Result:** `—`

### H-03 — Implement and verify the statistical core

**Points:** Statistical correctness

**Status:** `todo`

**Owner:** `unassigned`

**Started at:** `—`

**Owns:** `app/qc.py`, `tests/test_qc.py`, `docs/statistics.md`

**Notes:** Write statistics independently of the UI. Create tests for a worked known answer and a degenerate case, then code.

**Definition of done:** python -m pytest tests/test_qc.py -q passes and docs/statistics.md explains the formula and limitations.

**Result:** `—`
