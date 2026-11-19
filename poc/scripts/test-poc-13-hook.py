#!/usr/bin/env python3
"""Offline tests for the PoC-13 hook, channel and install script.

They start no CLI and no session, and they do not touch the real test repo:
the install script runs in a throwaway copy with its own fake test repo.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HOOK = pathlib.Path(__file__).resolve().parent.parent / "poc-13" / "hook.py"


class HookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = pathlib.Path(self.tmp.name)
        self.root = self.project / ".poc-13"
        self.env = {"PATH": os.environ["PATH"], "CLAUDE_PROJECT_DIR": str(self.project)}

    def tearDown(self):
        self.tmp.cleanup()

    def run_hook(self, mode, event, **kwargs):
        return subprocess.run([sys.executable, "-B", str(HOOK), mode], env=self.env,
                              input=json.dumps(event), capture_output=True, text=True,
                              timeout=20, **kwargs)

    def send(self, box, ident):
        (self.root / box).mkdir(parents=True, exist_ok=True)
        (self.root / box / f"{ident}.msg").write_text(f"body {ident}\n")

    def events(self):
        return [json.loads(line) for line in (self.root / "events.jsonl").read_text().splitlines()]

    def test_log_records_the_event_and_prints_nothing(self):
        done = self.run_hook("log", {"hook_event_name": "Stop", "session_id": "s", "transcript_path": "/x",
                                     "last_assistant_message": "x" * 999, "secret": "no"})
        self.assertEqual((done.returncode, done.stdout), (0, ""))
        record = self.events()[0]
        self.assertEqual(record["event"], "Stop")
        self.assertEqual(len(record["last_assistant_message"]), 300)
        self.assertNotIn("secret", record)
        self.assertNotIn("transcript_path", record)

    def test_settings_parse_and_the_watcher_fits_in_the_hook_timeout(self):
        self.assertIn("WAIT_SECONDS = 840", HOOK.read_text())
        for name in ("inject", "rewake", "channel"):
            hooks = json.loads((HOOK.parent / f"settings.{name}.json").read_text())["hooks"]
            for group in (g for groups in hooks.values() for g in groups):
                for hook in group["hooks"]:
                    if hook.get("asyncRewake"):
                        self.assertGreater(hook["timeout"], 840)
                    # With no hook file installed the command must not exit 2,
                    # which Claude Code would read as "block".
                    done = subprocess.run(["bash", "-c", hook["command"]], env=self.env,
                                          input="{}", capture_output=True, text=True,
                                          timeout=20)
                    self.assertEqual((done.returncode, done.stdout), (0, ""))

    def test_inject_adds_context_and_consumes_the_message(self):
        self.send("inbox", "A1")
        done = self.run_hook("inject", {"hook_event_name": "UserPromptSubmit", "prompt": "hi"})
        reply = json.loads(done.stdout)["hookSpecificOutput"]
        self.assertEqual(reply["hookEventName"], "UserPromptSubmit")
        self.assertIn("[poc-13 message A1] body A1", reply["additionalContext"])
        self.assertTrue((self.root / "delivered" / "A1.msg").exists())
        again = self.run_hook("inject", {"hook_event_name": "UserPromptSubmit"})
        self.assertEqual(again.stdout, "")

    def test_inject_blocks_stop_with_the_message(self):
        self.send("inbox", "A2")
        done = self.run_hook("inject", {"hook_event_name": "Stop"})
        reply = json.loads(done.stdout)
        self.assertEqual(reply["decision"], "block")
        self.assertIn("A2", reply["reason"])

    def test_inject_leaves_the_message_on_events_that_cannot_carry_it(self):
        self.send("inbox", "A3")
        for name in ("Notification", "SessionEnd"):
            done = self.run_hook("inject", {"hook_event_name": name})
            self.assertEqual(done.stdout, "")
        self.assertTrue((self.root / "inbox" / "A3.msg").exists())

    def test_inject_ignores_the_rewake_box(self):
        self.send("rewake", "B0")
        done = self.run_hook("inject", {"hook_event_name": "UserPromptSubmit"})
        self.assertEqual(done.stdout, "")

    def test_wait_exits_2_with_the_message_on_stderr(self):
        proc = subprocess.Popen([sys.executable, "-B", str(HOOK), "wait"], env=self.env,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        proc.stdin.write(json.dumps({"hook_event_name": "Stop"}))
        proc.stdin.close()
        time.sleep(1.5)
        self.assertIsNone(proc.poll())
        self.send("rewake", "B1")
        self.assertEqual(proc.wait(timeout=10), 2)
        self.assertIn("[poc-13 message B1] body B1", proc.stderr.read())
        proc.stdout.close(); proc.stderr.close()
        self.assertFalse((self.root / "watcher.pid").exists())
        self.assertIn("asyncRewake", [e.get("via") for e in self.events()])

    def test_second_watcher_steps_aside(self):
        first = subprocess.Popen([sys.executable, "-B", str(HOOK), "wait"], env=self.env,
                                 stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(1.5)
            second = self.run_hook("wait", {"hook_event_name": "Stop"})
            self.assertEqual(second.returncode, 0)
            self.assertEqual(self.events()[-1]["state"], "skipped")
        finally:
            first.terminate(); first.wait(timeout=10)

    def test_channel_answers_initialize_and_pushes_one_event(self):
        channel = HOOK.parent / "channel.py"
        proc = subprocess.Popen([sys.executable, "-B", str(channel)], env=self.env,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                         "params": {"protocolVersion": "2025-06-18"}}) + "\n")
            proc.stdin.flush()
            reply = json.loads(proc.stdout.readline())
            self.assertEqual(reply["id"], 1)
            self.assertIn("claude/channel", reply["result"]["capabilities"]["experimental"])
            self.send("channel", "C0")  # before `initialized`: must wait
            time.sleep(1.2)
            self.assertTrue((self.root / "channel" / "C0.msg").exists())
            proc.stdin.write(json.dumps({"jsonrpc": "2.0",
                                         "method": "notifications/initialized"}) + "\n")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n")
            proc.stdin.flush()
            lines = [json.loads(proc.stdout.readline()) for _ in range(2)]
            event = next(m for m in lines if m.get("method") == "notifications/claude/channel")
            self.assertEqual(event["params"], {"content": "body C0", "meta": {"id": "C0"}})
            error = next(m for m in lines if m.get("id") == 2)
            self.assertEqual(error["error"]["code"], -32601)
        finally:
            proc.stdin.close(); proc.wait(timeout=10); proc.stdout.close()
        self.assertEqual(proc.returncode, 0)

    def test_without_the_project_variable_the_hook_does_nothing(self):
        done = subprocess.run([sys.executable, "-B", str(HOOK), "inject"],
                              env={"PATH": os.environ["PATH"]}, input="{}",
                              capture_output=True, text=True, timeout=20)
        self.assertEqual((done.returncode, done.stdout), (0, ""))
        self.assertFalse(self.root.exists())


class PrepareTest(unittest.TestCase):
    """prepare-poc-13.sh in a sandbox: <tmp>/main is a copy of the scripts,
    <tmp>/agent-council-poc-testrepo is a fake test repo."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = pathlib.Path(self.tmp.name)
        poc = HOOK.parent.parent
        for name in ("scripts", "poc-13", "fixtures"):
            shutil.copytree(poc / name, base / "main" / "poc" / name)
        self.repo = base / "agent-council-poc-testrepo"
        self.repo.mkdir()
        (self.repo / ".poc-testrepo-marker").touch()
        env = {"PATH": os.environ["PATH"], "GIT_CONFIG_GLOBAL": os.devnull,
               "GIT_CONFIG_NOSYSTEM": "1"}
        for where in (base / "main", self.repo):
            subprocess.run(["git", "init", "-q", str(where)], env=env, check=True,
                           capture_output=True)
        self.env = env
        self.script = base / "main" / "poc" / "scripts" / "prepare-poc-13.sh"
        self.settings = self.repo / ".claude" / "settings.local.json"
        self.mcp = self.repo / ".mcp.json"

    def tearDown(self):
        self.tmp.cleanup()

    def prepare(self, profile):
        return subprocess.run([str(self.script), profile], env=self.env,
                              capture_output=True, text=True, timeout=30)

    def test_profiles_switch_and_remove_cleanly(self):
        self.assertEqual(self.prepare("channel").returncode, 0)
        self.assertTrue(self.mcp.exists())
        self.assertEqual(self.prepare("rewake").returncode, 0)
        self.assertFalse(self.mcp.exists())
        self.assertEqual((self.repo / ".poc-13" / "profile").read_text().strip(), "rewake")
        self.assertEqual(self.prepare("remove").returncode, 0)
        self.assertFalse(self.settings.exists())
        self.assertFalse((self.repo / ".poc-13" / "profile").exists())

    def test_edited_settings_are_neither_replaced_nor_removed(self):
        self.assertEqual(self.prepare("inject").returncode, 0)
        edited = json.loads(self.settings.read_text())
        edited["permissions"] = {"deny": ["Bash(rm:*)"]}  # the PoC hooks stay in place
        self.settings.write_text(json.dumps(edited, indent=2) + "\n")
        before = self.settings.read_bytes()
        for profile in ("rewake", "channel", "remove"):
            self.assertEqual(self.prepare(profile).returncode, 1, profile)
            self.assertEqual(self.settings.read_bytes(), before, profile)
        self.assertFalse(self.mcp.exists())

    def test_edited_mcp_config_is_neither_replaced_nor_removed(self):
        self.assertEqual(self.prepare("channel").returncode, 0)
        edited = json.loads(self.mcp.read_text())
        edited["mcpServers"]["other"] = {"command": "true"}  # poc13 stays in place
        self.mcp.write_text(json.dumps(edited, indent=2) + "\n")
        before = (self.mcp.read_bytes(), self.settings.read_bytes())
        for profile in ("inject", "channel", "remove"):
            self.assertEqual(self.prepare(profile).returncode, 1, profile)
            self.assertEqual((self.mcp.read_bytes(), self.settings.read_bytes()), before, profile)

    def test_files_from_someone_else_stop_install_and_remove(self):
        self.settings.parent.mkdir()
        self.settings.write_text("{}\n")
        for profile in ("inject", "remove"):
            self.assertEqual(self.prepare(profile).returncode, 1, profile)
        self.assertEqual(self.settings.read_text(), "{}\n")


if __name__ == "__main__":
    unittest.main()
