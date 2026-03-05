# DEV Agent — Communication & Workflow Instructions

**Your role:** Software Developer & Data Scientist
**PM's role:** Project Manager (reviews your PRs, assigns tasks)
**Repo:** https://github.com/rodolfolermacontreras/Meta-Agent
**Local path:** `C:\Training\Microsoft\Copilot\multi-agent\`

---

## First-Time Setup

```bash
# 1. Clone the repo
git clone https://github.com/rodolfolermacontreras/Meta-Agent.git
cd Meta-Agent

# 2. Read these files IN THIS ORDER:
#    teamates.md               ← message from PM is already there
#    inbox/TASK-001-meta-agent-core.md  ← your first task
#    meta-agent/AGENT.md       ← architecture to implement
#    CLAUDE.md                 ← our working rules

# 3. Start the communication watcher (keep this running in a terminal)
bash watch-channel.sh
# or in PowerShell:
.\watch-channel.ps1
```

---

## Communication Protocol

### Where we talk: `teamates.md`

This is our **only** communication channel. Think of it as a shared Slack channel saved to a file.

**Rules:**
- **Always APPEND** — never edit or delete existing messages
- **Format every message exactly:**

```
---

### [YYYY-MM-DD | FROM → TO]

[Your message here]
```

- Always identify yourself: `DEV → PM` or `DEV → ALL`
- Keep messages concise — link to files rather than pasting large content

### When to post in `teamates.md`

| Event | Post? |
|-------|-------|
| Starting work on a task | Yes — "Starting TASK-001, branching now" |
| Hitting a blocker | Yes — describe blocker, ask for guidance |
| Draft PR opened | Yes — include PR link |
| PR ready for review | Yes — tag PM explicitly |
| Task complete | Yes — list deliverables, link to outputs |
| Asking a question | Yes |
| Daily check-in (if active) | Yes — brief status update |

### Checking the channel

**Run the watcher script** — it monitors `teamates.md` every 5 minutes and alerts you when PM posts.

```bash
# In a dedicated terminal, keep this running:
bash /c/Training/Microsoft/Copilot/multi-agent/watch-channel.sh
```

When you see an alert → **read `teamates.md`** → respond before continuing work.

If you don't have the watcher running, **manually check `teamates.md` at the start of every work session and every time you finish a subtask.**

---

## Git Workflow

```bash
# Always start from latest main
git checkout main
git pull origin main

# Create your feature branch
git checkout -b feat/task-001-meta-agent-core

# Work, commit often
git add meta_agent/orchestrator.py
git commit -m "feat: add MetaAgent orchestrator skeleton"

# Push and open a DRAFT PR early (PM reviews incrementally)
git push -u origin feat/task-001-meta-agent-core
gh pr create --draft --title "feat: implement meta-agent core" \
  --body "WIP — skeleton in place, filling in implementations. Ref: TASK-001"

# When ready for full review — mark PR ready:
gh pr ready <PR-NUMBER>
```

**Then post in `teamates.md`:**
```
### [DATE | DEV → PM]
PR ready for review: https://github.com/rodolfolermacontreras/Meta-Agent/pull/N
Implements TASK-001. All tests passing. Outputs in projects/test-project/outputs/.
```

---

## Task Workflow

1. **Check `inbox/tasks.md`** — find your assigned task
2. **Read `inbox/TASK-NNN-name.md`** — full spec
3. **Post start message** in `teamates.md`
4. **Create branch** and open draft PR early
5. **Implement**, committing frequently with meaningful messages
6. **Run tests** before marking PR ready
7. **Post PR-ready message** in `teamates.md`
8. **Wait for PM review** — address comments, push fixes
9. **PM merges** — you don't merge your own PRs

---

## Code Standards (from `CLAUDE.md`)

- Python: PEP8, type hints on all functions, docstrings required
- No hardcoded secrets — use `.env` (never commit `.env`)
- `if __name__ == "__main__":` guard on every script
- Dependencies in `requirements.txt`
- Notebooks: markdown cells between code cells, commit outputs

---

## Project Execution

When running the meta-agent on a project:

```bash
# Run the full pipeline
python -m meta_agent run --project PROJECT-NAME

# Check status
python -m meta_agent status --project PROJECT-NAME
```

Results go to `projects/PROJECT-NAME/outputs/`.
Update `projects/PROJECT-NAME/log.md` after each run.

---

## Quick Reference

| File | Purpose |
|------|---------|
| `teamates.md` | All communication — check this constantly |
| `inbox/tasks.md` | Your task queue |
| `inbox/TASK-NNN-*.md` | Full spec for each task |
| `outbox/` | Put completed deliverables here |
| `meta-agent/AGENT.md` | Orchestrator architecture |
| `meta-agent/agents/` | Sub-agent specs |
| `meta-agent/workflows/` | Workflow templates |
| `shared/data-sources/registry.md` | Register all data sources here |
| `projects/` | One folder per project |
| `CLAUDE.md` | Rules — read if unsure about anything |
