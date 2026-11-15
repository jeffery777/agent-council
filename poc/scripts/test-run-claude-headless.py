#!/usr/bin/env python3
"""Offline tests for run-claude-headless.py with a fake `claude` on PATH.

They check the script only (normal exit, timeout, process-group cleanup).
They start no real CLI and are no evidence of what the real CLI can do.
"""

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "run-claude-headless.py")

# The fake reads its mode from a file next to itself, because the runner
# passes only a few environment variables on to the CLI.
FAKE = r'''#!/usr/bin/env python3
import json, os, signal, subprocess, sys, time
here = os.path.dirname(os.path.abspath(__file__))
if "--version" in sys.argv:
    print("0.0.0 (fake)"); sys.exit(0)
mode = open(os.path.join(here, "mode")).read().strip()
late = os.path.join(here, "late-write")
child = ("import signal,time\n"
         "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
         "time.sleep(8)\n"
         "open(%r, 'w').write('late')\n" % late)
print(json.dumps({"type": "system", "subtype": "init", "model": "fake-model",
                  "tools": [], "permissionMode": "dontAsk", "mcp_servers": []}), flush=True)
if mode in ("leader-exits-child-stays", "timeout-child-ignores-term"):
    subprocess.Popen([sys.executable, "-c", child])
if mode == "timeout-child-ignores-term":
    time.sleep(60)
print(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                  "result": "NONE", "num_turns": 1}), flush=True)
'''


class RunnerTest(unittest.TestCase):
    def run_case(self, mode, timeout):
        with tempfile.TemporaryDirectory() as tmp:
            fake = os.path.join(tmp, "claude")
            with open(fake, "w") as fh:
                fh.write(FAKE)
            os.chmod(fake, 0o755)
            with open(os.path.join(tmp, "mode"), "w") as fh:
                fh.write(mode)
            # If the fake cannot run, PATH lookup could fall through to the real CLI.
            check = subprocess.run([fake, "--version"], capture_output=True, text=True)
            self.assertEqual(check.stdout.strip(), "0.0.0 (fake)")
            env = dict(os.environ, PATH=tmp + os.pathsep + os.environ["PATH"])
            env.pop("ANTHROPIC_API_KEY", None)
            env.pop("ANTHROPIC_AUTH_TOKEN", None)
            started = time.monotonic()
            out = subprocess.run([sys.executable, RUNNER, "memory-default", "--model", "fake-model",
                                  "--attempt", "0", "--timeout", str(timeout)],
                                 env=env, capture_output=True, text=True)
            elapsed = time.monotonic() - started
            self.assertEqual(out.returncode, 0, out.stderr)
            record = json.loads(out.stdout)
            # The runner gives the group 5 s after SIGTERM, so it returns before the
            # fake child would write (8 s). Wait until that moment has passed.
            time.sleep(max(0.0, 9 - elapsed))
            late_write = os.path.exists(os.path.join(tmp, "late-write"))
        return record, late_write, elapsed

    def test_normal_exit(self):
        record, late_write, _ = self.run_case("normal", 20)
        self.assertEqual(record["cli_version"], "0.0.0 (fake)")
        self.assertEqual(record["exit_code"], 0)
        self.assertEqual(record["error_class"], "none")
        self.assertEqual(record["model_reported"], "fake-model")
        self.assertFalse(record["notes"]["timed_out"])
        self.assertTrue(record["notes"]["process_group_stopped"])
        self.assertFalse(late_write)

    def test_leader_exits_and_child_stays(self):
        record, late_write, _ = self.run_case("leader-exits-child-stays", 20)
        self.assertEqual(record["exit_code"], 0)
        self.assertTrue(record["notes"]["process_group_stopped"])
        self.assertFalse(late_write, "a child wrote after the runner returned")

    def test_timeout_and_child_ignores_term(self):
        record, late_write, elapsed = self.run_case("timeout-child-ignores-term", 1)
        self.assertTrue(record["notes"]["timed_out"])
        self.assertEqual(record["error_class"], "timeout")
        self.assertNotEqual(record["exit_code"], 0)
        self.assertTrue(record["notes"]["process_group_stopped"])
        self.assertFalse(late_write, "a child wrote after the runner returned")
        self.assertLess(elapsed, 15)

    def test_group_stop_not_confirmed(self):
        """The signal call is refused: the record must not look like a clean run."""
        spec = importlib.util.spec_from_file_location("runner", RUNNER)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)

        def refused(pid, sig):
            raise PermissionError

        with tempfile.TemporaryDirectory() as tmp:
            fake = os.path.join(tmp, "claude")
            with open(fake, "w") as fh:
                fh.write(FAKE)
            os.chmod(fake, 0o755)
            with open(os.path.join(tmp, "mode"), "w") as fh:
                fh.write("normal")  # no child is left behind, so nothing needs a real signal
            check = subprocess.run([fake, "--version"], capture_output=True, text=True)
            self.assertEqual(check.stdout.strip(), "0.0.0 (fake)")
            argv = ["runner", "memory-default", "--model", "fake-model", "--attempt", "0"]
            clean = {k: v for k, v in os.environ.items()
                     if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
            clean["PATH"] = tmp + os.pathsep + os.environ["PATH"]
            out = io.StringIO()
            with mock.patch.object(runner.os, "killpg", refused), \
                    mock.patch.object(runner.stop_group, "__defaults__", (0.2,)), \
                    mock.patch.dict(os.environ, clean, clear=True), \
                    mock.patch.object(sys, "argv", argv), \
                    contextlib.redirect_stdout(out), \
                    self.assertRaises(SystemExit) as stopped:
                runner.main()
        self.assertNotIn(stopped.exception.code, (0, None))
        record = json.loads(out.getvalue())
        self.assertEqual(record["cli_version"], "0.0.0 (fake)")
        self.assertEqual(record["exit_code"], 0)  # the CLI's own exit code is kept
        self.assertFalse(record["notes"]["process_group_stopped"])
        self.assertEqual(record["error_class"], "other")
        self.assertEqual(record["notes"]["test_repo_unchanged"], "unconfirmed")


if __name__ == "__main__":
    unittest.main()
