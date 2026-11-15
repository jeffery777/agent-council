#!/usr/bin/env python3
"""Offline runner checks; no real Codex, authentication or subscription use.

The fake processes operate only under poc/local/. These tests establish the
wrapper's failure handling, not the capabilities of a real CLI or sandbox.
"""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("codex_runner", HERE / "run-codex-headless.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

FAKE = r'''
import os, signal, subprocess, sys, time
mode, marker = sys.argv[1:]
if mode in ("child-stays", "timeout"):
    child = "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(1.2); open(%r,'w').write('late')" % marker
    subprocess.Popen([sys.executable, "-c", child])
if mode == "timeout":
    time.sleep(30)
if mode == "usage-limit":
    print('{"type":"error","message":"You have hit your usage limit."}', flush=True)
    time.sleep(30)
print('{"type":"turn.completed"}', flush=True)
'''


class RunnerTests(unittest.TestCase):
    def folder(self):
        root = runner.REPO / "poc/local/offline-codex-tests"
        root.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(dir=root))

    def process(self, mode):
        folder = self.folder()
        marker = folder / "late-write"
        original = runner.stop_group
        with mock.patch.object(runner, "stop_group", lambda p: original(p, grace=0.15)):
            outcome = runner.run_process([sys.executable, "-c", FAKE, mode, str(marker)],
                                         "fixture", folder, dict(os.environ), folder,
                                         0.2 if mode == "timeout" else 5)
        time.sleep(1.3)
        self.assertFalse(marker.exists(), "child wrote after group cleanup")
        self.assertTrue(outcome["process_group_stopped"])
        return outcome

    def test_normal_exit(self):
        self.assertEqual(self.process("normal")["exit_code"], 0)

    def test_leader_exits_child_stays(self):
        self.assertEqual(self.process("child-stays")["exit_code"], 0)

    def test_timeout_kills_term_ignoring_child(self):
        result = self.process("timeout")
        self.assertTrue(result["timed_out"])
        self.assertNotEqual(result["exit_code"], 0)

    def test_stop_failure_is_not_success(self):
        folder = self.folder()
        with mock.patch.object(runner.os, "killpg", side_effect=PermissionError):
            original = runner.stop_group
            with mock.patch.object(runner, "stop_group", lambda p: original(p, grace=0.02)):
                result = runner.run_process([sys.executable, "-c", "pass"], "",
                                            folder, dict(os.environ), folder, 5)
        self.assertFalse(result["process_group_stopped"])
        self.assertEqual(runner.error_class(result, {"events": []}, ""), "other")

    def test_usage_limit_stops_without_waiting_for_timeout(self):
        folder = self.folder()
        result = runner.run_process([sys.executable, "-c", FAKE, "usage-limit", str(folder / "late")],
                                    "fixture", folder, dict(os.environ), folder, 5)
        self.assertTrue(result["usage_limit_observed"])
        self.assertFalse(result["timed_out"])
        self.assertLess(result["duration_ms"], 2000)
        self.assertTrue(result["process_group_stopped"])
        result["timed_out"] = True
        self.assertEqual(runner.error_class(result, {"events": []}, ""), "usage_limit")
        agent = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "usage limit"}})
        self.assertFalse(runner.usage_limit_seen(agent, ""))

    def test_snapshot_not_taken_after_unconfirmed_stop(self):
        folder = self.folder()
        fixture = folder / "fixture"
        fixture.mkdir()
        fake_auth = type("Result", (), {"stdout": "Logged in using ChatGPT", "stderr": ""})()
        before = {"head": "fixture", "status": "", "tree_sha256": "fixture"}
        with mock.patch.object(runner, "LOCAL", folder), \
                mock.patch.object(runner, "environment", return_value={"HOME": str(folder)}), \
                mock.patch.object(runner, "test_repo_path", return_value=fixture), \
                mock.patch.object(runner, "command", return_value=fake_auth), \
                mock.patch.object(runner, "repo_state", return_value=before) as snapshot, \
                mock.patch.object(runner, "run_process") as run, \
                mock.patch.object(sys, "argv", ["runner", "poc-06-write", "--model", "fake-model", "--attempt", "1"]), \
                contextlib.redirect_stdout(io.StringIO()):
            def fake_run(argv, prompt, cwd, env, output, timeout):
                (output / "stdout.jsonl").write_text("")
                (output / "stderr.txt").write_text("")
                return {"exit_code": 0, "timed_out": False, "process_group_stopped": False, "duration_ms": 1}
            run.side_effect = fake_run
            self.assertEqual(runner.main(), 1)
            self.assertEqual(snapshot.call_count, 1)
        record = json.loads(next(folder.glob("*/record.json")).read_text())
        self.assertEqual(record["notes"]["test_repo_unchanged"], "unconfirmed")

    def test_no_model_inference_or_fake_denial_from_agent_text(self):
        schema = json.loads((runner.REPO / "poc/poc-06/output.schema.json").read_text())
        final = json.dumps({"task_id": "poc-06-write", "outcome": "denied", "detail": "gpt-model says denied"})
        raw = "\n".join(json.dumps(e) for e in [
            {"type": "thread.started", "thread_id": "not-retained"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": final}},
            {"type": "turn.completed"}])
        obs = runner.observations(raw, final, schema, "poc-06-write")
        self.assertEqual(obs["model_reported"], "unknown")
        self.assertEqual(obs["tools"], [])
        self.assertTrue(obs["output_format_valid"])
        self.assertFalse(runner.observations(raw, "{}", schema, "poc-06-write")["output_format_valid"])
        self.assertEqual(runner.observations(raw + "\nnot-json", final, schema, "poc-06-write")["malformed_jsonl_lines"], 1)

    def test_environment_excludes_parent_keys_and_rejects_dotenv_key(self):
        folder = self.folder()
        with mock.patch.dict(os.environ, {"HOME": str(folder), "PATH": os.environ["PATH"],
                                          "OPENAI_API_KEY": "offline-fixture-only", "CODEX_THREAD_ID": "fixture"}, clear=True):
            env = runner.environment()
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertNotIn("CODEX_THREAD_ID", env)
            (folder / ".codex").mkdir()
            (folder / ".codex/.env").write_text("export OPENAI_API_KEY=offline-fixture-only\n")
            with self.assertRaisesRegex(RuntimeError, "dotenv"):
                runner.environment()

    def test_error_class_uses_harness_errors(self):
        outcome = {"timed_out": False, "process_group_stopped": True, "exit_code": 0}
        obs = {"events": [{"type": "error", "message": "usage_limit reached"}],
               "tools": [], "output_format_valid": False, "malformed_jsonl_lines": 0}
        self.assertEqual(runner.error_class(outcome, obs, ""), "usage_limit")
        obs["events"] = [{"type": "error", "message": "authentication failed"}]
        self.assertEqual(runner.error_class(outcome, obs, ""), "auth")

    def test_router_denial_without_file_change_event(self):
        stderr = "2026-01-01T00:00:00Z ERROR codex_core::tools::router: error=patch rejected: writing is blocked by read-only sandbox; rejected by user approval settings\n"
        self.assertEqual(len(runner.harness_denials(stderr)), 1)
        self.assertEqual(runner.harness_denials("model says patch rejected"), [])
        outcome = {"timed_out": False, "process_group_stopped": True, "exit_code": 0}
        self.assertEqual(runner.error_class(outcome, {"events": [], "tools": []}, stderr), "approval_blocked")


if __name__ == "__main__":
    unittest.main()
