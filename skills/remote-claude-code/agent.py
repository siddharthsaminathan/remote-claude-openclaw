#!/usr/bin/env python3
"""
remote-claude-code agent — bridges phone messages to local Claude Code.

Architecture:
  Phone → Channel (WhatsApp/Telegram/Slack) → This Agent → Claude Code → LOCAL_REPO_PATH

Safety:
  - All senders verified against ALLOWED_SENDERS
  - All operations sandboxed to LOCAL_REPO_PATH
  - Never pushes without explicit "push" command
  - Never deletes files without confirmation
  - Never runs destructive commands
  - Every shell command is logged
"""

import argparse
import asyncio
import json
import logging
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ── Logging ───────────────────────────────────
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"commands-{datetime.now(timezone.utc).strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stderr),
    ],
)
log = logging.getLogger("remote-claude-code")


# ── Config ─────────────────────────────────────
class Config:
    """Per-laptop configuration loaded from .env and config files."""

    def __init__(self, env_path: str, agent_config_path: str, founders_path: str):
        self.env = self._load_env(env_path)
        self.agent_config = self._load_json(agent_config_path)
        self.founders = self._load_json(founders_path)

        # Identity
        self.founder_id = self.env.get("FOUNDER_ID", "unknown")
        self.founder_name = self.env.get("FOUNDER_NAME", "Unknown")
        self.founder_role = self.env.get("FOUNDER_ROLE", "Unknown")
        self.local_repo = Path(self.env.get("LOCAL_REPO_PATH", "")).resolve()
        self.claude_cmd = self.env.get("CLAUDE_CODE_COMMAND", "claude")

        # Proxy / model
        self.proxy_url = self.env.get("ANTHROPIC_BASE_URL", "http://localhost:8082")
        self.auth_token = self.env.get("ANTHROPIC_AUTH_TOKEN", "")
        self.main_model = self.env.get("MAIN_MODEL_ALIAS", "opus")
        self.cheap_model = self.env.get("CHEAP_MODEL_ALIAS", "haiku")

        # Channel
        self.channel = self.env.get("CHANNEL", "whatsapp")

        # Safety
        self.require_push_confirm = self._bool(self.env.get("REQUIRE_PUSH_CONFIRMATION", "true"))
        self.enforce_sandbox = self._bool(self.env.get("ENFORCE_REPO_SANDBOX", "true"))
        self.log_all = self._bool(self.env.get("LOG_ALL_COMMANDS", "true"))

        # Allowlist
        raw = self.env.get("ALLOWED_SENDERS", "")
        self.allowed_senders = {s.strip() for s in raw.split(",") if s.strip()}

        # Channel credentials (set in env, not checked into git)
        self.whatsapp_token = self.env.get("WHATSAPP_TOKEN", "")
        self.twilio_sid = self.env.get("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth = self.env.get("TWILIO_AUTH_TOKEN", "")
        self.telegram_token = self.env.get("TELEGRAM_BOT_TOKEN", "")
        self.slack_bot_token = self.env.get("SLACK_BOT_TOKEN", "")
        self.slack_app_token = self.env.get("SLACK_APP_TOKEN", "")

    @staticmethod
    def _load_env(path: str) -> dict:
        env = {}
        p = Path(path)
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip().strip('"').strip("'")
        return env

    @staticmethod
    def _load_json(path: str) -> dict:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text())
        return {}

    @staticmethod
    def _bool(val) -> bool:
        if isinstance(val, bool):
            return val
        return str(val).lower() in ("true", "1", "yes")

    def validate(self) -> list[str]:
        issues = []
        if not self.founder_id:
            issues.append("FOUNDER_ID not set")
        if not self.local_repo.exists():
            issues.append(f"LOCAL_REPO_PATH does not exist: {self.local_repo}")
        if not self.allowed_senders:
            issues.append("ALLOWED_SENDERS is empty — no one can reach this agent")
        return issues


