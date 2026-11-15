#!/usr/bin/env python3
"""Run one authorized M1 Codex case and retain an m1-r2 record locally.

Throwaway PoC code; standard library only. Codex's dotenv is read to check
variable names only; its contents are not retained. Unknown observations stay
unknown. Offline tests are not CLI evidence.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shlex
import stat
import subprocess
import time
import uuid

REPO = Path(__file__).resolve().parents[2]
LOCAL = REPO / "poc/local/codex"
CASES = {
    "poc-04": ("PoC-04", "poc-04/prompt.md", "poc-04/output.schema.json"),
    "poc-06-read": ("PoC-06", "poc-06/read-task.md", "poc-06/output.schema.json"),
    "poc-06-write": ("PoC-06", "poc-06/write-task.md", "poc-06/output.schema.json"),
}
OVERRIDES = [
    'forced_login_method="chatgpt"', 'model_provider="openai"',
    'approval_policy="never"', 'history.persistence="none"',
    "memories.use_memories=false", "memories.generate_memories=false",
    "features.memories=false", "features.shell_snapshot=false",
    "features.apps=false", "features.plugins=false", "features.hooks=false",
    "features.multi_agent=false", "features.multi_agent_v2=false",
    'web_search="disabled"', "project_doc_max_bytes=0",
]
ENV_NAMES = ("HOME", "PATH", "LANG", "LC_ALL", "TMPDIR", "SHELL")


def command(args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                          text=True, check=True, timeout=30)


def api_variable(name):
    return ("API_KEY" in name.upper() or name.upper() in {
        "ANTHROPIC_AUTH_TOKEN", "OPENAI_ACCESS_TOKEN", "CODEX_ACCESS_TOKEN"})


def environment():
    """Do not pass parent agent credentials, proxy overrides or runtime identity."""
    env = {k: os.environ[k] for k in ENV_NAMES if k in os.environ}
    if any(api_variable(k) for k in env):
        raise RuntimeError("API-key variable in child environment")
    # Codex loads this dotenv even with --ignore-user-config. Examine names only;
    # never retain its values, or read auth.json / a credential helper ourselves.
    home = Path(env["HOME"]) / ".codex"
    dotenv = home / ".env"
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            line = line.strip().removeprefix("export ").strip()
            if line and not line.startswith("#") and "=" in line:
                if api_variable(line.split("=", 1)[0].strip()):
                    raise RuntimeError("API-key variable in Codex dotenv")
    return env


def test_repo_path(env):
    out = command([str(REPO / "poc/scripts/create-test-repo.sh"), "--print-path"], env=env)
    path = Path(out.stdout.strip()).resolve()
    if not (path / ".poc-testrepo-marker").is_file() or not (path / ".git").is_dir():
        raise RuntimeError("existing local test repository not found; do not create it")
    if command(["git", "remote"], cwd=path, env=env).stdout.strip():
        raise RuntimeError("test repository has a remote")
    return path


def repo_state(path, env=None):
    """Hash file bytes, modes, links and empty directories, including .git."""
    head = command(["git", "rev-parse", "HEAD"], cwd=path, env=env).stdout.strip()
    status = command(["git", "--no-optional-locks", "status", "--porcelain=v1",
                      "--untracked-files=all", "--ignored"], cwd=path, env=env).stdout
    digest = hashlib.sha256()
    for root, dirs, files in os.walk(path, followlinks=False):
        dirs.sort()
        for name in sorted(dirs + files):
            p = Path(root) / name
            mode = p.lstat().st_mode
            digest.update(json.dumps([str(p.relative_to(path)), mode]).encode())
            if stat.S_ISLNK(mode):
                digest.update(os.readlink(p).encode())
            elif stat.S_ISREG(mode):
                digest.update(hashlib.sha256(p.read_bytes()).digest())
            elif not stat.S_ISDIR(mode):
                raise RuntimeError("unsupported special file in test repository")
    return {"head": head, "status": status, "tree_sha256": digest.hexdigest()}


def stop_group(proc, grace=3.0):
    """Confirm the whole group is gone, even when the leader exited normally."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            proc.wait()
            return True
        except PermissionError:
            pass
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            proc.poll()
            try:
                os.killpg(proc.pid, 0)
            except ProcessLookupError:
                proc.wait()
                return True
            except PermissionError:
                pass
            time.sleep(0.05)
    return False


def usage_limit_seen(raw, stderr):
    """Read only harness errors, excluding assertions in agent messages."""
    errors = []
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") in {"error", "turn.failed"}:
            errors.append(event)
    return bool(re.search(r"usage.?limit|usage_limit|quota exceeded|rate.?limit exceeded",
                          (json.dumps(errors) + stderr).lower()))


