#!/usr/bin/env bash
# check.sh - one command that tells you where the project stands.
#   bash .claude/skills/superagent/scripts/check.sh           # run from the repo root
#   bash .claude/skills/superagent/scripts/check.sh --team    # also FAIL if no task is done yet
# Prints one line per check: "ok", "todo" (not done yet, fine) or "FAIL" (broken).
# Exit 0 = nothing broken. Exit 1 = at least one FAIL.
set -u
team=0
[ "${1:-}" = "--team" ] && team=1
fail=0

# Find a working python (python3 or python).
py=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1; then py="$c"; break; fi
done

# 1. SPEC.md and its blanks.
fill=0
if [ -s SPEC.md ]; then
  fill=$(grep -c "FILL IN[.,]" SPEC.md || true)
  if [ "$fill" -eq 0 ]; then echo "ok    SPEC.md present, 0 FILL IN lines left"
  else echo "todo  SPEC.md present, $fill FILL IN lines left"; fi
else
  echo "FAIL  SPEC.md missing (run this from the repo root)"; fail=1
fi

# 2. CONTRACT.md validates; one line per task.
ndone=0; ntasks=0; nexttask=""
if [ ! -s CONTRACT.md ]; then
  echo "FAIL  CONTRACT.md missing (run this from the repo root)"; fail=1
elif [ -z "$py" ]; then
  echo "FAIL  no python found to parse CONTRACT.md"; fail=1
else
  out=$("$py" -X utf8 - CONTRACT.md <<'PY'
import re, sys
path = sys.argv[1]
source = open(path, encoding="utf-8").read()
headings = list(re.finditer(r"(?m)^### (H-\d{2}) — (.+)$", source))
if not headings:
    print("BAD no H-XX task headings found"); sys.exit(0)
tasks = []
required = ("Points", "Status", "Owner", "Started at", "Owns", "Definition of done", "Result")
for i, heading in enumerate(headings):
    block = source[heading.end():headings[i+1].start() if i+1 < len(headings) else len(source)]
    fields = {}
    for name in required:
        match = re.search(r"(?m)^\*\*" + re.escape(name) + r":\*\*\s*(.+)$", block)
        if not match:
            print("BAD task %s missing %s" % (heading.group(1), name)); sys.exit(0)
        fields[name] = match.group(1).strip()
    status = fields["Status"].strip("`")
    owner = fields["Owner"].strip("`")
    tasks.append((heading.group(1), status, owner))
ids = [t[0] for t in tasks]
if len(ids) != len(set(ids)):
    print("BAD duplicate task ID"); sys.exit(0)
bad = [t for t in tasks if t[1] not in ("todo", "in_progress", "blocked", "done")]
done = sum(1 for t in tasks if t[1] == "done")
nxt = next((t[0] for t in tasks if t[1] in ("in_progress", "todo")), "")
print("OK Markdown task ledger: %d tasks, %d done" % (len(tasks), done))
for tid, st, owner in tasks:
    print("TASK %-5s status=%-12s owner=%s" % (tid, st, owner or "-"))
if bad:
    print("BAD unknown status on: " + ", ".join(t[0] for t in bad))
print("NUMS %d %d %s" % (len(tasks), done, nxt))
PY
)
  if echo "$out" | grep -q "^BAD"; then
    echo "$out" | grep "^BAD" | sed 's/^BAD /FAIL  CONTRACT.md: /'; fail=1
  else
    echo "$out" | grep "^OK" | sed 's/^OK /ok    CONTRACT.md /'
    echo "$out" | grep "^TASK" | sed 's/^TASK /      task /'
    nums=$(echo "$out" | grep "^NUMS")
    ntasks=$(echo "$nums" | awk '{print $2}'); ndone=$(echo "$nums" | awk '{print $3}'); nexttask=$(echo "$nums" | awk '{print $4}')
  fi
fi

# 3. The plan.
if [ -s docs/plan.md ]; then echo "ok    docs/plan.md present"
else echo "todo  docs/plan.md not written yet (the plan comes after SPEC.md is filled in)"; fi

# 4. The router skill.
if [ -s .claude/skills/superagent/SKILL.md ]; then echo "ok    .claude/skills/superagent/SKILL.md present"
else echo "FAIL  .claude/skills/superagent/SKILL.md missing"; fail=1; fi

# 5. Closed-loop gate for a team that has started.
if [ "$team" -eq 1 ]; then
  if [ "$ndone" -ge 1 ]; then echo "ok    --team: $ndone task(s) checked in as done"
  else echo "FAIL  --team: no task is done yet. Run a task's definition_of_done, then set **Status:** `done` and a one-line **Result**"; fail=1; fi
fi

# 6. One line: what to do next.
if [ "$fail" -ne 0 ]; then
  echo "NEXT  fix the FAIL lines above first"
elif [ "$fill" -gt 0 ]; then
  echo "NEXT  SPEC has $fill FILL IN lines: type /superagent and describe your app"
elif [ ! -s docs/plan.md ]; then
  echo "NEXT  SPEC is filled in: type /superagent and ask for the plan (docs/plan.md)"
elif [ -n "$nexttask" ]; then
  echo "NEXT  build task $nexttask: type /superagent and say \"build $nexttask\""
else
  echo "NEXT  every task is done: deploy, then open the live URL and check it answers"
fi
[ "$fail" -eq 0 ] && echo "PASS  check.sh" || echo "FAIL  check.sh"
exit "$fail"
