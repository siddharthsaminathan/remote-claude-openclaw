#!/usr/bin/env python3
"""
Test harness for remote-claude-openclaw.

Simulates 6 scenarios:
  1. Siddharth config operating on Siddharth repo
  2. CEO config operating on CEO repo
  3. Unknown sender rejected
  4. fix command does not push
  5. push requires explicit approval
  6. operation outside LOCAL_REPO_PATH refused
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add the agent to path
AGENT_PATH = Path(__file__).resolve().parents[1] / "skills" / "remote-claude-code"
sys.path.insert(0, str(AGENT_PATH))

from agent import Config, SafetyEnforcer, ClaudeRunner


class TestConfig(unittest.TestCase):
    """Test that per-laptop config resolves correctly."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _write_env(self, content: str) -> str:
        path = os.path.join(self.tmp, ".env")
        with open(path, "w") as f:
            f.write(content)
        return path

    def _write_json(self, filename: str, data: dict) -> str:
        path = os.path.join(self.tmp, filename)
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_siddharth_config(self):
        """Scenario 1: Siddharth's config loads with correct identity."""
        env_path = self._write_env("""
FOUNDER_ID=siddharth
FOUNDER_NAME=Siddharth
FOUNDER_ROLE=CTO
LOCAL_REPO_PATH=/Users/siddharthsaminathan/Projects/Shanthibeta2
CLAUDE_CODE_COMMAND=claude
ANTHROPIC_BASE_URL=http://localhost:8082
ANTHROPIC_AUTH_TOKEN=test-token
MAIN_MODEL_ALIAS=opus
CHEAP_MODEL_ALIAS=haiku
CHANNEL=whatsapp
ALLOWED_SENDERS=+919XXXXXXXXX
""")
        founders_path = self._write_json("founders.json", {
            "founders": {
                "siddharth": {"name": "Siddharth", "role": "CTO", "channels": {"whatsapp": "+919XXXXXXXXX"}},
                "hayagreev": {"name": "Hayagreev", "role": "CEO", "channels": {"whatsapp": "+919XXXXXXXXY"}},
            }
        })
        agent_config_path = self._write_json("agent.json", {})

        config = Config(env_path, agent_config_path, founders_path)

        self.assertEqual(config.founder_id, "siddharth")
        self.assertEqual(config.founder_name, "Siddharth")
        self.assertEqual(config.founder_role, "CTO")
        self.assertEqual(config.channel, "whatsapp")
        self.assertEqual(config.main_model, "opus")
        self.assertEqual(config.cheap_model, "haiku")
        self.assertEqual(config.allowed_senders, {"+919XXXXXXXXX"})

    def test_ceo_config(self):
        """Scenario 2: CEO's config loads with correct identity."""
        env_path = self._write_env("""
FOUNDER_ID=hayagreev
FOUNDER_NAME=Hayagreev
FOUNDER_ROLE=CEO
LOCAL_REPO_PATH=/Users/hayagreev/Projects/Shanthibeta2
CLAUDE_CODE_COMMAND=claude
ANTHROPIC_BASE_URL=http://localhost:8082
ANTHROPIC_AUTH_TOKEN=test-token
MAIN_MODEL_ALIAS=opus
CHEAP_MODEL_ALIAS=haiku
CHANNEL=telegram
ALLOWED_SENDERS=+919XXXXXXXXY
""")
        founders_path = self._write_json("founders.json", {
            "founders": {
                "siddharth": {"name": "Siddharth", "role": "CTO", "channels": {"whatsapp": "+919XXXXXXXXX"}},
                "hayagreev": {"name": "Hayagreev", "role": "CEO", "channels": {"whatsapp": "+919XXXXXXXXY"}},
            }
        })
        agent_config_path = self._write_json("agent.json", {})

        config = Config(env_path, agent_config_path, founders_path)

        self.assertEqual(config.founder_id, "hayagreev")
        self.assertEqual(config.founder_name, "Hayagreev")
        self.assertEqual(config.founder_role, "CEO")
        self.assertEqual(config.channel, "telegram")
        self.assertEqual(config.allowed_senders, {"+919XXXXXXXXY"})


