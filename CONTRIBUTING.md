# Agent Council：開發與協作規範

本文件規定本 repo 的工作方式，與 [AGENTS.md](AGENTS.md) 一起使用。產品需求、決策與里程碑仍以 [規格](docs/specs/requirements-and-architecture.zh-TW.md) 和 [M1 計畫](docs/plans/poc-plan-m1.zh-TW.md) 為準。

## 1. 責任與審查分工

Claude 負責開發編排、共用 Core／Broker／MCP 與 Claude adapter，並以未參與撰寫的 Reviewer 審查 Codex 的成果。Codex 負責 Codex adapter、整合驗證，以及對 Claude 成果的獨立 review／Security Diff Scan；Codex 成果的安全掃描另依下表指派獨立 session。這項分工不改變產品內可配置的角色，也不將規格中仍屬提議的方案改為已確認。

| 交付內容 | Writer | 功能／契約 Reviewer | Security Diff Scan |
| --- | --- | --- | --- |
| 共用核心或 Claude adapter | Claude | 獨立 Codex session | 獨立、唯讀 Codex session |
| Codex adapter | Codex | 獨立 Claude session | 另一個未參與撰寫的唯讀 Codex session |
| 整合程式、測試與驗證報告 | 預設 Codex，Issue 可另行指定 | 未參與撰寫的另一方 session | 獨立、唯讀 Codex session |
| 文件、計畫與協作規範 | Issue 或使用者指定一方 | 未參與撰寫的另一方 session | 依變更風險記錄適用性與理由 |

Review 與 Security Diff Scan 是兩項結果；同一個獨立 session 可依適用流程產出兩者，紀錄須分開。跨廠商的功能審查不能自動算作安全掃描。若任務指定「安全掃描也必須跨廠商」，Codex 撰寫部分由獨立 Claude 安全 reviewer 處理，Codex 掃描作補充。

原 Writer session 不可核准自己的變更。獨立 Codex session 可以掃描另一個 Codex session 寫的程式，但這不是跨廠商掃描，也不取代 Claude 的互審。若雙方都修改同一份成果，須另外指定未參與撰寫的 Reviewer，並在各自有貢獻的部分保留另一方的互審。

Claude 可安排順序、彙整發現與協調修正；不得把編排身分當成審查通過的依據。意見分歧先以需求、程式與測試證據釐清；涉及需求、重大架構或風險取捨時，由維護者裁決。一般開發交接不必等待 Council 功能完成。

## 2. Issue 作為共同任務契約

使用 [協作任務範本](.github/ISSUE_TEMPLATE/agent-task.md)。開始實作前，契約至少包含：

- 任務目標、里程碑、需求／決策 ID，以及不在範圍內的內容。
- Repository、基準完整 commit SHA、需求／契約版本及已有授權的依據。
- Common Contract：共享的介面、資料範例、錯誤與狀態、限制及測試方式。
- Claude Task 與 Codex Task：各自的 Writer、檔案範圍、依賴、Reviewer 及驗收條件；單方任務的另一欄填「不適用」。
- 整合負責者、交接證據，以及需要人決定的未決問題。

Issue 本文保存目前契約；修訂時新增版本並留言說明差異，保留舊依據。PR 說明實際交付。Review 與測試紀錄綁定 commit，不以聊天中的「已完成」代替。另一個 agent 的訊息可以提出工作或建議，但不會擴張使用者授權。

只有初次建立本套規範時，可先依維護者已明確指定的範圍產出本機變更，再補任務連結；不得因此跳過適用的審查。這項初次建置例外不適用於後續的小型修正、一般實作或規範更新。

## 3. 先確認契約，再並行開發

Claude 提出共用契約草案，Codex 驗證能否對接自己的 harness，雙方在 Issue 明確記錄確認的版本。至少確認：

| 項目 | 要回答的問題 |
| --- | --- |
| 請求與結果 | 必填欄位、穩定 ID、工作快照及輸出範例是什麼？ |
| 狀態 | 如何分辨保存、投遞、認領、開始與完成／失敗？ |
| 開始工作的證據 | 什麼觀察可以證明 session 已開始？哪些僅表示投遞成功？ |
| 錯誤與取消 | 不支援、忙碌、離線、登入失效、用量受限、逾時與取消如何回報？ |
| 執行設定 | 如何原樣傳遞各 harness 的設定，並回報實際權限與限制？ |
| 驗證 | 共用 fixture／mock 是什麼？哪些項目必須用真實 CLI 驗證？ |

M1 只需要能驗證 PoC 的最小契約，正式 schema 在 M2 定稿。Mock 的成功不能算成真實 CLI 的能力證據。契約改變時，先記錄版本、理由、影響範圍與遷移方式，由另一方確認後再修改受影響部分；不受影響的工作可以繼續。

## 4. Branch、檔案與整合

