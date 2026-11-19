#!/usr/bin/env python3
"""Drop one PoC-13 test message into the local test repository.

Throwaway M1 PoC code. Writes only inside <testrepo>/.poc-13/.

Usage:
  poc-13-send.py inbox  <id>   message for the "hooks inject the inbox" profile
  poc-13-send.py rewake <id>   message for the asyncRewake profile
  poc-13-send.py channel <id>  message for the custom channel profile

<id> is a short label such as A1. The session is asked to answer `ACK <id>`.
"""

import json
import os
import pathlib
import re
import subprocess
import sys
import time


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("inbox", "rewake", "channel") \
            or not re.fullmatch(r"[A-Za-z0-9]{1,12}", sys.argv[2]):
        sys.exit(__doc__)
    box, ident = sys.argv[1], sys.argv[2]
    here = pathlib.Path(__file__).resolve().parent
    target = pathlib.Path(subprocess.run(
        [str(here / "create-test-repo.sh"), "--print-path"],
        capture_output=True, text=True, check=True, timeout=30).stdout.strip())
    root = target / ".poc-13"
    wanted = {"inbox": "inject", "rewake": "rewake", "channel": "channel"}[box]
    try:
        installed = (root / "profile").read_text().strip()
    except OSError:
        installed = "none"
    if installed != wanted:
        sys.exit(f"box {box} needs profile {wanted}; installed profile: {installed}")
    if list(root.glob(f"*/{ident}.msg")):
        sys.exit(f"message id already used: {ident}")
    text = (f"This is PoC-13 test message {ident}, delivered from outside the session. "
            f"Do not use any tool. Reply with exactly one line: ACK {ident}")
    temporary = root / f".{ident}.tmp"
    temporary.write_text(text + "\n", encoding="utf-8")
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "epoch": round(time.time(), 3), "kind": "sent", "box": box, "id": ident}
    with open(root / "events.jsonl", "a", encoding="utf-8") as out:
        out.write(json.dumps(record) + "\n")
    os.rename(temporary, root / box / f"{ident}.msg")  # appears in one step
    print(f"sent {ident} to {box}")


if __name__ == "__main__":
    main()
