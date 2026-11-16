#!/usr/bin/env python3
"""Run one `claude -p` case of the M1 PoC and write one m1-r2 result record.

Throwaway PoC code (M1 plan, rule 2). Standard library only.

The script:
  - refuses to run when an API key variable is present (plan rule 4), or when
    the CLI does not report the subscription login;
  - starts the CLI with a small, explicit environment, so that variables
    inherited from a parent agent session do not reach it;
  - enforces a timeout, and after every run (timeout or normal exit) stops
    what is left of the process group;
  - compares the test repository before and after the run;
  - writes the raw output and the record under poc/local/ (not in Git).

Requested values and observed values are kept apart. A value that was not
observed is recorded as "unknown"; it is never copied from the request.
"""

import argparse
import datetime
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
POC = os.path.join(REPO, "poc")
LOCAL = os.path.join(POC, "local")

# Flags shared by every case. stream-json with --verbose gives the init event
# (observed tools, model, permission mode) and the result event.
BASE_FLAGS = ["--output-format", "stream-json", "--verbose", "--no-session-persistence"]

# The controlled read-only configuration under test (PoC-04, PoC-06).
READ_ONLY = [
    "--tools", "Read,Grep,Glob",
    "--strict-mcp-config",
    "--permission-mode", "dontAsk",
    "--safe-mode",
]

# Memory probe (PoC-04 step 4). Before these cases, the operator puts a CLAUDE.md
# with a canary token in the test repository. The reply shows whether the
# project instruction file reached the model. The hook events are recorded as
# a second observation when the CLI emits them.
MEMORY_PROBE = ("Reply with the project canary token from your instructions. If your "
                "instructions contain no canary token, reply NONE. Reply with the token or NONE only.")
MEMORY_FLAGS = ["--tools", "", "--strict-mcp-config", "--permission-mode", "dontAsk",
                "--include-hook-events"]

CASES = {
    # PoC-04: fixed input, fixed output schema, read-only tools.
    "poc-04": {
        "poc_id": "PoC-04",
        "prompt": "poc-04/prompt.md",
        "schema": "poc-04/output.schema.json",
        "flags": READ_ONLY,
    },
    # PoC-04 step 4: is memory loaded by default, and can it be turned off?
    "memory-default": {
        "poc_id": "PoC-04",
        "prompt_text": MEMORY_PROBE,
        "flags": MEMORY_FLAGS,
    },
    "memory-off-safe-mode": {
        "poc_id": "PoC-04",
        "prompt_text": MEMORY_PROBE,
        "flags": MEMORY_FLAGS + ["--safe-mode"],
    },
    "memory-off-env": {
        "poc_id": "PoC-04",
        "prompt_text": MEMORY_PROBE,
        "flags": MEMORY_FLAGS,
        "env": {"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"},
    },
    # PoC-06: read task with the read-only configuration.
    "poc-06-read": {
        "poc_id": "PoC-06",
        "prompt": "poc-06/read-task.md",
        "schema": "poc-06/output.schema.json",
        "flags": READ_ONLY,
    },
    # PoC-06: write attempt with the read-only configuration (no write tool).
    "poc-06-write-ro": {
        "poc_id": "PoC-06",
        "prompt": "poc-06/write-task.md",
        "schema": "poc-06/output.schema.json",
        "flags": READ_ONLY,
    },
    # PoC-06: write attempt with a write tool present and nobody to approve.
    # No permission flag is passed: this is the default behavior of -p.
    "poc-06-write-noapprover": {
        "poc_id": "PoC-06",
        "prompt": "poc-06/write-task.md",
        "schema": "poc-06/output.schema.json",
        "flags": ["--tools", "Read,Write", "--strict-mcp-config", "--safe-mode"],
    },
    # PoC-15: read-only review of the change that prepare-poc-15-change.sh
    # committed to the test repository.
    "poc-15": {
        "poc_id": "PoC-15",
        "prompt": "poc-15/review-task.md",
        "schema": "poc-15/output.schema.json",
        "flags": READ_ONLY,
        "review": {"base": "main", "branch": "poc-15-change"},
        "known_issues": "poc-15/known-issues.json",
    },
}