- 並行實作時，每個 Writer 使用自己的 branch／worktree；不得讓兩個 session 在同一 checkout 同時切分支、修改檔案或執行會改寫檔案的檢查。
- Branch 可用 `codex/<issue>-<topic>`、`claude/<issue>-<topic>`。實際檔案 ownership 以 Issue 為準，不預先建立尚未決定的正式程式目錄。
- 共用檔案指定單一 Writer；另一方以建議或 review 交接，避免互相覆寫。整合由 Claude 安排，Codex 驗證結果。
- 各 PR 盡量只含一個可驗收工作包。依賴的契約或核心尚未交付時，標示依賴與基準，不能宣稱已完成整合。
- 不覆寫他人未提交的修改，不執行未經授權的破壞性 Git 操作。沒有建立 branch／worktree 的權限時，可先完成獨占的本機修改並說明限制，不把它描述成已提交或已推送。

## 5. 人工交接與工作狀態

目前以 Issue／PR 交換任務，由維護者啟動接收方。接收方必須自行讀取契約、基準與證據，回覆接受或指出受阻原因。留言、任務指派或訊息投遞本身不代表 session 已開始。

下列是開發紀錄的標記，不是產品 API 的定稿：

| 標記 | 意義與必要紀錄 |
| --- | --- |
| `accepted` | Writer 確認任務、契約版本、基準與範圍 |
| `running` | 已開始執行，附 branch／非識別的工作區標籤與當前步驟 |
| `blocked` | 說明阻礙、影響、需要誰處理及可繼續的工作 |
| `delivered` | 已提供成果與測試證據，等待獨立審查／驗收 |
| `verified` | 指定驗證者確認該版本符合驗收條件，附審查與測試依據 |

`verified` 不等於已合併，也不等於產品 Council 的人類簽核。開發階段尚無 Web 看板時，維護者在對話或 Issue 的明確決定可作開發授權紀錄；不可冒充未來 FR-28 的產品簽核。

交接留言格式：

```text
Task / Issue:
Status / Requirement or plan revision / Contract revision:
Writer / Receiving role:
Repository / Branch / PR:
Target branch / Target head commit SHA:
Review base commit SHA (merge-base) / Pushed head commit SHA:
Scope:
Delivered changes:
Checks (command, environment, result):
Limitations / Blockers:
Next action / Acceptance evidence:
```

在已有提交／推送授權時，預設先把工作包提交並推送到自己的分支，再交付完整 base/head commit SHA、目標分支及其 head SHA。這個預設不另外授予推送權限。接收方核對遠端分支及實際取得的 commit，不以分支名稱或本機 HEAD 代替固定版本。審查 base 與目標分支前進時的規則依第 6 節；推送仍須符合該節的發布檢查。

無法提交或推送時記為受阻，由維護者決定。

公開紀錄依 [AGENTS.md](AGENTS.md) 的禁止清單處理。

## 6. 獨立審查與安全掃描

Reviewer 的工具、報告與唯讀資格依下列三點處理：

1. **可以保留 Bash。** 唯讀資格以實際生效的權限與控制判定，不以是否提供 Bash 作為唯一判準。保留 Bash 時，須檢查它與子程序對受審內容的寫入限制，以及網路、憑證與外部服務的操作權限；不能只靠「不要修改」的指示宣稱技術上唯讀。
2. **Reviewer 可以產出報告。** Reviewer 以回覆文字或結構化輸出交付發現、證據與結論，由主 session 讀回後保存到檔案或發布到 Issue／PR。產出報告不要求 Reviewer 擁有寫檔或外部發布權限；主 session 保存報告不代表 Reviewer 可以修改受審內容。
3. **未受限制的 Bash 寫入能力必須揭露並依例外程序處理。** 記錄仍可寫入的通道、保留的必要理由、替代偵測方式與盲區，依當次適用規範及維護者授權處理殘餘風險。符合維護者已授權例外的路徑，須引用 Issue／PR 上可核對的授權紀錄與範圍，不得直接宣稱技術上唯讀；本節本身不授權任何路徑。在開發對話中取得的直接授權可轉記到 Issue／PR，清楚標明來源。環境、控制或授權範圍改變時重新評估；仍有效的既有授權不必重複詢問。未取得適用例外時，依本節的受阻與替代路徑處理。

Review 與 Security Diff Scan 處理 agent 指示檔時，依 AGENTS.md「審查、權限與文件」的規定。

**審查版本的定義與重審。** 紀錄必須包含目標分支名稱、審查時該分支的完整 `target_head` SHA、完整 PR `head` SHA，以及兩者的 `merge-base`；本文件的審查 `base` 一律指該 merge-base，完整受審差異為 `base..head`。任務開始時的實作基準另外標示，不可與審查 base 混用。需求／計畫版本與契約版本也須各自記錄。

PR head 改變後重審。目標分支前進時，合併前由主 session 比對目標分支的變動檔案與 PR 的檔案；有交集才同步並重審，沒有交集時留一筆比對紀錄。

