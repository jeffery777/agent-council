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
| `local/` | 本機產生的檔案（SQLite 檔、執行結果的暫存）。這個目錄不進版本控制。 |

各 PoC 的程式由後續的 M1 任務加入。

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
