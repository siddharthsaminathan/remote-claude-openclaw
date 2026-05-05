# CEO Handoff — Remote Claude Code Setup

**For:** Hayagreev (CEO)
**Date:** May 2026
**Laptop:** MacBook (macOS, same as Siddharth's)

---

## What This Is

After this setup, you'll be able to send commands from your phone (WhatsApp) to Claude Code running on your laptop. Your phone controls YOUR laptop only. Siddharth's phone controls HIS laptop. No cross-routing.

```
Your Phone (WhatsApp: +91 9841837272)
  → OpenClaw Gateway (WhatsApp transport)
    → Claude Code CLI (DeepSeek v4 pro via local proxy)
      → Your local copy of Shanthibeta2 repo
        → Response back to your phone via WhatsApp
```

---

## Step 0: Prerequisites

Your laptop needs these installed:

```bash
# Check each one:
node --version        # >= 18
python3 --version     # >= 3.10
git --version
brew --version        # macOS package manager
```

### Install Claude Code
```bash
npm install -g @anthropic-ai/claude-code
```

### Install uv (Python package manager)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Graphify
```bash
uv tool install graphifyy
```

---

## Step 1: Clone Repositories

### 1a. Clone the remote-claude-openclaw repo
```bash
mkdir -p ~/Projects
cd ~/Projects
git clone git@github.com:<your-github-org>/remote-claude-openclaw.git
cd remote-claude-openclaw
```

### 1b. Clone the Shanthibeta2 (emote) repo
```bash
cd ~/Projects
git clone git@github.com:<your-github-org>/Shanthibeta2.git
```

### 1c. Clone the proxy server
```bash
cd ~/CascadeProjects
git clone git@github.com:<your-github-org>/free-claude-code.git
```

> Siddharth will share the actual GitHub URLs. If the repos are private, make sure your SSH key is added to GitHub.

---

## Step 2: Configure Your .env

```bash
cd ~/Projects/remote-claude-openclaw
cp .env.example .env
```

Edit `.env` with YOUR values:

```bash
# CEO Laptop Configuration
FOUNDER_ID=hayagreev
FOUNDER_NAME=Hayagreev
FOUNDER_ROLE=CEO
LOCAL_REPO_PATH=/Users/<your-username>/Projects/Shanthibeta2
CLAUDE_CODE_COMMAND=claude
ANTHROPIC_BASE_URL=http://localhost:8082
ANTHROPIC_AUTH_TOKEN=freecc
MAIN_MODEL_ALIAS=opus
CHEAP_MODEL_ALIAS=haiku
CHANNEL=whatsapp
ALLOWED_SENDERS=<your-openclaw-number>,+919841837272
OPENCLAW_PORT=18789
```

Replace `<your-username>` with your macOS username.
Replace `<your-openclaw-number>` with the WhatsApp number you'll use for OpenClaw.

---

## Step 3: Start the Proxy Server

The proxy maps Claude model names (opus, sonnet, haiku) to DeepSeek models (v4 pro, v4 flash).

```bash
cd ~/CascadeProjects/free-claude-code
uv uvicorn server:app --host 0.0.0.0 --port 8082
```

**Keep this terminal open.** The proxy must stay running while the agent is active.

Test it works:
```bash
# In another terminal:
ANTHROPIC_AUTH_TOKEN="freecc" ANTHROPIC_BASE_URL="http://localhost:8082" claude --print "Say hello"
```

You should get a response. This confirms Claude Code is routing through your proxy.

---

## Step 4: Build the Graphify Knowledge Graph

Graphify maps the entire codebase so Claude Code answers faster with fewer tokens.

```bash
cd ~/Projects/Shanthibeta2

# Install Graphify for Claude Code
graphify install
graphify claude install

# Build the knowledge graph
ANTHROPIC_AUTH_TOKEN="freecc" ANTHROPIC_BASE_URL="http://localhost:8082" claude --print "/graphify ."
```

This creates `graphify-out/` in the Shanthibeta2 directory with:
- `GRAPH_REPORT.md` — full codebase audit
- `graph.json` — raw graph data
- `graph.html` — interactive visualization

From now on, Claude Code will read the graph before answering code questions — **8x fewer tokens**.

---

## Step 5: Set Up OpenClaw

### 5a. Install OpenClaw
```bash
brew install openclaw
```

### 5b. Run the setup wizard
```bash
openclaw configure
```

Follow the interactive prompts:
- **Model:** Select OpenRouter with DeepSeek
- **WhatsApp channel:** Enable it
- **Gateway:** Local mode, port 18789

### 5c. Configure WhatsApp allowlist
Edit `~/.openclaw/openclaw.json` and set the WhatsApp section to:

```json
"whatsapp": {
  "enabled": true,
  "dmPolicy": "allowlist",
  "selfChatMode": true,
  "allowFrom": [
    "<YOUR_OPENCLAW_WHATSAPP_NUMBER>",
    "+919841837272"
  ],
  "groupPolicy": "allowlist"
}
```

- `<YOUR_OPENCLAW_WHATSAPP_NUMBER>` — the WhatsApp number OpenClaw logs into on YOUR laptop
- `+919841837272` — YOUR phone (CEO)
- Do NOT add `+917299707403` — that's Siddharth/CTO's phone

### 5d. Install Graphify for OpenClaw
```bash
cd ~/.openclaw/workspace
graphify claw install
```

---

## Step 6: Install Safety Rules

```bash
cd ~/Projects/remote-claude-openclaw
chmod +x scripts/*.sh
./scripts/install.sh
```

This copies the safety rules (CLAUDE.md) to your OpenClaw workspace. The rules enforce:
- No push without explicit approval
- No file deletion without confirmation
- No destructive commands
- Sandbox to your LOCAL_REPO_PATH
- Unknown senders rejected

---

## Step 7: Run Doctor Check

```bash
cd ~/Projects/remote-claude-openclaw
./scripts/doctor.sh
```

All checks should pass before proceeding. Fix any failures (the doctor tells you what's wrong).

---

## Step 8: Link WhatsApp

### 8a. Start the gateway
```bash
openclaw gateway --port 18789 --bind loopback
```

Keep this terminal open.

### 8b. Open the dashboard
In a browser, go to:
```
http://127.0.0.1:18789/
```

You'll see the OpenClaw control UI. It will show a **QR code** for WhatsApp.

### 8c. Scan the QR code
On YOUR phone (`+91 9841837272`):
1. Open WhatsApp
2. Settings → Linked Devices → Link a Device
3. Scan the QR code from the dashboard

> **Important:** This links OpenClaw to YOUR WhatsApp. You'll send commands from your phone to this number. Siddharth has his own OpenClaw linked to a different number on his laptop.

### 8d. Verify connection
```bash
openclaw channels status
```

You should see: `WhatsApp default: linked, connected`

---

## Step 9: Start the Agent

```bash
cd ~/Projects/remote-claude-openclaw
./scripts/start.sh
```

You should see:
```
AGENT IDENTITY
Owner:  Hayagreev (CEO)
Repo:   /Users/<your-username>/Projects/Shanthibeta2
Channel: whatsapp
SAFETY MODE: ENABLED
```

---

## Step 10: Test

From YOUR phone (WhatsApp, number `+91 9841837272`), send a message to your OpenClaw WhatsApp number:

```
status
```

You should get back:
- Branch name
- Last commit
- Dirty/clean status

Then try:

```
diff
```

And:

```
plan: add a hello world test
```

---

## Commands Reference

| Command | What it does |
|---------|-------------|
| `plan: <task>` | Claude Code plans, no edits |
| `fix: <task>` | Claude Code edits + tests, no commit/push |
| `status` | Git status + recent commits |
| `diff` | Uncommitted changes summary |
| `commit: <message>` | Commit local changes |
| `push` | Push to remote (explicit approval) |
| `stop` | Stop current task |

---

## Daily Operation

### Starting everything (after reboot):

**Terminal 1 — Proxy:**
```bash
cd ~/CascadeProjects/free-claude-code
uv uvicorn server:app --host 0.0.0.0 --port 8082
```

**Terminal 2 — OpenClaw:**
```bash
openclaw gateway --port 18789 --bind loopback
```

**Terminal 3 — Verify:**
```bash
cd ~/Projects/remote-claude-openclaw
./scripts/doctor.sh
```

Then send `status` from WhatsApp to test.

### Stopping:
```bash
cd ~/Projects/remote-claude-openclaw
./scripts/stop.sh
```
Plus Ctrl+C in the proxy terminal.

---

## Files Overview

| File | Purpose |
|------|---------|
| `~/.openclaw/openclaw.json` | OpenClaw config (WhatsApp, gateway, models) |
| `~/.openclaw/workspace/CLAUDE.md` | Safety rules + command routing |
| `~/.openclaw/workspace/USER.md` | Your identity and preferences |
| `~/.openclaw/workspace/memory/` | Daily dev blogs, bug registry |
| `~/Projects/remote-claude-openclaw/.env` | Your per-laptop config |
| `~/Projects/Shanthibeta2/graphify-out/` | Knowledge graph files |

---

## Troubleshooting

### "Proxy not reachable"
Make sure Terminal 1 (proxy server) is running. Check: `curl http://localhost:8082/health`

### "WhatsApp not linked"
Re-run: `openclaw channels login --channel whatsapp` and scan the QR from the dashboard.

### "Claude Code not found"
```bash
npm install -g @anthropic-ai/claude-code
```

### "Permission denied" on script
```bash
chmod +x ~/Projects/remote-claude-openclaw/scripts/*.sh
```

### Graphify errors
```bash
uv tool install graphifyy --force
graphify install
```

---

## Safety

- Your agent operates ONLY on YOUR laptop's LOCAL_REPO_PATH
- It NEVER pushes without you sending `push`
- It NEVER deletes files without confirmation
- Unknown phone numbers are rejected
- Every command is logged
- Siddharth's phone CANNOT control your laptop
- Your phone CANNOT control Siddharth's laptop

---

## Questions?

Message Siddharth. Or send `status` to your OpenClaw WhatsApp and ask the agent.
