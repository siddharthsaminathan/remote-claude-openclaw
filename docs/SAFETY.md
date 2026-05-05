# Safety Rules — remote-claude-openclaw

## Hard Blocks (cannot be bypassed)

### 1. No push without explicit `push` command
The agent will never run `git push` unless you send the exact command `push` from your phone. No other command triggers a push.

### 2. No file deletion without confirmation
Commands containing `rm`, `git rm`, `unlink`, or `del` are blocked. You must reply `confirm-delete` to proceed.

### 3. No destructive commands
The following patterns are blocked at the safety layer:
- `rm -rf`
- `git push --force`
- `git reset --hard`
- `git clean`
- `chmod 777`
- Fork bombs
- Disk formatting

### 4. Sandbox enforcement
All operations are restricted to `LOCAL_REPO_PATH`. Any attempt to operate outside this directory is blocked.

### 5. Unknown sender rejection
Only phone numbers in `ALLOWED_SENDERS` can reach the agent. All others get "Access denied."

### 6. Command logging
Every command from every sender is logged to `logs/commands-YYYYMMDD.log`. This creates an audit trail.

## Soft Guards (warn but allow)

### Diff before commit
The `commit:` command shows the diff summary before committing. Review it.

### Push confirmation
`push` is a dedicated command. Using it is explicit approval. The agent does not push as a side effect of any other command.

### Stop capability
`stop` kills the current Claude Code process if one is running. Useful if the agent gets stuck.

## What the Agent CANNOT Do

- Access files outside `LOCAL_REPO_PATH`
- Push code without you sending `push`
- Delete files without `confirm-delete`
- Accept commands from unknown phone numbers
- Run destructive shell commands
- Access the internet (Claude Code is the only network consumer)
- Modify its own safety configuration

## What the Agent CAN Do

- Read and write files within `LOCAL_REPO_PATH`
- Run tests and linters
- Create commits (with your message)
- Push (only when you explicitly say `push`)
- Report status and diffs
- Plan changes without executing them

## Architecture-level Safety

- Each laptop runs its own agent with its own `.env`
- Siddharth's agent does NOT control Hayagreev's laptop
- Hayagreev's agent does NOT control Siddharth's laptop
- There is no central server that could mix up identities
- Model routing uses Claude aliases — the proxy handles real model names