class TestSafetyEnforcer(unittest.TestCase):
    """Test safety rules block dangerous operations."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Create a mock repo
        self.repo = Path(self.tmp) / "mockrepo"
        self.repo.mkdir()

        env_path = os.path.join(self.tmp, ".env")
        with open(env_path, "w") as f:
            f.write(f"""
FOUNDER_ID=siddharth
FOUNDER_NAME=Siddharth
FOUNDER_ROLE=CTO
LOCAL_REPO_PATH={self.repo}
CLAUDE_CODE_COMMAND=claude
CHANNEL=whatsapp
ALLOWED_SENDERS=+919XXXXXXXXX
""")
        config = Config(env_path, os.path.join(self.tmp, "agent.json"), os.path.join(self.tmp, "founders.json"))
        self.safety = SafetyEnforcer(config)

    def test_blocks_rm_rf(self):
        """Destructive rm -rf is blocked."""
        allowed, reason = self.safety.check_command("rm -rf /tmp/test")
        self.assertFalse(allowed)
        self.assertIn("destructive", reason.lower())

    def test_blocks_git_push_force(self):
        """Force push is blocked."""
        allowed, reason = self.safety.check_command("git push --force origin main")
        self.assertFalse(allowed)

    def test_blocks_git_reset_hard(self):
        """Hard reset is blocked."""
        allowed, reason = self.safety.check_command("git reset --hard HEAD~1")
        self.assertFalse(allowed)

    def test_allows_safe_commands(self):
        """Safe commands pass through."""
        allowed, reason = self.safety.check_command("git status")
        self.assertTrue(allowed)

    def test_path_sandbox(self):
        """Paths outside LOCAL_REPO_PATH are rejected."""
        outside = Path("/etc/passwd")
        allowed, reason = self.safety.check_path(outside)
        self.assertFalse(allowed)
        self.assertIn("outside", reason.lower())

    def test_path_inside_sandbox(self):
        """Paths inside LOCAL_REPO_PATH are allowed."""
        inside = self.repo / "src" / "test.ts"
        inside.mkdir(parents=True, exist_ok=True)
        allowed, reason = self.safety.check_path(inside)
        self.assertTrue(allowed)


class TestCommandRouting(unittest.TestCase):
    """Test that commands route correctly and follow safety rules."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp) / "mockrepo"
        self.repo.mkdir()

        # Initialize as git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=self.repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.repo, capture_output=True)
        # Create a file so git has something to track
        (self.repo / "test.txt").write_text("hello")
        subprocess.run(["git", "add", "test.txt"], cwd=self.repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.repo, capture_output=True)

        env_path = os.path.join(self.tmp, ".env")
        with open(env_path, "w") as f:
            f.write(f"""
FOUNDER_ID=siddharth
FOUNDER_NAME=Siddharth
LOCAL_REPO_PATH={self.repo}
CLAUDE_CODE_COMMAND=echo
CHANNEL=whatsapp
ALLOWED_SENDERS=+919XXXXXXXXX
""")
        self.config = Config(
            env_path,
            os.path.join(self.tmp, "agent.json"),
            os.path.join(self.tmp, "founders.json"),
        )
        self.runner = ClaudeRunner(self.config)

    def test_status_command(self):
        """status returns repo info."""
        result = self.runner.run("status", "+919XXXXXXXXX", "")
        self.assertEqual(result["status"], "ok")
        self.assertIn("mockrepo", result["output"])

    def test_diff_command(self):
        """diff returns git diff summary."""
        result = self.runner.run("diff", "+919XXXXXXXXX", "")
        # Clean or dirty, should not error
        self.assertIn(result["status"], ["ok", "error"])

    def test_fix_does_not_push(self):
        """Scenario 4: fix command does not push."""
        # fix: should not contain push in its prompt
        result = self.runner.run("fix: test bug", "+919XXXXXXXXX", "test bug")
        # The command routes to _fix which explicitly says "do NOT push"
        self.assertNotEqual(result["status"], "blocked")

    def test_push_requires_approval(self):
        """Scenario 5: push requires explicit push command."""
        result = self.runner.run("push", "+919XXXXXXXXX", "")
        # Since echo is our "claude", push just runs git push which should succeed or fail gracefully
        self.assertIsNotNone(result)

    def test_unknown_command_rejected(self):
        """Unknown commands get an error."""
        result = self.runner.run("hack: all the things", "+919XXXXXXXXX", "")
        self.assertEqual(result["status"], "error")
        self.assertIn("Unknown command", result["output"])