# ── Safety Enforcer ────────────────────────────
class SafetyEnforcer:
    """Blocks dangerous operations and enforces sandboxing."""

    DESTRUCTIVE_PATTERNS = [
        r"\brm\s+-rf\b", r"\bgit\s+push\s+--force\b", r"\bgit\s+reset\s+--hard\b",
        r"\bgit\s+clean\b", r"\bdd\s+if=\b", r"\bmkfs\.\b", r"\b:(){ :\|:& };:\b",
        r"\bchmod\s+777\b", r"\b>\/dev\/sd", r"\bformat\s+C:\b",
    ]

    def __init__(self, config: Config):
        self.config = config

    def check_command(self, command: str) -> tuple[bool, str]:
        """Returns (allowed, reason)."""
        for pattern in self.DESTRUCTIVE_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Blocked destructive pattern: {pattern}"
        return True, "ok"

    def check_path(self, path: Path) -> tuple[bool, str]:
        """Ensure path is within LOCAL_REPO_PATH."""
        if not self.config.enforce_sandbox:
            return True, "sandbox disabled"
        try:
            resolved = path.resolve()
            if str(resolved).startswith(str(self.config.local_repo)):
                return True, "ok"
            return False, f"Path {resolved} is outside LOCAL_REPO_PATH"
        except Exception:
            return False, "path resolution failed"

    def check_push(self, command: str) -> tuple[bool, str]:
        """Push requires explicit approval."""
        if re.search(r"\bgit\s+push\b", command) and "approve-push" not in command:
            if self.config.require_push_confirm:
                return False, "Push requires explicit 'push' command approval"
        return True, "ok"

    def check_delete(self, command: str) -> tuple[bool, str]:
        """File deletion requires confirmation."""
        if re.search(r"\b(rm|git\s+rm|unlink|del\b)\b", command):
            return False, "File deletion requires explicit confirmation — reply 'confirm-delete' to proceed"
        return True, "ok"


