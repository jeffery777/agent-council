#!/usr/bin/env python3
"""PoC-13 hook for a Claude Code session in the local test repository.

Throwaway M1 PoC code. Do not reuse it in the product.

Usage (from the hook configuration):
  hook.py log      record the hook event only
  hook.py inject   record the event, and hand waiting messages to the session
  hook.py wait     asyncRewake watcher: wait for one message, then exit 2

State lives in <project>/.poc-13/:
  inbox/      messages for `inject`
  rewake/     messages for `wait`
  channel/    messages for the custom channel (channel.py)
  delivered/  messages a hook or the channel has handed to the session
  events.jsonl  one JSON line per hook event and per delivery

events.jsonl holds session IDs and parts of the conversation. It stays on this
machine.
"""

import json
import os
import pathlib
import sys
import time

WAIT_SECONDS = 840      # must stay below the hook `timeout` in the settings
POLL_SECONDS = 0.5
TEXT_LIMIT = 300
KEPT_FIELDS = ("session_id", "source", "notification_type",
               "tool_name", "stop_hook_active", "reason")
TEXT_FIELDS = ("prompt", "last_assistant_message")
CONTEXT_EVENTS = ("SessionStart", "UserPromptSubmit", "PostToolUse")


def state_dir():
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project:
        sys.exit(0)  # not started by Claude Code: do nothing
    root = pathlib.Path(project) / ".poc-13"
    for name in ("inbox", "rewake", "channel", "delivered"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def log(root, record):
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "epoch": round(time.time(), 3), **record}
    with open(root / "events.jsonl", "a", encoding="utf-8") as out:
        out.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_event():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    return event if isinstance(event, dict) else {}


def summary(event, mode):
    record = {"kind": "hook", "mode": mode, "pid": os.getpid(),
              "event": event.get("hook_event_name")}
    for key in KEPT_FIELDS:
        if key in event:
            record[key] = event[key]
    for key in TEXT_FIELDS:
        if isinstance(event.get(key), str):
            record[key] = event[key][:TEXT_LIMIT]
    return record


def claim(root, box):
    """Move every waiting message to delivered/ and return [(id, text)]."""
    claimed = []
    for path in sorted((root / box).glob("*.msg")):
        target = root / "delivered" / path.name
        try:
            os.rename(path, target)  # only one hook process wins a message
        except OSError:
            continue
        claimed.append((path.stem, target.read_text(encoding="utf-8").strip()))
    return claimed


def render(messages):
    return "\n".join(f"[poc-13 message {ident}] {text}" for ident, text in messages)


def inject(root, event):
    name = event.get("hook_event_name")
    if name not in CONTEXT_EVENTS and name != "Stop":
        return
    messages = claim(root, "inbox")
    if not messages:
        return
    text = render(messages)
    if name == "Stop":
        reply = {"decision": "block", "reason": text}
    else:
        reply = {"hookSpecificOutput": {"hookEventName": name, "additionalContext": text}}
    log(root, {"kind": "delivered", "via": f"inject:{name}",
               "ids": [ident for ident, _ in messages],
               "session_id": event.get("session_id")})
    print(json.dumps(reply, ensure_ascii=False))


def wait(root, event):
    lock = root / "watcher.pid"
    try:
        other = int(lock.read_text())
        os.kill(other, 0)
        log(root, {"kind": "watcher", "state": "skipped", "pid": os.getpid(), "running": other})
        return 0  # one watcher per project is enough
    except (OSError, ValueError):
        pass
    lock.write_text(str(os.getpid()))
    parent = os.getppid()
    log(root, {"kind": "watcher", "state": "started", "pid": os.getpid(),
               "event": event.get("hook_event_name")})
    deadline = time.monotonic() + WAIT_SECONDS
    try:
        while time.monotonic() < deadline:
            if os.getppid() != parent:
                # The session that started this watcher is gone: take no message.
                log(root, {"kind": "watcher", "state": "orphaned", "pid": os.getpid()})
                return 0
            messages = claim(root, "rewake")
            if messages:
                log(root, {"kind": "delivered", "via": "asyncRewake",
                           "ids": [ident for ident, _ in messages],
                           "session_id": event.get("session_id")})
                print(render(messages), file=sys.stderr)
                return 2
            time.sleep(POLL_SECONDS)
        log(root, {"kind": "watcher", "state": "expired", "pid": os.getpid()})
        return 0
    finally:
        try:
            if lock.read_text() == str(os.getpid()):
                lock.unlink()
        except OSError:
            pass


def main():
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if mode not in ("log", "inject", "wait"):
        sys.exit("usage: hook.py log|inject|wait")
    root = state_dir()
    event = read_event()
    if mode == "wait":
        sys.exit(wait(root, event))
    log(root, summary(event, mode))
    if mode == "inject":
        inject(root, event)


if __name__ == "__main__":
    main()
