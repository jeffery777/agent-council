# Agent Council：Claude 補充指示

@AGENTS.md

共同規範在 [AGENTS.md](AGENTS.md) 與 [CONTRIBUTING.md](CONTRIBUTING.md)。
本檔只補充 Claude Code 的載入方式、工具對應與命令，不另訂共同政策。
本檔與共同規範不一致時，以共同規範為準，並向維護者回報不一致之處。

## 載入方式

- 上方的 `@AGENTS.md` 讓 Claude Code 在每個 session 載入共同指示。
- CONTRIBUTING.md 不會自動載入。執行開發、交接或審查任務前，先讀取全文。
- 使用者層級的 Claude 指示也會載入。它與本 repo 的規範衝突、且無法判定優先序時，回報維護者。
- Claude 的原生記憶與對話摘要不是交接或審查證據。證據以 Issue、PR 與綁定 commit 的紀錄為準。

## 角色與工具對應

| 共同規範中的角色 | Claude 的做法 |
| --- | --- |
| 開發 Orchestrator | 主 session。先用 `dev-skills:dev-deliver` 判斷 rigor，再拆分任務與安排交接。 |
| Writer | 主 session 或 `dev-skills:dev-implementer`。主 session 讀回實際 diff 後才交付。 |
| Claude 這一側的檢查 | `dev-skills:dev-reviewer` 與 `dev-skills:dev-security-reviewer` subagent。 |
| 審查 Codex 撰寫的變更 | 未參與撰寫的 Claude session。它可以派出 reviewer subagent，再讀回並彙整結果。 |

- Claude 是 Writer 時，subagent 的檢查是 Claude 這一側的自查，不算 CONTRIBUTING.md 第 1 節分工表的 Review 或 Security Diff Scan。
- Claude 是 Reviewer 時，reviewer subagent 的結果是否可作為分工表的 Review，依下一節的唯讀資格與例外判定。
- 分工表各項檢查的時機與適用性依 CONTRIBUTING.md 第 6 節判定。
- commit、push 與發布 Issue／PR／review 文字前的發布檢查（CONTRIBUTING.md 第 6 節）由 `dev-skills:dev-security-reviewer` 執行。這條路徑屬於第 6 節第 3 點的例外，依據與範圍見下一節。
- Claude 無法啟動 Codex session。需要 Codex 審查時，在 Issue／PR 留下交接紀錄，並請維護者啟動 Codex。Codex 回覆前，狀態記為 `delivered`，不記為 `verified`。
- Branch 使用 `claude/<issue>-<topic>`。與 Codex 並行時，使用獨立的 worktree。

## Reviewer 的唯讀資格與例外

- `dev-skills` 的 reviewer subagent 沒有 Edit 與 Write 工具，但保留 Bash（來源：dev-skills 0.1.0 的 CB-5）。它在回覆中交付報告，由主 session 讀回後保存或發布。
- 仍可寫入的通道：Bash。Bash 與它的子程序對受審工作目錄的寫入、網路、憑證與外部服務是否受到限制，尚未實測。它的唯讀目前只靠指示約束，不可記為技術上唯讀。
- 保留 Bash 的理由：發布檢查需要 Git 查詢，以取得 staged diff、待推送的 commits 與作者身分。
- 替代偵測：主 session 在檢查前後各執行一次下方的狀態命令，並比對結果。
- 盲區：已存在的 untracked 檔案內的修改、被忽略的檔案、`.git` 內部的變動（例如設定、hooks 與其他 refs）、先修改再還原的暫時性寫入，以及 repo 以外的影響。
- 例外依據：維護者的確認記錄在 PR #9 的兩則留言：[發布檢查與 merge 前審查](https://github.com/jeffery777/agent-council/pull/9#issuecomment-6877210284)、[公開文字的發布檢查](https://github.com/jeffery777/agent-council/pull/9#issuecomment-6877737742)。每次紀錄引用這項依據，並標明上述限制。
- 例外範圍有兩項：Claude 的發布檢查（commit、push，以及公開的 Issue／PR／review 文字）；以及 PR #9 中，對 Codex 撰寫的共同規範的 merge 前審查。
- 其他 PR 的 merge 前審查不在範圍內。Claude 擔任 Reviewer 時，使用技術上唯讀的 session，或另外取得維護者的授權並記錄在 Issue／PR；兩者都沒有時記為受阻。
- 工具、沙箱設定或授權範圍改變時，重新評估這項例外。
- PR 改到 agent 指示檔時，主 session 在 PR checkout 之外啟動（AGENTS.md「審查、權限與文件」）。reviewer subagent 曾載入主 session 工作目錄中的指示檔；以獨立 worktree 啟動的 subagent 也一樣（在 PR #9 的審查中觀察到）。所以主 session 的工作目錄不可含受審的指示檔；受審檔以 `git -C` 或 `git show` 讀取。
- 需要技術上唯讀時，以 CLI 的工具限制啟動獨立 session。Claude Code 2.1.312 提供 `--tools`、`--disallowedTools` 與 `--permission-mode`（來源：`claude --help`）。
- 哪一組旗標能確實唯讀，尚未驗證；M1 的 PoC-15 會提供實測結果。驗證前，每次審查記錄實際使用的旗標，以及與寫入能力有關的工具類別。

## 命令

目前 repo 只有文件，沒有 build、test 或 CI 指令。

```bash
# 文件變更的格式檢查
git diff --check

# 交接或審查前後的狀態
git rev-parse HEAD
git --no-optional-locks status --porcelain=v1 --untracked-files=all
git --no-optional-locks diff --cached --binary --no-ext-diff --no-textconv | shasum -a 256
git --no-optional-locks diff HEAD --binary --no-ext-diff --no-textconv | shasum -a 256
```

- `gh` 的寫入命令一律加上 `--repo jeffery777/agent-council`。
- Headless 執行（`claude -p`）使用官方訂閱登入。執行前確認環境中沒有 `ANTHROPIC_API_KEY`（包含繼承來的變數），不使用 `--bare`（規格 PoC-04）。
