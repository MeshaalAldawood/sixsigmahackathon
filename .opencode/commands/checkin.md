---
description: "Run a task's definition_of_done and check it in to CONTRACT.md (e.g. /checkin H-03); shows the diff and commits only after your yes"
agent: build
model: google/gemini-3.1-flash-lite
---
Task id: $1
If the task id above is blank, use the task in CONTRACT.md that is in_progress; if there is none, or more than one, ask me which.

Check this task in, following the contract-ledger skill (.claude/skills/contract-ledger/SKILL.md).

1. Run the task's definition_of_done exactly as written in CONTRACT.md. Paste the command and its real output. Never swap in a different command.
2. If it failed, stop: the task is not done. Leave **Status:** `in_progress`, write what is missing in result, and tell me.
3. If it passed, change exactly two lines in this task's block in CONTRACT.md, one small edit each (the two lines are not next to each other, so never try to replace both in one edit): the **Status:** line becomes **Status:** `done`, and the **Result:** line becomes **Result:** `one line saying what exists now and the check that proved it`. Do not rewrite or replace the block: owner, Started at, owns, notes and definition_of_done stay exactly as they are. In every edit, the new text keeps every line of the old text; only the status value and the result value change. If started_at is blank, run date "+%Y-%m-%d %H:%M" and paste what it prints (never a time you made up). Quote any value that contains a colon.
4. Check the ledger: run bash .claude/skills/superagent/scripts/check.sh and git diff CONTRACT.md. If any line other than status and result changed, put it back before going on.
5. Show me git status, the diff, and the exact commit command, staging files by name (the task's owned files plus CONTRACT.md; never git add . or git add -A). Then stop: end your message with the question "Commit these files? (yes/no)" and run nothing else. Commit only after I answer yes in my next message. Never push.
6. After the commit, paste the definition_of_done output again and the commit hash.
