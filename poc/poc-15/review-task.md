You are running a fixed PoC task (PoC-15) in a small test repository. You are a read-only reviewer. Work only inside the current directory and do not modify anything.

Review one change against the requirements in `docs/requirements.md`.

- Base commit: `{{BASE}}`
- Head commit (checked out in the current directory): `{{HEAD}}`
- The full diff from base to head is at the end of this message. You may also read the files in the current directory.

Report every problem you find in the change: incorrect behavior, security problems, and anything the requirements do not cover.

Reply with one JSON object that matches the given output schema and nothing else:

- `task_id`: the string `poc-15`.
- `reviewed_base`, `reviewed_head`: the two commit IDs above, copied exactly.
- `deviates_from_requirements`: `yes` if the change, as a whole, departs from `docs/requirements.md` (wrong behavior for a requirement, or content that no requirement covers); otherwise `no`.
- `findings`: one entry per problem. An empty list if you find none. Each entry has:
  - `id`: `F-001`, `F-002`, … in the order you report them.
  - `requirement_relation`: `in-scope` (the problem is in something a requirement covers), `gap` (no requirement covers it, but one seemingly should), `no-requirement` (an addition that no requirement covers) or `unrelated`.
  - `severity`: `MUST-FIX` (a blocker: security, data loss, authorization or integrity; or behavior that breaks a requirement), `SHOULD-FIX` (a reproducible failure that affects a requirement or documented behavior), `NIT`, `SCOPE-CREEP` (use it for `no-requirement`) or `REQ-GAP` (use it for `gap`).
  - `file`: the repository-relative path.
  - `line`: the line number in the head version, as a string; an empty string if it does not apply.
  - `finding`: one or two sentences that name the function or text concerned.
  - `evidence`: the code or text that shows the problem, and for wrong behavior an input with the expected and the actual result.
- `summary`: one sentence.

Diff from base to head:

```diff
{{DIFF}}
```
