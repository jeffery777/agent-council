You are running a fixed PoC task (PoC-04) in a small test repository. Work only inside the current directory and do not modify anything.

1. Read `docs/requirements.md` and `src/wordcount.py`.
2. For each of REQ-1, REQ-2 and REQ-3, decide whether `src/wordcount.py` implements it.
3. Reply with one JSON object that matches the given output schema and nothing else:
   - `task_id`: the string `poc-04`.
   - `requirements`: exactly three entries, one per requirement ID, each with `id`, `status` (`implemented`, `not_implemented` or `unclear`) and a one-sentence `evidence` that names the function you looked at.
   - `files_read`: the repository-relative paths of the files you actually read.
   - `summary`: one sentence.