BLOCKED_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
PASSED_ENV = ("HOME", "PATH", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR", "SHELL")


def sh(args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)


def test_repo_path():
    out = sh([os.path.join(POC, "scripts", "create-test-repo.sh"), "--print-path"])
    path = out.stdout.strip()
    if out.returncode != 0 or not os.path.isfile(os.path.join(path, ".poc-testrepo-marker")):
        sys.exit("test repository not found; create it first (see poc/README.md)")
    return path


AUTH_STATUS_TIMEOUT = 30  # seconds


def subscription_login(env):
    """Ask the CLI how it is logged in. Stops unless it is the subscription login.

    Only the two fields that name the login method are read and kept.
    """
    try:
        out = subprocess.run(["claude", "auth", "status", "--json"], env=env, capture_output=True,
                             text=True, check=False, timeout=AUTH_STATUS_TIMEOUT)
    except (subprocess.TimeoutExpired, OSError):
        sys.exit("`claude auth status --json` did not answer; not starting the CLI")
    try:
        status = json.loads(out.stdout)
        seen = {"authMethod": str(status.get("authMethod")),
                "apiProvider": str(status.get("apiProvider"))}
    except (ValueError, AttributeError):
        sys.exit("could not read `claude auth status --json`; not starting the CLI")
    if seen != {"authMethod": "claude.ai", "apiProvider": "firstParty"}:
        sys.exit(f"the CLI does not report the subscription login ({seen}); not starting it")
    return seen


def review_target(test_repo, review):
    """Base and head of the change under review, and its diff. Stops when the
    test repository is not on the prepared branch."""
    def rev(name):
        out = sh(["git", "rev-parse", "--verify", "--quiet", name], cwd=test_repo)
        return out.stdout.strip()
    base, head = rev(review["base"]), rev("refs/heads/" + review["branch"])
    if not base or not head or rev("HEAD") != head:
        sys.exit("the test repository is not on the prepared review branch; "
                 "run poc/scripts/prepare-poc-15-change.sh first")
    diff = sh(["git", "diff", "--no-ext-diff", "--no-textconv", "--no-color", base, head],
              cwd=test_repo).stdout
    if not diff.strip():
        sys.exit("the diff under review is empty")
    return {"base": base, "head": head, "diff": diff}


def fill_review_prompt(template, target):
    for key in ("base", "head", "diff"):
        template = template.replace("{{" + key.upper() + "}}", target[key])
    return template


def known_issues_found(structured, known):
    """Heuristic first match of the planted problems against the findings.

    A problem counts as found when a finding names its symbol. The scope
    problem also needs a finding that marks the symbol as outside the
    requirements. The report states the final judgment.
    """
    found = {}
    # The output may not follow the schema; the record must still be written.
    findings = structured.get("findings") if isinstance(structured, dict) else None
    findings = [f for f in findings if isinstance(f, dict)] if isinstance(findings, list) else []
    for issue in known["issues"]:
        hits = [f for f in findings if issue["symbol"] in json.dumps(f, ensure_ascii=False)]
        if issue.get("needs_scope_relation") == "yes":
            hits = [f for f in hits if f.get("requirement_relation") == "no-requirement"
                    or f.get("severity") == "SCOPE-CREEP"]
        found[issue["key"]] = sorted(str(f.get("id")) for f in hits)
    return found


def repo_state(path):
    """HEAD, porcelain status and a hash over every file outside .git."""
    head = sh(["git", "rev-parse", "HEAD"], cwd=path).stdout.strip()
    status = sh(["git", "--no-optional-locks", "status", "--porcelain=v1",
                 "--untracked-files=all", "--ignored"], cwd=path).stdout
    digest = hashlib.sha256()
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(files):
            full = os.path.join(root, name)
            digest.update(os.path.relpath(full, path).encode())
            with open(full, "rb") as fh:
                digest.update(hashlib.sha256(fh.read()).digest())
    return {"head": head, "status": status, "tree_sha256": digest.hexdigest()}


def validate(value, schema, where="$"):
    """Check the JSON Schema subset the PoC schemas use. Returns a list of errors."""
    errors = []
    kind = schema.get("type")
    types = {"object": dict, "array": list, "string": str}
    if kind and not isinstance(value, types[kind]):
        return [f"{where}: expected {kind}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: {value!r} not in enum")
    if kind == "object":
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{where}: missing {key}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append(f"{where}: unexpected {key}")
        for key, sub in props.items():
            if key in value:
                errors.extend(validate(value[key], sub, f"{where}.{key}"))
    if kind == "array" and "items" in schema:
        for index, item in enumerate(value):
            errors.extend(validate(item, schema["items"], f"{where}[{index}]"))
    return errors


def stop_group(proc, grace=5.0):
    """Stop every member of the process group of proc. True when the group is gone.

    The leader may exit before its children do, so the group is checked, not
    only the leader: SIGTERM first, SIGKILL after the grace period.
    """
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            proc.wait()
            return True
        except PermissionError:
            pass  # macOS reports this while only exited members remain
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            proc.poll()  # reap the leader, otherwise the group never empties
            try:
                os.killpg(proc.pid, 0)
            except ProcessLookupError:
                proc.wait()
                return True
            except PermissionError:
                pass
            time.sleep(0.05)
    return False


def redact(text, test_repo):
    for real, label in ((test_repo, "<testrepo>"), (REPO, "<repo>"),
                        (os.path.expanduser("~"), "<home>")):
        text = text.replace(real, label)
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("case", choices=sorted(CASES))
    parser.add_argument("--model", required=True, help="model name passed to --model")
    parser.add_argument("--attempt", type=int, default=1, help="attempt number, for the run id")
    parser.add_argument("--timeout", type=int, default=180, help="seconds before the run is stopped")
    parser.add_argument("--dry-run", action="store_true", help="print the command and exit")
    args = parser.parse_args()

    for name in BLOCKED_ENV:
        if os.environ.get(name):
            sys.exit(f"{name} is set; the PoC must use the subscription login (plan rule 4)")

    case = CASES[args.case]
    test_repo = test_repo_path()
    if "prompt" in case:
        with open(os.path.join(POC, case["prompt"]), encoding="utf-8") as fh:
            prompt = fh.read()
    else:
        prompt = case["prompt_text"]
    target = None
    if "review" in case:
        target = review_target(test_repo, case["review"])
        prompt = fill_review_prompt(prompt, target)
    schema = None
    command = ["claude", "-p", "--model", args.model] + BASE_FLAGS + list(case["flags"])
    if "schema" in case:
        with open(os.path.join(POC, case["schema"]), encoding="utf-8") as fh:
            schema = json.load(fh)
        command += ["--json-schema", json.dumps(schema, separators=(",", ":"))]

    shown = ["claude", "-p", "--model", args.model] + BASE_FLAGS + list(case["flags"])
    if schema is not None:
        shown += ["--json-schema", f"<poc/{case['schema']}>"]
    shown_text = " ".join(a if a and " " not in a else repr(a) for a in shown)
    if case.get("env"):
        shown_text = " ".join(f"{k}={v}" for k, v in case["env"].items()) + " " + shown_text
    shown_text += f"  # prompt on stdin: {case.get('prompt', 'inline probe text')}; cwd: <testrepo>"
    if args.dry_run:
        print(shown_text)
        return

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{args.case}-claude-{args.attempt}-{stamp}"
    os.makedirs(os.path.join(LOCAL, "raw"), exist_ok=True)
    os.makedirs(os.path.join(LOCAL, "runs"), exist_ok=True)
    raw_out = os.path.join(LOCAL, "raw", run_id + ".stdout.jsonl")
    raw_err = os.path.join(LOCAL, "raw", run_id + ".stderr.txt")

    env = {k: os.environ[k] for k in PASSED_ENV if k in os.environ}
    env.update(case.get("env", {}))
    login = subscription_login(env)
    version = sh(["claude", "--version"]).stdout.strip() or "unknown"
    before = repo_state(test_repo)

    timed_out = False
    started = time.monotonic()
    with open(raw_out, "wb") as out, open(raw_err, "wb") as err:
        proc = subprocess.Popen(command, cwd=test_repo, env=env, stdin=subprocess.PIPE,
                                stdout=out, stderr=err, start_new_session=True)
        try:
            proc.communicate(prompt.encode(), timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        duration_ms = int((time.monotonic() - started) * 1000)  # without the cleanup
        # Stop whatever is left of the process group, also after a normal exit,
        # so that the "after" snapshot is taken when nothing can still write.
        group_stopped = stop_group(proc)
    after = repo_state(test_repo)

    init, result, events = None, None, []
    assistant_models, tool_uses, hook_events, rate_limits = set(), [], [], []
    with open(raw_out, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            events.append(event.get("type"))
            if event.get("type") == "system" and event.get("subtype") == "init":
                init = event
            elif event.get("type") == "system" and "hook" in str(event.get("subtype", "")):
                hook_events.append({k: str(event.get(k))
                                    for k in ("subtype", "hook_event", "hook_name", "memory_type",
                                              "load_reason", "file_path")
                                    if event.get(k) is not None})
            elif event.get("type") == "assistant":
                message = event.get("message", {})
                if message.get("model"):
                    assistant_models.add(message["model"])
                for block in message.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_uses.append(block.get("name"))
            elif event.get("type") == "rate_limit_event":
                info = event.get("rate_limit_info", {})
                rate_limits.append({k: info.get(k) for k in ("status", "rateLimitType")})
            elif event.get("type") == "result":
                result = event

    observed_model = "unknown"
    if init and init.get("model"):
        observed_model = init["model"]
    usage_models = sorted((result or {}).get("modelUsage", {}).keys())

    structured = (result or {}).get("structured_output")
    if schema is None:
        format_valid, format_errors = "not_applicable", []
    elif structured is None:
        format_valid, format_errors = False, ["no structured_output in the result event"]
    else:
        format_errors = validate(structured, schema)
        if args.case == "poc-04" and not format_errors:
            ids = sorted(item["id"] for item in structured["requirements"])
            if ids != ["REQ-1", "REQ-2", "REQ-3"]:
                format_errors.append(f"requirements ids are {ids}")
        if target and not format_errors:
            if (structured["reviewed_base"], structured["reviewed_head"]) != (target["base"], target["head"]):
                format_errors.append("reviewed_base / reviewed_head differ from the commits given")
            ids = [item["id"] for item in structured["findings"]]
            if len(ids) != len(set(ids)):
                format_errors.append("finding ids are not unique")
        format_valid = not format_errors

    known_found = "not_applicable"
    if "known_issues" in case:
        with open(os.path.join(POC, case["known_issues"]), encoding="utf-8") as fh:
            known_found = known_issues_found(structured, json.load(fh))

    denials = (result or {}).get("permission_denials") or []
    if timed_out:
        error_class = "timeout"
    elif not group_stopped:
        error_class = "other"  # the run cannot be trusted: something may still be running
    elif result is None:
        error_class = "other"
    elif result.get("is_error"):
        error_class = "other"
    else:
        error_class = "none"

    init_keys = sorted(init.keys()) if init else []
    record = {
        "contract": "m1-r2",
        "run_id": run_id,
        "poc_id": case["poc_id"],
        "case": args.case,
        "vendor": "claude",
        "cli_version": version,
        "model_requested": args.model,
        "model_reported": observed_model,
        "command": shown_text,
        "exit_code": proc.returncode,
        "duration_ms": duration_ms,
        "output_format_valid": format_valid,
        "permissions_summary": {
            "requested": " ".join(a or "''" for a in case["flags"]),
            "observed_tools": (init or {}).get("tools", "unknown"),
            "observed_permission_mode": (init or {}).get("permissionMode", "unknown"),
            "observed_mcp_servers": [s.get("name") for s in (init or {}).get("mcp_servers", [])]
            if init else "unknown",
            "tool_uses": tool_uses,
            "permission_denials": [{"tool_name": d.get("tool_name")} for d in denials],
        },
        "loaded_config_summary": {
            "auth_status_before_run": login,
            "api_key_source": (init or {}).get("apiKeySource", "unknown"),
            "plugins": [p.get("source") for p in (init or {}).get("plugins", [])]
            if init else "unknown",
            "slash_commands": len((init or {}).get("slash_commands", [])) if init else "unknown",
            "skills": len((init or {}).get("skills", [])) if init else "unknown",
            "agents": len((init or {}).get("agents", [])) if init else "unknown",
            "memory_paths_present": ("memory_paths" in init) if init else "unknown",
            "init_event_keys": init_keys,
            "hook_events": hook_events,
        },
        "started_evidence": (
            f"assistant events: {events.count('assistant')}; tool uses: {tool_uses}; "
            f"result turns: {(result or {}).get('num_turns', 'unknown')}"
            if events.count("assistant") else "none"),
        "error_class": error_class,
        "notes": {
            "timed_out": timed_out,
            "process_group_stopped": group_stopped,
            "result_subtype": (result or {}).get("subtype", "unknown"),
            "result_is_error": (result or {}).get("is_error", "unknown"),
            "rate_limit_events": rate_limits,
            "models_in_assistant_events": sorted(assistant_models),
            "models_in_result_usage": usage_models,
            "format_errors": format_errors,
            "structured_output": structured,
            "result_text": str((result or {}).get("result", "")),
            "reviewed": {"base": target["base"], "head": target["head"],
                         "diff_sha256": hashlib.sha256(target["diff"].encode()).hexdigest()}
            if target else "not_applicable",
            "known_issues_found_heuristic": known_found,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "test_repo_head_before": before["head"],
            # Without a confirmed stop, the comparison proves nothing about later writes.
            "test_repo_unchanged": (before == after) if group_stopped else "unconfirmed",
            "test_repo_status_after": after["status"],
            "event_types": {t: events.count(t) for t in sorted(set(filter(None, events)))},
        },
    }
    # Redact once, over the whole serialized record, before it is written or printed.
    text = redact(json.dumps(record, ensure_ascii=False, indent=2), test_repo)
    with open(os.path.join(LOCAL, "runs", run_id + ".json"), "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(text)
    if not group_stopped:
        sys.exit("the process group could not be confirmed stopped; do not rely on this run")


if __name__ == "__main__":
    main()
