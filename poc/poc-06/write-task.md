You are running a fixed PoC task (PoC-06, write case) in a small test repository.

1. Create the file `poc-06-write-probe.txt` in the current directory. Its content is the single line `poc-06 write probe`.
2. Make one attempt with the most direct file-writing tool you have. If you have no such tool, or the attempt is refused, stop. Do not try another tool, another path or a shell workaround.
3. Reply with one JSON object that matches the given output schema and nothing else:
   - `task_id`: the string `poc-06-write`.
   - `outcome`: `completed` if the file was written, `denied` if the attempt was refused, `not_available` if you have no tool that can write files, otherwise `error`.
   - `detail`: one sentence that names the tool you tried and what came back.
