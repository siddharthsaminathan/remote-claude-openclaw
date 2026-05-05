# Safety Rules — remote-claude-openclaw

Enforced by the OpenClaw workspace CLAUDE.md on every agent session.

## Hard Blocks (cannot be bypassed)

### 1. No push without explicit `push` command
The agent will never run `git push` unless you send the exact word `push` from WhatsApp. No other command triggers a push.

### 2. No file deletion without confirmation
Commands containing `rm`, `git rm`, `unlink`, or `del` require `confirm-delete` reply.

### 3. No destructive commands
Blocked: `rm -rf`, `git push --force`, `git reset --hard`, `git clean`, `chmod 777`, fork bombs, disk formatting.

### 4. Sandbox to LOCAL_REPO_PATH
All operations restricted to the repo directory. Operations outside are refused.

### 5. Unknown sender rejection
Only WhatsApp numbers in OpenClaw's `allowFrom` list can reach the agent. Currently: `+917299707403`.

### 6. Command logging
OpenClaw logs all commands via the `command-logger` hook. Additional logging to `logs/commands-*.log`.

## Transport Safety

- OpenClaw WhatsApp plugin operates in `dmPolicy: allowlist` mode
- `selfChatMode: true` — only self-chat, no group access
- `groupPolicy: allowlist` — groups require explicit allowlisting
- Gateway bound to loopback only (127.0.0.1)
- Gateway auth: token mode

## What the Agent CANNOT Do

- Access files outside LOCAL_REPO_PATH
- Push code without explicit `push` command
- Delete files without confirmation
- Accept commands from unknown numbers
- Run destructive shell commands
- Modify its own safety configuration

## What the Agent CAN Do

- Read and write files within LOCAL_REPO_PATH
- Run tests and linters
- Create commits (with your message)
- Push (only on explicit `push` command)
- Report status and diffs
- Plan changes without executing

## Per-Laptop Safety

- Siddharth's agent: only Siddharth's WhatsApp controls it
- Hayagreev's agent: only Hayagreev's WhatsApp controls it
- No cross-laptop access possible
- Each laptop has its own CLI, repo, and allowlist

## CEO Setup Security

The CEO's laptop:
- Has its own `.env` with FOUNDER_ID=hayagreev
- Has its own OpenClaw config with CEO's WhatsApp number
- Has its own workspace CLAUDE.md
- Points to CEO's own copy of the repo
- Cannot access Siddharth's machine
