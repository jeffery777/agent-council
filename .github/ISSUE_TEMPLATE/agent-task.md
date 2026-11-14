---
name: Agent collaboration task
about: 定義 Claude 與 Codex 的共同契約、工作範圍與交接證據
title: ""
labels: ""
assignees: ""
---

## 目標與依據

- 目標／要解決的問題：
- 里程碑：
- 需求／決策 ID 與來源：
- 使用者授權／維護者決定的來源：
- Repository：
- 基準完整 commit SHA：
- 契約版本：
- 不在範圍內：

## Common Contract

只填本工作包需要的最小契約。M1 的契約不代表正式版 schema。

- 請求／結果欄位與範例：
- 狀態、錯誤與開始工作的證據：
- 忙碌、逾時、取消、重試與去重：
- harness 設定的傳遞及權限證據：
- 共用 fixture／mock 與真實 CLI 驗證的分界：
- 依賴、限制與需要人決定的事項：
- Claude 確認版本／證據：
- Codex 確認版本／證據：

## Claude Task

單方任務可填「不適用」。

- Writer／角色：
- 目標與檔案範圍：
- Branch／worktree 識別：
- 依賴：
- 交付與驗收條件：
- Reviewer：

## Codex Task

- Writer／角色：
- 目標與檔案範圍：
- Branch／worktree 識別：
- 依賴：
- 交付與驗收條件：
- Reviewer：

## 整合、審查與交接

- 整合安排／驗證負責者：
- commit／push 前發布檢查的獨立唯讀 reviewer：
- merge 前 Security Diff Scan 負責 session（須獨立且唯讀，綁定 PR head）：
- 本次適用的關卡／安全掃描適用性與理由：
- 適用的 engineering-workflow-core／dev-skills 版本（尚未採用填未採用）：
- 必要測試與證據：
- 驗收者：

預設以已推送分支的完整 base/head commit SHA 交接。Review 綁定相同 SHA、範圍與契約版本；PR head 改變後重做。未提交 patch 僅作例外，須包含 untracked、確切產生命令及原始位元組的 SHA-256。交接／review 紀錄依 [CONTRIBUTING.md](https://github.com/jeffery777/agent-council/blob/main/CONTRIBUTING.md) 第 5、6 節；本分支審閱時可先讀取根目錄的同名檔案。

## 進度與修訂

以留言保留 `accepted / running / blocked / delivered / verified` 的進度、PR／commit 與證據。修改本文契約時，增加版本並留言記錄差異。Issue 更新後仍需由維護者啟動接收方，不表示對方已開始。
