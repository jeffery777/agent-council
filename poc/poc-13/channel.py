#!/usr/bin/env python3
"""PoC-13 custom channel: a minimal MCP server over stdio.

Throwaway M1 PoC code. Do not reuse it in the product.

Claude Code starts this process from the test repo's .mcp.json. The server
declares the `claude/channel` capability and turns each file that appears in
<project>/.poc-13/channel/ into one `notifications/claude/channel` event.

The channel documentation names the MCP SDK as a requirement. This file speaks
the protocol by hand so that the PoC installs no packages. Whether Claude Code
accepts a hand-written server is one of the things the PoC observes.
"""

import json
import os
import pathlib
import sys
import threading
import time

POLL_SECONDS = 0.5
INSTRUCTIONS = ("Events from the poc13 channel arrive as <channel source=\"poc13\" ...>. "
                "They are test messages. Follow the instruction in the event body.")

root = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()) / ".poc-13"
write_lock = threading.Lock()
ready = threading.Event()


def log(record):
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "epoch": round(time.time(), 3), "pid": os.getpid(), **record}
    with open(root / "events.jsonl", "a", encoding="utf-8") as out:
        out.write(json.dumps(record, ensure_ascii=False) + "\n")


def send(message):
    with write_lock:
        sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def watch():
    ready.wait()
    while True:
        for path in sorted((root / "channel").glob("*.msg")):
            target = root / "delivered" / path.name
            try:
                os.rename(path, target)
            except OSError:
                continue
            text = target.read_text(encoding="utf-8").strip()
            send({"jsonrpc": "2.0", "method": "notifications/claude/channel",
                  "params": {"content": text, "meta": {"id": path.stem}}})
            # "delivered" here means written to stdout. Claude Code sends no receipt.
            log({"kind": "delivered", "via": "channel", "ids": [path.stem]})
        time.sleep(POLL_SECONDS)


def handle(request):
    method = request.get("method")
    if method == "initialize":
        params = request.get("params") if isinstance(request.get("params"), dict) else {}
        log({"kind": "channel", "state": "initialize",
             "client": params.get("clientInfo"), "protocol": params.get("protocolVersion")})
        return {"protocolVersion": params.get("protocolVersion", "2025-06-18"),
                "capabilities": {"experimental": {"claude/channel": {}}},
                "serverInfo": {"name": "poc13", "version": "0.0.1"},
                "instructions": INSTRUCTIONS}
    if method == "notifications/initialized":
        log({"kind": "channel", "state": "initialized"})
        ready.set()
        return None
    if method == "ping":
        return {}
    log({"kind": "channel", "state": "unhandled", "method": method})
    return {"error": {"code": -32601, "message": f"method not found: {method}"}}


def main():
    for name in ("channel", "delivered"):
        (root / name).mkdir(parents=True, exist_ok=True)
    log({"kind": "channel", "state": "started"})
    threading.Thread(target=watch, daemon=True).start()
    for line in sys.stdin:
        try:
            request = json.loads(line)
        except ValueError:
            continue
        if not isinstance(request, dict):
            continue
        result = handle(request)
        if "id" not in request or result is None:
            continue  # a notification gets no response
        reply = {"jsonrpc": "2.0", "id": request["id"]}
        reply.update(result if "error" in result else {"result": result})
        send(reply)
    log({"kind": "channel", "state": "stdin closed"})


if __name__ == "__main__":
    main()