def run_process(argv, prompt, cwd, env, folder, timeout):
    timed_out = False
    usage_limit_observed = False
    start = time.monotonic()
    with (folder / "stdout.jsonl").open("xb") as out, (folder / "stderr.txt").open("xb") as err:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                stdout=out, stderr=err, start_new_session=True)
        try:
            try:
                proc.stdin.write(prompt.encode())
                proc.stdin.close()
            except BrokenPipeError:
                pass
            while True:
                usage_limit_observed = usage_limit_seen(
                    (folder / "stdout.jsonl").read_text(errors="replace"),
                    (folder / "stderr.txt").read_text(errors="replace"))
                if usage_limit_observed or proc.poll() is not None:
                    break
                if time.monotonic() - start >= timeout:
                    timed_out = True
                    break
                time.sleep(0.05)
        finally:
            stopped = stop_group(proc)
    usage_limit_observed |= usage_limit_seen(
        (folder / "stdout.jsonl").read_text(errors="replace"),
        (folder / "stderr.txt").read_text(errors="replace"))
    return {"exit_code": proc.returncode, "timed_out": timed_out,
            "usage_limit_observed": usage_limit_observed,
            "process_group_stopped": stopped,
            "duration_ms": round((time.monotonic() - start) * 1000)}


def validate(value, schema, where="$"):
    """Validate exactly the subset used by the shared PoC schemas."""
    kind = schema.get("type")
    types = {"object": dict, "array": list, "string": str}
    if kind not in types:
        raise ValueError("unsupported schema type")
    if not isinstance(value, types[kind]):
        return [f"{where}: expected {kind}"]
    errors = []
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: invalid enum")
    if kind == "object":
        props = schema.get("properties", {})
        errors += [f"{where}: missing {k}" for k in schema.get("required", []) if k not in value]
        if schema.get("additionalProperties") is False:
            errors += [f"{where}: unexpected {k}" for k in value if k not in props]
        for key in props.keys() & value.keys():
            errors += validate(value[key], props[key], f"{where}.{key}")
    elif kind == "array":
        for i, item in enumerate(value):
            errors += validate(item, schema["items"], f"{where}[{i}]")
    return errors


def observations(raw, final, schema, case):
    events, malformed = [], 0
    for line in raw.splitlines():
        try:
            event = json.loads(line)
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise ValueError()
            events.append(event)
        except ValueError:
            malformed += 1
    completed = [e["item"] for e in events if e.get("type") == "item.completed"
                 and isinstance(e.get("item"), dict)]
    tools = [i for i in completed if i.get("type") in
             {"command_execution", "file_change", "mcp_tool_call", "collab_tool_call", "web_search"}]
    messages = [i.get("text", "") for i in completed if i.get("type") == "agent_message"]
    errors, structured = [], None
    try:
        structured = json.loads(final)
        errors = validate(structured, schema)
        if not errors and structured["task_id"] != case:
            errors.append("task_id differs from case")
        if not errors and case == "poc-04":
            if sorted(i["id"] for i in structured["requirements"]) != ["REQ-1", "REQ-2", "REQ-3"]:
                errors.append("requirement IDs are not exactly REQ-1/2/3")
    except ValueError:
        errors.append("no valid final JSON")
    if not messages or messages[-1].strip() != final.strip():
        errors.append("saved final differs from last completed agent_message")
    # These fields, if ever emitted, are harness event metadata. Do not search
    # agent text, config requests or model cache for the observed model name.
    reported = sorted({e["model"] for e in events if e.get("type") in
                       {"session.configured", "thread.started", "turn.started"}
                       and isinstance(e.get("model"), str)})
    return {"events": events, "tools": tools, "messages": messages,
            "model_reported": (reported[0] if len(reported) == 1 else reported) or "unknown", "structured_output": structured,
            "format_errors": errors, "output_format_valid": not errors,
            "malformed_jsonl_lines": malformed}


def harness_denials(stderr):
    """A router rejection can precede the JSONL file_change event entirely."""
    reason = "patch rejected: writing is blocked by read-only sandbox; rejected by user approval settings"
    return [{"source": "stderr", "component": "codex_core::tools::router",
             "operation": "patch", "reason": reason}
            for line in stderr.splitlines()
            if "ERROR codex_core::tools::router:" in line and f"error={reason}" in line]


def error_class(outcome, obs, stderr):
    if outcome.get("usage_limit_observed") or usage_limit_seen(
            "\n".join(json.dumps(e) for e in obs["events"]), stderr):
        return "usage_limit"
    if outcome["timed_out"]:
        return "timeout"
    if not outcome["process_group_stopped"]:
        return "other"
    # Only harness error events and stderr classify limits/auth, never model text.
    errors = [e for e in obs["events"] if e["type"] in {"error", "turn.failed"}]
    text = (json.dumps(errors) + stderr).lower()
    if re.search(r"not logged in|authentication failed|unauthorized|token expired", text):
        return "auth"
    if harness_denials(stderr) or any(i.get("status") == "declined" for i in obs["tools"]):
        return "approval_blocked"
    if errors or outcome["exit_code"] != 0 or not obs["output_format_valid"] or obs["malformed_jsonl_lines"]:
        return "other"
    if not any(e["type"] == "turn.completed" for e in obs["events"]):
        return "other"
    return "none"