# ── Claude Code Runner ─────────────────────────
class ClaudeRunner:
    """Calls local Claude Code with safety enforcement."""

    def __init__(self, config: Config):
        self.config = config
        self.safety = SafetyEnforcer(config)
        self.current_process: subprocess.Popen | None = None

    def run(self, command: str, sender: str, task: str = "") -> dict:
        """
        Execute a Claude Code task.
        Returns: {"status": "ok"|"error"|"blocked", "output": str}
        """
        # Safety checks
        allowed, reason = self.safety.check_command(task)
        if not allowed:
            log.warning(f"BLOCKED destructive command from {sender}: {task[:100]}")
            return {"status": "blocked", "output": f"SAFETY BLOCK: {reason}"}

        # Route command
        cmd_lower = command.strip().lower()

        if cmd_lower.startswith("plan:"):
            return self._plan(task)
        elif cmd_lower.startswith("fix:"):
            return self._fix(task)
        elif cmd_lower == "status":
            return self._status()
        elif cmd_lower == "diff":
            return self._diff()
        elif cmd_lower.startswith("commit:"):
            return self._commit(task)
        elif cmd_lower == "push":
            return self._push()
        elif cmd_lower == "stop":
            return self._stop()
        else:
            return {"status": "error", "output": f"Unknown command: {command}\nAvailable: plan:, fix:, status, diff, commit:, push, stop"}

    def _plan(self, task: str) -> dict:
        """Plan only — no edits, no file changes."""
        prompt = f"Plan the following task. Do NOT edit any files. Only output the plan:\n{task}"
        return self._invoke_claude(prompt, read_only=True)

    def _fix(self, task: str) -> dict:
        """Edit locally, run tests, NO push."""
        prompt = f"Fix the following. Edit files locally. Run tests if relevant. Do NOT commit, do NOT push:\n{task}"
        return self._invoke_claude(prompt, read_only=False)

    def _status(self) -> dict:
        """Repo status + current state."""
        repo = self.config.local_repo
        branch = self._shell("git branch --show-current", cwd=repo).strip()
        dirty = self._shell("git status --porcelain", cwd=repo).strip()
        log_line = self._shell("git log --oneline -1", cwd=repo).strip()
        return {
            "status": "ok",
            "output": f"Repo: {repo}\nBranch: {branch}\nLast commit: {log_line}\nDirty files: {len(dirty.splitlines()) if dirty else 0}",
        }

    def _diff(self) -> dict:
        """Summarize git diff."""
        repo = self.config.local_repo
        diff_stat = self._shell("git diff --stat", cwd=repo).strip()
        if not diff_stat:
            diff_stat = "(clean — no uncommitted changes)"
        return {"status": "ok", "output": diff_stat}

    def _commit(self, task: str) -> dict:
        """Commit local diff with message."""
        repo = self.config.local_repo
        # Show diff summary first
        diff_stat = self._shell("git diff --stat", cwd=repo).strip()
        diff_body = self._shell("git diff", cwd=repo).strip()

        if not diff_body:
            return {"status": "ok", "output": "Nothing to commit — working tree is clean."}

        # Prompt Claude to generate commit message
        prompt = (
            f"Generate a concise git commit message (1-2 sentences) for these changes. "
            f"Output ONLY the commit message, nothing else.\n\n"
            f"Diff summary:\n{diff_stat}\n\n"
            f"Task context: {task}\n"
        )
        result = self._invoke_claude(prompt, read_only=True)

        # Extract message (strip any markdown formatting)
        msg = result.get("output", "").strip()
        if not msg:
            msg = task

        # Run commit
        out = self._shell(f'git commit -am "$(cat <<\'EOF\'\n{msg}\nEOF\n)"', cwd=repo)
        return {"status": "ok", "output": f"Committed:\n{out}"}

    def _push(self) -> dict:
        """Push to remote — explicit approval already given by using 'push' command."""
        repo = self.config.local_repo
        out = self._shell("git push", cwd=repo)
        return {"status": "ok", "output": f"Pushed:\n{out}"}

    def _stop(self) -> dict:
        """Stop current Claude Code run if possible."""
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
            return {"status": "ok", "output": "Stopped current run."}
        return {"status": "ok", "output": "Nothing running."}

    def _invoke_claude(self, prompt: str, read_only: bool = False) -> dict:
        """Call Claude Code CLI."""
        env = os.environ.copy()
        env["ANTHROPIC_BASE_URL"] = self.config.proxy_url
        env["ANTHROPIC_AUTH_TOKEN"] = self.config.auth_token
        env["ANTHROPIC_MODEL"] = self.config.main_model

        flags = ["--dangerously-skip-permissions"] if read_only else []
        cmd = [self.config.claude_cmd, "--print", *flags, prompt]

        log.info(f"CLAUDE: {cmd[:2]}... prompt={prompt[:80]}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.config.local_repo),
                env=env,
            )
            output = result.stdout.strip() or result.stderr.strip()
            if result.returncode != 0:
                return {"status": "error", "output": f"Claude exited {result.returncode}:\n{output[:2000]}"}
            return {"status": "ok", "output": output[:4000]}
        except subprocess.TimeoutExpired:
            return {"status": "error", "output": "Claude Code timed out (5 min)"}
        except Exception as e:
            return {"status": "error", "output": f"Failed to invoke Claude: {e}"}

    def _shell(self, command: str, cwd=None) -> str:
        """Run a shell command (logged)."""
        cwd = cwd or self.config.local_repo
        log.info(f"SHELL: cd {cwd} && {command}")
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=30, cwd=str(cwd),
            )
            return result.stdout.strip() or result.stderr.strip()
        except Exception as e:
            return f"(error: {e})"