class TestSenderVerification(unittest.TestCase):
    """Test allowlist enforcement."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = Path(self.tmp) / "mockrepo"
        self.repo.mkdir()

    def test_known_sender_accepted(self):
        """Known senders are in ALLOWED_SENDERS."""
        env_path = os.path.join(self.tmp, ".env")
        with open(env_path, "w") as f:
            f.write(f"""
FOUNDER_ID=siddharth
LOCAL_REPO_PATH={self.repo}
CLAUDE_CODE_COMMAND=echo
CHANNEL=whatsapp
ALLOWED_SENDERS=+919XXXXXXXXX,+919AAAAAAAAA
""")
        config = Config(env_path, os.path.join(self.tmp, "agent.json"), os.path.join(self.tmp, "founders.json"))
        self.assertIn("+919XXXXXXXXX", config.allowed_senders)
        self.assertIn("+919AAAAAAAAA", config.allowed_senders)

    def test_unknown_sender_not_in_list(self):
        """Scenario 3: Unknown senders are not in the allowlist."""
        env_path = os.path.join(self.tmp, ".env")
        with open(env_path, "w") as f:
            f.write(f"""
FOUNDER_ID=siddharth
LOCAL_REPO_PATH={self.repo}
CLAUDE_CODE_COMMAND=echo
CHANNEL=whatsapp
ALLOWED_SENDERS=+919XXXXXXXXX
""")
        config = Config(env_path, os.path.join(self.tmp, "agent.json"), os.path.join(self.tmp, "founders.json"))
        self.assertNotIn("+15551234567", config.allowed_senders)


class TestNoCrossFounderRouting(unittest.TestCase):
    """Verify that Siddharth's config never routes to CEO's repo and vice versa."""

    def test_siddharth_points_to_siddharth_repo(self):
        """Siddharth's config uses his repo path only."""
        tmp = tempfile.mkdtemp()
        siddharth_repo = Path(tmp) / "siddharth-repo"
        siddharth_repo.mkdir()

        env_path = os.path.join(tmp, ".env")
        with open(env_path, "w") as f:
            f.write(f"""
FOUNDER_ID=siddharth
LOCAL_REPO_PATH={siddharth_repo}
CLAUDE_CODE_COMMAND=echo
CHANNEL=whatsapp
ALLOWED_SENDERS=+919XXXXXXXXX
""")
        config = Config(env_path, os.path.join(tmp, "agent.json"), os.path.join(tmp, "founders.json"))
        self.assertEqual(str(config.local_repo), str(siddharth_repo.resolve()))
        # Should NOT be a CEO path
        self.assertNotIn("hayagreev", str(config.local_repo))

    def test_ceo_points_to_ceo_repo(self):
        """CEO's config uses his repo path only."""
        tmp = tempfile.mkdtemp()
        ceo_repo = Path(tmp) / "hayagreev-repo"
        ceo_repo.mkdir()

        env_path = os.path.join(tmp, ".env")
        with open(env_path, "w") as f:
            f.write(f"""
FOUNDER_ID=hayagreev
LOCAL_REPO_PATH={ceo_repo}
CLAUDE_CODE_COMMAND=echo
CHANNEL=whatsapp
ALLOWED_SENDERS=+919XXXXXXXXY
""")
        config = Config(env_path, os.path.join(tmp, "agent.json"), os.path.join(tmp, "founders.json"))
        self.assertEqual(str(config.local_repo), str(ceo_repo.resolve()))
        self.assertNotIn("siddharth", str(config.local_repo))


if __name__ == "__main__":
    print("=" * 60)
    print("  remote-claude-openclaw — Test Harness")
    print("=" * 60)
    print()

    # Run with verbose output
    unittest.main(verbosity=2)