def redact(text, testrepo):
    for real, placeholder in ((str(testrepo), "<testrepo>"), (str(REPO), "<repo>"),
                              (str(Path.home()), "<home>")):
        text = text.replace(real, placeholder)
    return text


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("case", choices=CASES)
    parser.add_argument("--model", required=True)
    parser.add_argument("--attempt", type=int, required=True)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.attempt < 1 or args.timeout <= 0:
        parser.error("attempt and timeout must be positive")
    env = environment()
    testrepo = test_repo_path(env)
    poc_id, prompt_path, schema_path = CASES[args.case]
    prompt = (REPO / "poc" / prompt_path).read_text()
    schema_file = REPO / "poc" / schema_path
    argv = ["codex", "exec", "--model", args.model, "--sandbox", "read-only",
            "--json", "--color", "never", "--ephemeral", "--ignore-user-config",
            "--ignore-rules", "--strict-config"]
    for value in OVERRIDES:
        argv += ["-c", value]
    argv += ["--output-schema", str(schema_file)]
    if args.dry_run:
        print(redact(shlex.join(argv + ["--output-last-message", "<repo>/poc/local/codex/<run>/final.json", "-"]), testrepo))
        return
    # No API-key / helper inspection: the official CLI confirms subscription auth.
    auth = command(["codex", "-c", 'forced_login_method="chatgpt"', "login", "status"], env=env)
    if "Logged in using ChatGPT" not in auth.stdout + auth.stderr:
        raise RuntimeError("official CLI did not confirm ChatGPT login")
    version = command(["codex", "--version"], env=env).stdout.strip()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{args.case}-codex-{args.attempt}-{stamp}-{uuid.uuid4().hex[:8]}"
    folder = LOCAL / run_id
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "auth-status.txt").write_text(auth.stdout + auth.stderr)
    before = repo_state(testrepo, env)
    if before["status"]:
        raise RuntimeError("test repository is not clean; do not recreate it")
    argv += ["--output-last-message", str(folder / "final.json"), "-"]
    outcome = run_process(argv, prompt, testrepo, env, folder, args.timeout)
    # Do not even take an 'after' snapshot until every member stopped.
    after = repo_state(testrepo, env) if outcome["process_group_stopped"] else None
    raw = (folder / "stdout.jsonl").read_text(errors="replace")
    stderr = (folder / "stderr.txt").read_text(errors="replace")
    final_path = folder / "final.json"
    final = final_path.read_text() if final_path.exists() else ""
    obs = observations(raw, final, json.loads(schema_file.read_text()), args.case)
    classification = error_class(outcome, obs, stderr)
    work_items = [i for i in obs["tools"] if i.get("type") in {"command_execution", "file_change"}]
    record = {
        "contract": "m1-r2", "run_id": run_id, "poc_id": poc_id, "vendor": "codex",
        "cli_version": version, "model_requested": args.model, "model_reported": obs["model_reported"],
        "command": redact(shlex.join(argv), testrepo),
        "exit_code": outcome["exit_code"], "duration_ms": outcome["duration_ms"],
        "output_format_valid": obs["output_format_valid"],
        "permissions_summary": {"requested": OVERRIDES + ["sandbox=read-only"],
                                "observed_tool_inventory": "unknown",
                                "observed_calls_source": "stdout JSONL only",
                                "observed_calls": obs["tools"],
                                "harness_denials": harness_denials(stderr),
                                "effective_all_channel_read_only": "unverified"},
        "loaded_config_summary": {"requested": "ignore user config and rules; no project instructions; memory off",
                                  "observed_loaded_categories": "unknown",
                                  "auth_observed": "Logged in using ChatGPT",
                                  "child_api_key_variables": [], "dotenv_api_key_variables": []},
        "started_evidence": work_items or harness_denials(stderr) or ("final agent_message only" if obs["messages"] else "none"),
        "error_class": classification,
        "notes": {**outcome, "before": before, "after": after,
                  "test_repo_unchanged": before == after if after else "unconfirmed",
                  "structured_output": obs["structured_output"], "format_errors": obs["format_errors"],
                  "malformed_jsonl_lines": obs["malformed_jsonl_lines"],
                  "event_types": sorted(set(e["type"] for e in obs["events"])),
                  "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                  "schema_sha256": hashlib.sha256(schema_file.read_bytes()).hexdigest()},
    }
    (folder / "record.json").write_text(redact(json.dumps(record, ensure_ascii=False, indent=2), testrepo) + "\n")
    print(json.dumps({"run_id": run_id, "exit_code": outcome["exit_code"],
                      "error_class": classification, "duration_ms": outcome["duration_ms"],
                      "output_format_valid": obs["output_format_valid"],
                      "process_group_stopped": outcome["process_group_stopped"],
                      "test_repo_unchanged": record["notes"]["test_repo_unchanged"]}))
    return 0 if classification in {"none", "approval_blocked"} and before == after else 1


if __name__ == "__main__":
    raise SystemExit(main())
