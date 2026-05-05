# CEO Setup — Hayagreev's Laptop

This guide assumes Siddharth has already set up his laptop. You are setting up **your own laptop** independently.

## Step 1: Clone the repo

```bash
cd ~/Projects
git clone <repo-url> remote-claude-openclaw
cd remote-claude-openclaw
```

## Step 2: Copy and edit .env

```bash
cp .env.example .env
```

Now edit `.env` with your values:

```bash
FOUNDER_ID=hayagreev
FOUNDER_NAME=Hayagreev
FOUNDER_ROLE=CEO
LOCAL_REPO_PATH=/Users/hayagreev/Projects/Shanthibeta2
CLAUDE_CODE_COMMAND=claude
ANTHROPIC_BASE_URL=http://localhost:8082
ANTHROPIC_AUTH_TOKEN=<same-token-as-siddharth-gave-you>
MAIN_MODEL_ALIAS=opus
CHEAP_MODEL_ALIAS=haiku
CHANNEL=whatsapp
ALLOWED_SENDERS=+91XXXXXXXXXX    # YOUR phone number here
```

## Step 3: Install

```bash
chmod +x scripts/*.sh
./scripts/install.sh
```

This checks:
- Node, Python, Git are available
- Claude Code CLI is installed
- Proxy is reachable
- Your repo exists

## Step 4: Doctor check

```bash
./scripts/doctor.sh
```

This verifies everything works. All checks should pass before proceeding.

## Step 5: Start

```bash
./scripts/start.sh
```

You'll see a banner showing:
- Owner: Hayagreev (CEO)
- Repo: /Users/hayagreev/Projects/Shanthibeta2
- SAFETY MODE: ENABLED

## Step 6: Send a test message

From your phone (WhatsApp/Telegram/Slack), send:

```
status
```

You should get back the repo status (branch, last commit, dirty files).

Then try:

```
diff
```

To see uncommitted changes.

## Commands you can send from your phone

| Command | What it does |
|---------|-------------|
| `plan: <task>` | Plan only, no code changes |
| `fix: <task>` | Edit code, run tests, NO push |
| `status` | Repo status + current branch |
| `diff` | Summarize uncommitted changes |
| `commit: <message>` | Commit local changes |
| `push` | Push to remote (explicit approval) |
| `stop` | Stop current run |

## Safety

- Your agent only operates on YOUR laptop's LOCAL_REPO_PATH
- It will NEVER push without you sending `push`
- It will NEVER delete files without confirmation
- Unknown phone numbers are rejected
- Every command is logged to `logs/commands-*.log`

## Troubleshooting

**"Claude Code not found"**
```bash
npm install -g @anthropic-ai/claude-code
```

**"Proxy not reachable"**
Siddharth needs to start the proxy on his machine. You need access to it, or run your own.

**"LOCAL_REPO_PATH not found"**
Clone the Shanthibeta2 repo to your laptop first.
