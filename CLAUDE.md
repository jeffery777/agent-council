# Agent Council：Claude 補充指示

@AGENTS.md

共同規範在 [AGENTS.md](AGENTS.md) 與 [CONTRIBUTING.md](CONTRIBUTING.md)。
本檔只補充 Claude Code 的載入方式、工具對應與命令，不另訂共同政策。
本檔與共同規範不一致時，以共同規範為準，並向維護者回報不一致之處。

## 載入方式

- 上方的 `@AGENTS.md` 讓 Claude Code 在每個 session 載入共同指示。
- CONTRIBUTING.md 不會自動載入。執行開發、交接或審查任務前，先讀取全文。
- 使用者層級的 Claude 指示與本 repo 的規範同時適用。兩者要求不同時，採用較嚴的一方。
- Claude 的原生記憶與對話摘要不是交接或審查證據。證據以 Issue、PR 與綁定 commit 的紀錄為準。

## 角色與工具對應

| 共同規範中的角色 | Claude 的做法 |
| --- | --- |
| 開發 Orchestrator | 主 session。先用 `dev-skills:dev-deliver` 判斷 rigor，再拆分任務與安排交接。 |
| Writer | 主 session 或 `dev-skills:dev-implementer`。主 session 讀回實際 diff 後才交付。 |
| Claude 這一側的檢查 | `dev-skills:dev-reviewer` 與 `dev-skills:dev-security-reviewer` subagent。 |
| 審查 Codex 撰寫的變更 | 未參與撰寫、以唯讀方式啟動的另一個 Claude session。 |

- Claude 這一側的 subagent 檢查，不算分工表中由 Codex 執行的互審或 Security Diff Scan。兩者都要做，紀錄分開。
- 每次 commit 與 push 前，由 `dev-skills:dev-security-reviewer` 掃描要送出的內容、作者身分與訊息。這是 Claude 這一側的發布前檢查，不取代 Codex 的 Security Diff Scan。
- Claude 無法啟動 Codex session。需要 Codex 審查時，在 Issue／PR 留下交接紀錄，並請維護者啟動 Codex。Codex 回覆前，狀態記為 `delivered`，不記為 `verified`。
- Branch 使用 `claude/<issue>-<topic>`。與 Codex 並行時，使用獨立的 worktree。

## 唯讀審查的證據

- `dev-skills` 的 reviewer subagent 沒有 Edit 與 Write 工具，但保留 Bash。它的唯讀只靠指示約束（來源：dev-skills 0.1.0 的 CB-5）。審查紀錄要寫明這項限制，不可記為技術上唯讀。
- 需要技術上唯讀時，以 CLI 的工具限制啟動獨立 session。Claude Code 2.1.312 提供 `--tools`、`--disallowedTools` 與 `--permission-mode`（來源：`claude --help`）。
- 哪一組旗標能確實唯讀，尚未驗證；M1 的 PoC-15 會提供實測結果。驗證前，每次審查記錄實際使用的旗標與該 session 的可用工具清單。
- 審查前後各執行一次下方的狀態命令，並比對結果。

## 命令

目前 repo 只有文件，沒有 build、test 或 CI 指令。

```bash
# 文件變更的格式檢查
git diff --check

# 交接或審查前後的狀態
git rev-parse HEAD
git status --porcelain=v1 --untracked-files=all
```

- `gh` 的寫入命令一律加上 `--repo jeffery777/agent-council`。
- Headless 執行（`claude -p`）使用官方訂閱登入。不設定 `ANTHROPIC_API_KEY`，不使用 `--bare`（規格 PoC-04）。
