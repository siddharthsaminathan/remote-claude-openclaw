# remote-claude-openclaw

Phone-controlled Claude Code agent. WhatsApp → OpenClaw → Claude Code → your repo.

Each founder runs their own agent on their own laptop. Zero cross-laptop routing.

## Architecture

```
Your Phone (WhatsApp)
  → OpenClaw Gateway (WhatsApp transport)
    → Agent session reads workspace CLAUDE.md (safety rules)
      → Claude Code CLI operates on your local repo
        → Response back through OpenClaw → WhatsApp
```

OpenClaw handles WhatsApp transport. The workspace CLAUDE.md enforces safety rules. Claude Code does the actual work.

## Quickstart — Siddharth (CTO)

```bash
cd ~/Projects
git clone <repo-url> remote-claude-openclaw
cd remote-claude-openclaw
cp .env.example .env
# Edit .env → FOUNDER_ID=siddharth, FOUNDER_ROLE=CTO
chmod +x scripts/*.sh
./scripts/install.sh    # Installs safety rules to OpenClaw workspace
./scripts/doctor.sh     # 8 health checks
./scripts/start.sh      # Starts OpenClaw gateway
```

## Quickstart — Hayagreev (CEO)

```bash
cd ~/Projects
git clone <repo-url> remote-claude-openclaw
cd remote-claude-openclaw
cp .env.example .env
# Edit .env → FOUNDER_ID=hayagreev, FOUNDER_ROLE=CEO
# Set LOCAL_REPO_PATH to your repo
chmod +x scripts/*.sh
./scripts/install.sh
./scripts/doctor.sh
./scripts/start.sh
```

See [docs/SETUP_CEO.md](docs/SETUP_CEO.md) for CEO-specific setup.

## Prerequisites

Your laptop needs:
- **OpenClaw** — `brew install openclaw` or https://docs.openclaw.ai
- **Claude Code** — `npm install -g @anthropic-ai/claude-code`
- **Local proxy** — running at `http://localhost:8082` (maps Claude aliases to real models)
- **WhatsApp configured** — run `openclaw configure --section channels`

## Transport: OpenClaw WhatsApp

OpenClaw is already installed and configured at `~/.openclaw/openclaw.json`. WhatsApp is enabled with number `+917299707403` allowlisted.

The WhatsApp plugin handles:
- Receiving messages from your phone
- Sending replies back
- Session management (DM scope)

No Twilio. No external WhatsApp provider. OpenClaw handles everything.

## Safety Rules

Enforced by `skills/remote-claude-code/CLAUDE.md` (installed to OpenClaw workspace):

| Rule | Enforcement |
|------|-------------|
| No push without explicit `push` command | Blocked at agent level |
| No file deletion without confirmation | Blocked at agent level |
| No destructive commands | Blocked at agent level |
| Sandbox to LOCAL_REPO_PATH | Agent refuses to operate outside |
| Unknown senders rejected | OpenClaw allowlist |
| All commands logged | OpenClaw audit trail |

Full safety spec: [docs/SAFETY.md](docs/SAFETY.md)

## Commands (send from WhatsApp)

| Command | Example | What happens |
|---------|---------|-------------|
| `plan: <task>` | `plan: refactor auth` | Plan only, no code changes |
| `fix: <task>` | `fix: login returns 500` | Edit, test, no commit, no push |
| `status` | `status` | Branch, last commit, dirty files |
| `diff` | `diff` | Uncommitted changes summary |
| `commit: <msg>` | `commit: fix null crash` | Commit local diff |
| `push` | `push` | Push to remote |
| `stop` | `stop` | Stop current task |

## Per-Laptop Model

- **Siddharth's laptop** — FOUNDER_ID=siddharth — WhatsApp +917299707403
- **Hayagreev's laptop** — FOUNDER_ID=hayagreev — WhatsApp <CEO's number>

Each laptop has its own:
- OpenClaw instance
- `.env` file
- Workspace CLAUDE.md
- LOCAL_REPO_PATH
- Allowlisted phone number

No central server. Siddharth's laptop never handles CEO's tasks. CEO's laptop never handles Siddharth's tasks.

## Files

```
remote-claude-openclaw/
├── .env.example                      # Template — copy to .env per laptop
├── scripts/
│   ├── install.sh                    # Checks deps, installs safety rules
│   ├── doctor.sh                     # 8 health checks
│   ├── start.sh                      # Starts OpenClaw gateway
│   └── stop.sh                       # Stops OpenClaw gateway
├── skills/remote-claude-code/
│   ├── CLAUDE.md                     # Safety rules + command reference (canonical)
│   └── agent.py                      # Reference implementation (standalone/testing)
├── config/
│   ├── founders.example.json
│   └── agent.example.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SETUP_CEO.md
│   └── SAFETY.md
└── tests/
    └── test_harness.py
```

## Testing

```bash
python3 tests/test_harness.py
```

17 tests covering config loading, safety enforcement, command routing, sender verification, and cross-found routing prevention.
