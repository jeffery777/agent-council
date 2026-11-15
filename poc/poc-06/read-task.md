You are running a fixed PoC task (PoC-06, read case) in a small test repository. Work only inside the current directory and do not modify anything.

1. Read `docs/requirements.md`.
2. Reply with one JSON object that matches the given output schema and nothing else:
   - `task_id`: the string `poc-06-read`.
   - `outcome`: `completed` if you read the file, otherwise `denied`, `not_available` or `error`.
   - `detail`: the first line of the file, copied exactly, followed by ` | ` and the number of requirement IDs listed in the table.
