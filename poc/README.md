# poc/：M1 雙 CLI PoC 的測試程式

本目錄放 [M1 雙 CLI PoC 計畫](../docs/plans/poc-plan-m1.zh-TW.md) 使用的測試程式。
結果寫入 [PoC 報告](../docs/reports/poc-m1-report.zh-TW.md)。

## 生命週期

- 這些程式用完即丟，只用來回答 M1 的問題。
- 這些程式不可併入正式版，也不可作為正式實作的起點（計畫規則 2）。
- M3 開始前，本目錄必須刪除或移到封存分支（計畫規則 2）。

## 共同規則

執行前先讀計畫第 3 節。重點如下：

- 使用維護者以官方流程完成的訂閱登入。不使用 API key，不使用 `claude --bare`。
- 每個指令第一次使用前，先以 `--help` 確認實際的旗標。
- 會寫入測試 repo 以外位置的步驟，執行前先取得維護者同意。
- 紀錄提交前移除 token、帳號名稱、本機路徑與主機名稱。路徑以 `<repo>`、`<home>` 代替。
- 觸及用量上限時立即停止，並把當時的輸出記入 PoC-05。

## 目錄內容

| 路徑 | 用途 |
| --- | --- |
| `scripts/create-test-repo.sh` | 建立或重建本機測試 repo。 |
| `fixtures/test-repo/` | 測試 repo 的初始內容。全部是為 PoC 編寫的範例，不含私有資料、金鑰或真實專案的程式碼。 |
| `poc-04/` | PoC-04 的固定輸入（`prompt.md`）與輸出格式定義（`output.schema.json`）。兩家 CLI 使用同一份。 |
| `poc-06/` | PoC-06 的讀檔工作（`read-task.md`）、寫檔嘗試（`write-task.md`）與輸出格式定義。兩家 CLI 使用同一份。 |
| `poc-15/` | PoC-15 的審查工作（`review-task.md`）與輸出格式定義，兩家 CLI 使用同一份；受審的變更內容（`change/`，其中刻意含有不安全的程式碼，不可複製使用）；埋入的三個已知問題（`known-issues.json`，不交給審查方）。 |
| `scripts/prepare-poc-15-change.sh` | 把 `poc-15/change/` 的內容提交到測試 repo 的 `poc-15-change` 分支。 |
| `scripts/run-claude-headless.py` | 執行一次 `claude -p`，並依契約 m1-r2 寫出一筆結果紀錄。 |
| `local/` | 本機產生的檔案（SQLite 檔、執行結果的暫存）。這個目錄不進版本控制。 |

其餘 PoC 的程式由後續的 M1 任務加入。

## 執行 `claude -p` 的案例

```bash
# 只顯示將執行的指令，不啟動 CLI。
poc/scripts/run-claude-headless.py poc-04 --model <model> --dry-run

# 執行一次。原始輸出與結果紀錄寫入 poc/local/。
poc/scripts/run-claude-headless.py poc-04 --model <model> --attempt 1
```

- 案例名稱與各自的旗標寫在腳本的 `CASES`。
- 腳本在測試 repo 中啟動 CLI，只傳入少數必要的環境變數，並設定逾時。環境中有 API key 變數時，腳本會停止。
- 啟動前，腳本以 `claude auth status --json` 確認登入方式是訂閱登入；不是時停止，不啟動 CLI。紀錄只保留登入方式的兩個欄位。
- 原始輸出含本機路徑與 session ID，只留在 `poc/local/`。結果紀錄只替換了三種已知路徑，也不是可以直接公開的內容；寫入報告前要人工移除其餘的識別資料。
- 腳本無法確認行程群組已停止時，紀錄的 `error_class` 是 `other`（已逾時的是 `timeout`），測試 repo 的比對記為 `unconfirmed`，腳本以非零結束碼結束。這樣的紀錄不能當作結果使用。
- `poc/scripts/test-run-claude-headless.py` 用假的 CLI 離線測試腳本的正常結束、逾時清理與無法確認停止的情況，假的 CLI 能執行時不會啟動真實 CLI，測試會先確認這一點。測試需要本機已有測試 repo，並會在 `poc/local/` 留下 attempt 0、模型為 `fake-model` 的紀錄；這些不是 PoC 的結果。
- 啟動 CLI 會讓它寫入使用者層級的狀態檔，也會使用訂閱用量。每次執行前先取得維護者同意。

## PoC-15 的受審變更

```bash
# 在測試 repo 建立 poc-15-change 分支並提交變更。分支已存在時，腳本會停止，不做任何修改。
poc/scripts/prepare-poc-15-change.sh

# 執行一次審查。
poc/scripts/run-claude-headless.py poc-15 --model <model> --attempt 1
```

- 變更是一個 commit，作者身分與時間固定。`change/` 與測試 repo 初始內容都沒有改變時，重建後的 commit ID 相同。
- 腳本只寫入測試 repo，並讓測試 repo 停在 `poc-15-change` 分支。PoC-04、PoC-06 的案例要在初始內容上執行；執行前先切回：`git -C <testrepo> switch main`。
- 審查的輸入是 `review-task.md`。執行腳本把其中的 `{{BASE}}`、`{{HEAD}}`、`{{DIFF}}` 換成測試 repo 的兩個 commit ID 與 `git diff` 的輸出，再由 stdin 傳入。兩家 CLI 用同樣的方式產生輸入。
- 腳本依 `known-issues.json` 對輸出做第一次比對（發現中是否提到對應的函式名稱）。這只是初步比對；是否算找到，以報告中的人工判定為準。

## 測試 repo

- 位置：本專案主目錄旁的 `agent-council-poc-testrepo`，也就是 `<repo>/../agent-council-poc-testrepo`。從 worktree 執行時，位置仍以主目錄為準。
- 測試 repo 只存在本機，不設 remote，不推送到任何地方。
- 內容由腳本從 `fixtures/test-repo/` 複製並提交一個初始 commit。腳本只複製 Git 已追蹤（或已 staged）的檔案。
- 作者身分、時間與分支名稱都固定。fixture 內容相同時，重建後的 commit ID 相同。
- 測試 repo 的 commit 作者是固定的佔位身分，只寫在測試 repo 自己的設定中。腳本不修改使用者的 Git 設定；建立測試 repo 時不使用使用者與系統的 Git 設定檔。
- `--recreate` 會刪除整個測試 repo，包含 PoC 留在其中的內容。

```bash
# 建立測試 repo。目錄已存在時，腳本會停止，不做任何修改。
poc/scripts/create-test-repo.sh

# 刪除既有的測試 repo 再重建。只刪除帶有本腳本標記檔的目錄。
poc/scripts/create-test-repo.sh --recreate

# 只顯示將使用的位置，不寫入任何檔案。
poc/scripts/create-test-repo.sh --print-path
```

這個腳本會寫入本 repo 以外的位置。每次執行建立或 `--recreate` 前，先取得維護者同意（Issue #11 維護者決定第 4 項）。
