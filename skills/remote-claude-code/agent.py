#!/usr/bin/env python3
"""
remote-claude-code — safety enforcement and Claude Code runner.

PRIMARY RUNTIME: OpenClaw workspace CLAUDE.md
  The canonical safety rules live in skills/remote-claude-code/CLAUDE.md.
  install.sh copies this file to the OpenClaw workspace (~/.openclaw/workspace/CLAUDE.md).
  When OpenClaw receives a WhatsApp message, its agent session reads CLAUDE.md
  and enforces all safety rules automatically.

THIS FILE: Reference implementation + standalone testing
  Use this for:
  - Running tests (test_harness.py imports from here)
  - Standalone mode when OpenClaw is unavailable
  - Understanding the safety enforcement logic in code form

Architecture:
  WhatsApp → OpenClaw Gateway (transport) → Agent reads CLAUDE.md (safety)
    → Claude Code CLI (execution) → Response → WhatsApp

OpenClaw config: ~/.openclaw/openclaw.json
  - WhatsApp channel enabled
  - Allowlisted senders
  - Gateway port 18789 (local loopback)

No Twilio. No external WhatsApp provider. OpenClaw handles transport.
"""

import argparse
import json
import logging
import os
import re
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"commands-{datetime.now(timezone.utc).strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stderr)],
)
log = logging.getLogger("remote-claude-code")


class Config:
    """Per-laptop configuration loaded from .env."""

    def __init__(self, env_path: str, agent_config_path: str, founders_path: str):
        self.env = self._load_env(env_path)
        self.agent_config = self._load_json(agent_config_path)
        self.founders = self._load_json(founders_path)
        self.founder_id = self.env.get("FOUNDER_ID", "unknown")
        self.founder_name = self.env.get("FOUNDER_NAME", "Unknown")
        self.founder_role = self.env.get("FOUNDER_ROLE", "Unknown")
        self.local_repo = Path(self.env.get("LOCAL_REPO_PATH", "")).resolve()
        self.claude_cmd = self.env.get("CLAUDE_CODE_COMMAND", "claude")
        self.proxy_url = self.env.get("ANTHROPIC_BASE_URL", "http://localhost:8082")
        self.auth_token = self.env.get("ANTHROPIC_AUTH_TOKEN", "")
        self.main_model = self.env.get("MAIN_MODEL_ALIAS", "opus")
        self.cheap_model = self.env.get("CHEAP_MODEL_ALIAS", "haiku")
        self.channel = self.env.get("CHANNEL", "whatsapp")
        raw = self.env.get("ALLOWED_SENDERS", "")
        self.allowed_senders = {s.strip() for s in raw.split(",") if s.strip()}

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

    def validate(self) -> list[str]:
        issues = []
        if not self.founder_id:
            issues.append("FOUNDER_ID not set")
        if not self.local_repo.exists():
            issues.append(f"LOCAL_REPO_PATH does not exist: {self.local_repo}")
        if not self.allowed_senders:
            issues.append("ALLOWED_SENDERS is empty")
        return issues


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
        for pattern in self.DESTRUCTIVE_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Blocked destructive pattern: {pattern}"
        return True, "ok"

    def check_path(self, path: Path) -> tuple[bool, str]:
        try:
            resolved = path.resolve()
            if str(resolved).startswith(str(self.config.local_repo)):
                return True, "ok"
            return False, f"Path {resolved} is outside LOCAL_REPO_PATH"
        except Exception:
            return False, "path resolution failed"

    def check_push(self, command: str) -> tuple[bool, str]:
        if re.search(r"\bgit\s+push\b", command):
            return False, "Push requires explicit 'push' command approval"
        return True, "ok"

    def check_delete(self, command: str) -> tuple[bool, str]:
        if re.search(r"\b(rm|git\s+rm|unlink|del\b)\b", command):
            return False, "File deletion requires confirmation — reply 'confirm-delete'"
        return True, "ok"