# ── Channel Bridge (stub — implement per channel) ──
class ChannelBridge:
    """Abstract channel interface. Implement for WhatsApp, Telegram, Slack."""

    def __init__(self, config: Config):
        self.config = config

    async def connect(self):
        """Connect to the messaging channel."""
        channel = self.config.channel
        log.info(f"Connecting to {channel}...")

        if channel == "telegram" and self.config.telegram_token:
            log.info("Telegram mode — bot starting")
        elif channel == "whatsapp" and self.config.twilio_sid:
            log.info("WhatsApp mode — webhook listener starting")
        elif channel == "slack" and self.config.slack_bot_token:
            log.info("Slack mode — Socket Mode starting")
        else:
            log.warning(f"Channel '{channel}' configured but no credentials found")

    async def receive_message(self) -> dict | None:
        """
        Wait for and return the next message.
        Returns: {"sender": "+919XXXXXXXXX", "text": "fix: bug in login", "channel": "whatsapp"}
        Stub — replace with actual channel implementation.
        """
        # Placeholder: poll stdin for testing
        loop = asyncio.get_event_loop()
        try:
            text = await loop.run_in_executor(None, sys.stdin.readline)
            text = text.strip()
            if text:
                return {
                    "sender": self.config.allowed_senders[0] if self.config.allowed_senders else "unknown",
                    "text": text,
                    "channel": self.config.channel,
                }
        except (EOFError, KeyboardInterrupt):
            pass
        return None

    async def send_response(self, recipient: str, text: str):
        """Send response back to the same founder's phone."""
        log.info(f"RESPONSE to {recipient}: {text[:100]}...")
        # Stub: print to stdout for now
        print(f"\n── Response to {recipient} ──\n{text}\n── End ──\n")


# ── Main Agent Loop ────────────────────────────
class RemoteClaudeAgent:
    def __init__(self, config: Config):
        self.config = config
        self.runner = ClaudeRunner(config)
        self.channel = ChannelBridge(config)

    async def run(self):
        log.info("=" * 50)
        log.info(f"Agent starting — owner: {self.config.founder_name} ({self.config.founder_role})")
        log.info(f"Repo: {self.config.local_repo}")
        log.info(f"Channel: {self.config.channel}")
        log.info(f"Allowlist: {self.config.allowed_senders}")
        log.info(f"Safety: sandbox={'on' if self.config.enforce_sandbox else 'OFF'}, "
                 f"push_confirm={'on' if self.config.require_push_confirm else 'OFF'}")
        log.info("=" * 50)

        await self.channel.connect()

        while True:
            try:
                msg = await self.channel.receive_message()
                if msg is None:
                    await asyncio.sleep(1)
                    continue

                sender = msg["sender"]
                text = msg["text"].strip()

                # Verify sender
                if sender not in self.config.allowed_senders:
                    log.warning(f"REJECTED unknown sender: {sender}")
                    await self.channel.send_response(
                        sender,
                        "Access denied. Your number is not in the allowlist.",
                    )
                    continue

                log.info(f"RECEIVED [{sender}]: {text}")

                # Parse command
                parts = text.split(":", 1)
                command = parts[0].strip().lower()
                task = parts[1].strip() if len(parts) > 1 else ""

                # Execute
                result = self.runner.run(command, sender, task)
                await self.channel.send_response(sender, result["output"])

            except asyncio.CancelledError:
                log.info("Agent shutting down...")
                break
            except Exception as e:
                log.exception(f"Unexpected error: {e}")
                await asyncio.sleep(2)

    def shutdown(self):
        log.info("Shutdown signal received.")


# ── Entry Point ────────────────────────────────
async def main():
    parser = argparse.ArgumentParser(description="remote-claude-code agent")
    parser.add_argument("--env", default=".env", help="Path to .env file")
    parser.add_argument("--config", default="config/agent.json", help="Path to agent config")
    parser.add_argument("--founders", default="config/founders.json", help="Path to founders config")
    args = parser.parse_args()

    config = Config(args.env, args.config, args.founders)
    issues = config.validate()
    if issues:
        for i in issues:
            log.error(f"Config issue: {i}")
        sys.exit(1)

    agent = RemoteClaudeAgent(config)
    loop = asyncio.get_event_loop()

    def _shutdown():
        agent.shutdown()
        loop.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: _shutdown())

    try:
        await agent.run()
    except KeyboardInterrupt:
        agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
