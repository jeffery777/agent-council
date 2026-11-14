# Agent Council：代理共同指示

本檔適用於整個 repo。所有代理開始工作前必須閱讀本檔，以及 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 依據與目前階段

- 產品需求與決策狀態以 [需求與架構規格](docs/specs/requirements-and-architecture.zh-TW.md) 為準；M1 依 [雙 CLI PoC 計畫](docs/plans/poc-plan-m1.zh-TW.md) 執行。
- 本檔規定本專案的開發協作，不代表 agent-council 已具備自動交接能力，也不替代 engineering-workflow-core 的產品關卡契約（D-22）。
- 目前先準備並完成 M1，再依結果定稿 M2。不得直接開始 M3 正式實作；各里程碑沿用規格與計畫的驗收要求。
- 不得把標為「提議」的決策當成已核准。需求、共用介面或計畫有衝突時，先記錄影響並釐清；可繼續不受影響的工作。

## 開發分工

| 範圍 | 預設 Writer／負責者 | 預設 Reviewer |
| --- | --- | --- |
| 任務拆分、依賴排序、交接與整合安排 | Claude（開發 Orchestrator） | Codex 檢查契約與整合證據 |
| 共用 Core、Broker、MCP、流程控制程式、Claude adapter | Claude | 未參與撰寫的 Codex session |
| Codex adapter | Codex | 未參與撰寫的 Claude session |
| 整合程式、測試與驗證報告 | 預設 Codex，Issue 可另行指定 | 未參與撰寫的另一方 session |
| Security Diff Scan | 獨立、唯讀的 Codex reviewer session | 依 CONTRIBUTING.md 保留結果與證據 |

- 這是本 repo 的預設開發分工。每項任務指定一個 Writer；Reviewer 必須依實際撰寫者調整，不只看檔名或廠商。
- 原 Writer session 不可自我核准。換角色名稱不會形成獨立審查；Codex 撰寫的變更仍須由 Claude 互審。
- Claude 的開發編排權不包含人的決策權，也不能兼任同一討論的仲裁者。產品內的 Flow Controller 與開發 Orchestrator 是不同責任。
- 本次分工不把產品的角色與廠商對應寫死；產品角色仍依規格配置。

## 工作與交接

1. 讀取任務 Issue、需求／計畫及指定的基準 commit。一般實作使用 [協作任務範本](.github/ISSUE_TEMPLATE/agent-task.md)，記錄 Common Contract、Claude Task、Codex Task 與驗收條件。
2. 開始前檢查 branch、HEAD、工作目錄與既有修改。不得覆寫別人的工作；並行開發使用各自的 branch／worktree。同一份檔案同一時間只有一位 Writer。
3. 兩個 adapter 並行開發前，先由雙方確認最小共用契約：請求與結果、狀態與錯誤、開始工作的證據、逾時與取消、mock／測試方式。M1 只定 PoC 所需的契約，不提前凍結正式版 schema。
4. 各自只修改任務範圍。共用契約變更先在 Issue 記錄影響，由另一方確認後更新契約版本，再改動受影響部分。
5. 執行與變更相稱的檢查。只報告實際跑過的指令、環境與結果，不把計畫或推論寫成已驗證。
6. 預設以已推送分支交接，附 Issue／PR、完整 base/head commit SHA、範圍、測試與限制。未提交內容僅作例外，須依 CONTRIBUTING.md 第 5 節附完整 patch（含 untracked）、確切產生命令與原始位元組的 SHA-256。
7. 由獨立 Reviewer 綁定同一份內容審查；修正由 Writer 執行。受審內容、基準或需求版本改變後，舊結果保留為紀錄，重新取得適用於新版本的審查。

Issue／PR 更新不會自動喚醒對方。M1 以前由維護者啟動對方 session，讓對方讀取任務；不得宣稱留言成功就代表對方已接手。交接與審查紀錄格式見 CONTRIBUTING.md。

## 架構與實作邊界

- Claude 與 Codex 都是本系統 MCP server 的 client（D-03）。廠商特有行為留在對應 adapter 或技能包。
- Adapter 只負責通知或啟動、確認已開始、帶回結果（D-25）。執行設定依各 harness 的格式傳遞，不另建統一的工具、模型或沙箱執行引擎。
- 「已投遞」不等於「已開始」。不得用 CLI 結束碼或 MCP 連線代替實際開始工作的證據（FR-22）。
- Broker 用於訊息、工作狀態與稽核，不是 agent 記憶或知識庫（D-26、NFR-11）。不增加跨 thread 的自動／語意檢索，不讀寫或管理原生記憶；允許同一 thread 上下文及以 ID 明確引用已簽核決策。仲裁者依 NFR-11 不接續歷史、能關閉記憶時必須關閉，不能關閉時記錄限制。可重用知識須經人簽核與 storage adapter 發布。
- M1 程式放在 `poc/`，使用專用測試 repo。PoC 程式不得直接成為正式實作；環境、憑證與寫入範圍依 PoC 計畫處理。
- 選擇能驗證當前需求的最小做法。不得自行加入訊息平台、記憶系統、跨主機服務或其他未列入當前里程碑的基礎設施。

## 審查、權限與文件

- Reviewer 與安全掃描 session 必須唯讀，記錄實際生效的權限與可用工具；審查前後檢查受審內容與 repo 狀態。僅口頭要求「不要修改」不足以證明唯讀。
- commit／push 前的發布檢查由各方自己的獨立唯讀 reviewer 執行。分工表中的 Security Diff Scan 在 merge 前綁定 PR head 執行，head 改變後重做；它不是每次 commit／push 都要等待 Codex 的關卡。具體時機與不適用條件見 CONTRIBUTING.md 第 6 節。
- 權限不足或對方不可用時，記錄具體限制。可沿既有授權的替代路徑工作，但不可把缺少的審查記為通過，或擅自放寬權限。
- 不收集、轉送或提交登入 token／憑證；不自動切換到 API 計費。M1 使用官方訂閱登入，遵守計畫的用量與停止條件。
- GitHub 是開發任務與證據的交接處。只放適合該 repo 可見範圍的內容；原始 transcript、私人資料與憑證不得直接貼入。
- 提交、推送、合併及其他外部寫入依使用者已有授權與適用流程執行。本檔不授予破壞性操作或變更授權設定的權限。
- 文件使用繁體中文或既有檔案語言；一句一事，區分事實、推論與待驗證事項。不為純文件修改新增無關測試或工具鏈。
- `CLAUDE.md` 由 Claude 維護，以本檔為共同基礎，只補充 Claude 的載入方式、命令與工具細節；不得複製或另訂衝突的共同政策。