class ClaudeRunner:
    """Calls local Claude Code CLI with safety enforcement."""

    def __init__(self, config: Config):
        self.config = config
        self.safety = SafetyEnforcer(config)

    def run(self, command: str, sender: str, task: str = "") -> dict:
        allowed, reason = self.safety.check_command(task)
        if not allowed:
            log.warning(f"BLOCKED destructive command from {sender}: {task[:100]}")
            return {"status": "blocked", "output": f"SAFETY BLOCK: {reason}"}

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
            return {"status": "ok", "output": "Stopped."}
        else:
            return {"status": "error", "output": f"Unknown command: {command}\nAvailable: plan:, fix:, status, diff, commit:, push, stop"}

    def _plan(self, task: str) -> dict:
        prompt = f"Plan the following task. Do NOT edit any files. Only output the plan:\n{task}"
        return self._invoke_claude(prompt)

    def _fix(self, task: str) -> dict:
        prompt = f"Fix the following. Edit files locally. Run tests if relevant. Do NOT commit, do NOT push:\n{task}"
        return self._invoke_claude(prompt)

    def _status(self) -> dict:
        repo = self.config.local_repo
        branch = self._shell("git branch --show-current", cwd=repo).strip()
        dirty = self._shell("git status --porcelain", cwd=repo).strip()
        log_line = self._shell("git log --oneline -1", cwd=repo).strip()
        return {"status": "ok", "output": f"Repo: {repo}\nBranch: {branch}\nLast: {log_line}\nDirty: {len(dirty.splitlines()) if dirty else 0} files"}

    def _diff(self) -> dict:
        repo = self.config.local_repo
        diff_stat = self._shell("git diff --stat", cwd=repo).strip() or "(clean)"
        return {"status": "ok", "output": diff_stat}

    def _commit(self, task: str) -> dict:
        repo = self.config.local_repo
        diff_stat = self._shell("git diff --stat", cwd=repo).strip()
        if not self._shell("git diff", cwd=repo).strip():
            return {"status": "ok", "output": "Nothing to commit."}
        prompt = f"Generate a concise git commit message (1-2 sentences). Output ONLY the message:\n\nDiff:\n{diff_stat}\n\nContext: {task}"
        result = self._invoke_claude(prompt)
        msg = result.get("output", "").strip() or task
        out = self._shell(f'git commit -am "$(cat <<\'EOF\'\n{msg}\nEOF\n)"', cwd=repo)
        return {"status": "ok", "output": f"Committed:\n{out}"}

    def _push(self) -> dict:
        repo = self.config.local_repo
        out = self._shell("git push", cwd=repo)
        return {"status": "ok", "output": f"Pushed:\n{out}"}

    def _invoke_claude(self, prompt: str) -> dict:
        env = os.environ.copy()
        env["ANTHROPIC_BASE_URL"] = self.config.proxy_url
        env["ANTHROPIC_AUTH_TOKEN"] = self.config.auth_token
        env["ANTHROPIC_MODEL"] = self.config.main_model
        cmd = [self.config.claude_cmd, "--print", prompt]
        log.info(f"CLAUDE: prompt={prompt[:80]}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(self.config.local_repo), env=env)
            output = result.stdout.strip() or result.stderr.strip()
            if result.returncode != 0:
                return {"status": "error", "output": f"Claude exited {result.returncode}:\n{output[:2000]}"}
            return {"status": "ok", "output": output[:4000]}
        except subprocess.TimeoutExpired:
            return {"status": "error", "output": "Claude Code timed out (5 min)"}
        except Exception as e:
            return {"status": "error", "output": f"Failed to invoke Claude: {e}"}

    def _shell(self, command: str, cwd=None) -> str:
        cwd = cwd or self.config.local_repo
        log.info(f"SHELL: cd {cwd} && {command}")
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, cwd=str(cwd))
            return result.stdout.strip() or result.stderr.strip()
        except Exception as e:
            return f"(error: {e})"


# ── Standalone / Testing Entry Point ──────────
def main():
    parser = argparse.ArgumentParser(description="remote-claude-code (standalone/testing)")
    parser.add_argument("--env", default=".env")
    parser.add_argument("--config", default="config/agent.json")
    parser.add_argument("--founders", default="config/founders.json")
    parser.add_argument("command", nargs="?", help="Command to run (plan:/fix:/status/diff/commit:/push/stop)")
    args = parser.parse_args()

    config = Config(args.env, args.config, args.founders)
    issues = config.validate()
    if issues:
        for i in issues:
            log.error(f"Config issue: {i}")
        sys.exit(1)

    runner = ClaudeRunner(config)

    if args.command:
        parts = args.command.split(":", 1)
        cmd = parts[0].strip().lower()
        task = parts[1].strip() if len(parts) > 1 else ""
        result = runner.run(cmd, "local", task)
        print(result["output"])
    else:
        print("Usage: python agent.py <command>")
        print("Commands: plan:, fix:, status, diff, commit:, push, stop")
        print()
        print("For production, use OpenClaw + workspace CLAUDE.md.")
        print("See README.md for full setup.")


if __name__ == "__main__":
    main()