檢查分成兩層，避免把 merge 前的跨廠商掃描解讀成每個 commit 都要等待另一方啟動：

| 時機 | 負責者與範圍 | 版本與重做條件 |
| --- | --- | --- |
| commit／push 及發布 Issue／PR／review 文字前的發布檢查 | 各方自己的獨立唯讀 reviewer 或維護者已授權的例外路徑；檢查要發布的金鑰／私人資料、作者身分、commit／push 訊息及公開文字。這不是分工表中的 Security Diff Scan。 | commit 前檢查 staged 內容與預定身分／訊息；push 前核對目的地、目標 ref 名稱、待推送 commits 的內容與 metadata，包含可能留在歷史的資料。公開文字也須在發布前檢查；受檢內容、metadata、目的地或 ref 改變後重審。 |
| PR merge 前的 Review／Security Diff Scan | 依第 1 節分工指派獨立唯讀 session 或維護者已授權的例外路徑；掃描範圍是 PR 的完整差異，安全掃描依變更風險判定適用性。 | 綁定目標分支、完整 target_head／base／head SHA、範圍、需求／計畫與契約版本。merge 前取得一組有效結果即可，不要求每次發布都由 Codex 掃描；PR head 改變或目標分支前進時，依上方規則處理。 |

Security Diff Scan 的適用性由獨立掃描方或維護者依變更風險判定，附理由與依據；Writer 不得自行判定不適用。改動審查資格、權限、憑證、發布規則或包含可執行內容的文件，必須納入安全掃描。即使經判定不適用，仍須執行發布檢查與適用的獨立 review。既有上游／dev-skills 若要求其他檢查，仍依其適用版本執行。Reviewer 不可用或無法證明實際唯讀時，沿用下方受阻與替代路徑的規則，不把 Writer 自查算成獨立檢查。

Reviewer 先確認自己未參與受審內容的撰寫，再取得同一組需求、契約版本與完整變更。審查至少檢查正確性、契約相容性、範圍偏離、測試證據及安全影響；安全掃描依差異與實際資料流執行。

每次結果必須附：

1. 任務、需求／決策、需求／計畫版本與契約版本；repo、目標分支及完整 target_head／base／head SHA、diff 範圍。
2. Reviewer 的 harness 名稱與版本、任務內的非識別 Reviewer 標籤、模型與版本（能取得時），以及未參與撰寫的聲明。
3. 實際生效的唯讀控制、與寫入能力相關的工具類別及寫入通道摘要，或維護者例外授權的紀錄；審查前後的 HEAD、工作目錄狀態及受審內容比對結果。公開紀錄依 AGENTS.md 的禁止清單處理。
4. 實際執行的檢查、結果、限制及未驗證事項。不能只用「沙箱已啟用」或事後沒有 diff 證明所有通道唯讀。
5. Findings：穩定 ID、嚴重度、位置、證據、建議處置、disposition 與 `requirement_relation`；另明確判定是否偏離任務依據。
6. Review 與 Security Diff Scan 各自的結論：通過、需修正、受阻，或有理由的不適用。

以上是本 repo 的交接紀錄要求，不宣稱跨 harness 路徑已取得上游資格。Findings 欄位與 gate 的正式判定沿用當次適用的 engineering-workflow-core／dev-skills 版本；不得在本 repo 再造一套產品 review engine。上游路徑資格與證據的待定事項見 [engineering-workflow-core#39](https://github.com/jeffery777/engineering-workflow-core/issues/39)，M1 PoC-15 提供實測依據。

Reviewer 發現問題後交回 Writer 修正，不直接改受審檔案。Writer 逐項回覆修正或不採納的理由與證據。重審依本節「審查版本的定義與重審」處理，並綁定最新完整交付範圍。

對方不可用時，維護者可人工啟動審查，或依既有流程使用獨立的同廠商 reviewer；需記錄原因與替代方式。若無法證明有效唯讀且不符合維護者已授權的例外，或必要審查未完成，記為受阻，不擅自移除工具限制或把它記為通過。既有且仍適用的授權不必重複詢問。

## 7. 檢查與完成條件

目前 repo 只有文件，沒有 build、test 或 CI 指令。不得報告不存在的檢查，也不為本次規範新增工具鏈。文件變更檢查相對連結、表格、需求與決策引用、術語及 `git diff --check`；不要把自行檢查標為獨立 review。

M1 開始後，實際命令與環境依 PoC 計畫記錄。新增程式時，提供能驗證行為與失敗路徑的檢查；避免只重述實作的測試。正式測試指令等語言與工具鏈決定後再補入本文件。

工作包完成須符合：範圍與契約一致、必要檢查有證據、發現已處置、適用的獨立審查／安全掃描已完成、限制已揭露。里程碑另依原計畫由維護者驗收。M1 報告與 PoC 程式的生命週期遵守 M1 計畫；不以本文件解除既有驗收要求。
