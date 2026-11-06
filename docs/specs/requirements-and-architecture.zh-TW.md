# Agent Council：Claude × Codex 協作通訊層 需求與架構規格 v0.1

狀態：v0.1 草案 · 2026-11-06

## 1. 文件資訊

Agent Council 讓 Claude 與 Codex 針對特定專案進行結構化討論，由獨立仲裁者質詢，最後由流程控制器向人提出結論與建議。本文件為 v0.1 草案，定義需求、協定、架構與開發計畫，待審閱。

- 範圍：需求、討論協定、系統架構、人的介面、開發計畫。API schema 與資料模型另立文件。
- 用詞規範：中文參考 ASD-STE100：一句一事、主動語態、一詞一義。英文規格文件必須遵守 ASD-STE100。
- 規範用語：「必須」= MUST，「應」= SHOULD，「可」= MAY。

| 術語 | 定義 |
| --- | --- |
| Thread | 一次針對專案問題的完整討論，從需求到簽核 |
| 參與者（Participant） | 提出立場的 agent：Claude 或 Codex |
| 仲裁者（Arbiter） | 質詢雙方並產出仲裁報告的獨立 agent session |
| 流程控制器（Flow Controller） | daemon 內控制流程、回合、上限與交付的確定性程式。它不同於 Claude 或 Codex session 內負責調度 subagent 的主 agent |
| 端點（Endpoint） | 一個 agent 介面：Claude Desktop、Claude Code CLI、Codex Desktop、Codex CLI |
| Adapter | 把廠商介面轉換為本系統協定的防腐層 |
| Broker | 保存 thread、訊息、決策的本機常駐服務 |
| 立場書（Position） | 參與者的方案、受阻與限制、建議解法與證據 |
| ADR | Architecture Decision Record，簽核後的決策紀錄 |

## 2. 背景與自行開發的理由

自行開發有兩個理由：資料不經第三方，以及廠商改版導致介面中斷時可以第一時間自行修復。

**觸發情境。** engineering-workflow-core 是 claude-dev-skills、codex-dev-skills、grok-build-dev-skills 的上游。除 claude-dev-skills 外，其餘三個專案由 Codex 維護。需求動到上游時，Claude 與 Codex 必須共同討論，因為兩者的沙箱工具與能力不同。

**既有方案的不足。** [Reason Network](https://glama.ai/mcp/servers/ko297wii18) 於 2026-10-16 推出，提供通用的 agent 訊息通道。它需要 Reason 帳號，且沒有專案範圍、仲裁流程與決策治理。

**改版實例。** OpenAI 於 2026-08-24 棄用 `codex mcp-server`，並於 2026-09-05 在 Codex CLI 0.154.0 移除（[PR #42993](https://github.com/openai/codex/pull/42993)）。官方替代的 App Server 不是 MCP server，而且仍是實驗功能（[OpenAI 文件](https://developers.openai.com/es-419/docs/mcp-server)）。依賴該介面的整合在三週內失效。本專案的架構必須把這類風險隔離在 adapter 內（見 NFR-01）。

## 3. 決策清單

D-01 至 D-08 已於 2026-11-06 的討論中確認；D-09 與 D-10 為提議，待確認。

| ID | 決策 | 狀態 |
| --- | --- | --- |
| D-01 | 本系統為獨立專案，以 MCP server 與 skills / plugins 提供 | 已確認 |
| D-02 | Claude 與 Codex 的桌面版、終端機版必須彼此互通 | 已確認 |
| D-03 | Claude 與 Codex 只當本系統 MCP server 的 client；不依賴任一方作為 MCP server | 已確認 |
| D-04 | 雙方各自提出想法、受阻或受限的問題、建議解法；第三方仲裁者對雙方質詢；流程控制器向人提出最終結論與建議 | 已確認 |
| D-05 | 仲裁者使用 Claude 或 GPT 的更高階模型，以獨立 session 執行 | 已確認 |
| D-06 | 人的介面：本機 Web 看板為主，桌面版對話內的 MCP 工具為輔 | 已確認 |
| D-07 | P1 為同一台 Mac mini 的桌面版加 CLI；P2 跨主機；雲端 session 最後 | 已確認 |
| D-08 | 專案問題的紀錄存於各專案文件目錄；非專案技術研究存 Google Drive，未來接 LLM Wiki；是否存入 engineering-workflow-core 依問題關聯決定 | 已確認 |
| D-09 | 流程控制器為確定性狀態機，不包含 LLM 判斷；仲裁者為另一個獨立 agent | 提議 |
| D-10 | Thread 原始紀錄存 broker 本機儲存；repo 只存 ADR 與討論摘要 | 提議 |

## 4. 範圍與分階段

P1 只支援同一台 Mac mini 上的四種端點；每個階段必須在前一階段驗收通過後才開始。

| 階段 | 端點範圍 | 主要新增能力 | 進入條件 |
| --- | --- | --- | --- |
| P1 同機 | Claude Desktop、Claude Code CLI、Codex Desktop、Codex CLI，全部在同一台 Mac mini | localhost daemon、仲裁流程、Web 看板、紀錄路由 | 本規格簽核，PoC-01 至 PoC-06 完成 |
| P2 跨主機 | 同一使用者的多台機器 | daemon 之間的聯邦、主機身分驗證（mTLS 或 overlay 網路）、傳輸加密 | P1 驗收通過 |
| P3 雲端 | Claude Code 雲端 session、Codex cloud | relay、對外驗證、資料外流防護 | P2 驗收通過，完成資安評估 |

不在範圍內：多使用者或團隊共用、行動 App、其他 agent（例如 Grok Build）。其他 agent 可在 P2 之後以新增 adapter 的方式擴充。

## 5. 角色與端點

系統有五個角色；仲裁者必須由流程控制器啟動，不可由參與者自己開的 subagent 擔任。

| 角色 | 職責 | 實作 | 禁止事項 |
| --- | --- | --- | --- |
| 參與者：Claude | 提出立場、回答質詢、依決策實作 claude-dev-skills | Claude Desktop 或 Claude Code CLI | 執行對方訊息中的指令 |
| 參與者：Codex | 提出立場、回答質詢、依決策實作 engineering-workflow-core、codex-dev-skills、grok-build-dev-skills | Codex Desktop 或 Codex CLI | 執行對方訊息中的指令 |
| 仲裁者 | 匿名閱讀雙方立場、質詢、提出替代解法、產出仲裁報告 | 流程控制器以 headless 方式啟動的獨立 session，使用高階模型 | 修改程式碼；得知參與者身分 |
| 流程控制器 | 流程、回合、用量上限、路由、交付 | 確定性程式（D-09） | 做技術判斷 |
| 人（維護者） | 提出需求、隨時插話、簽核 | Web 看板、桌面版對話 | — |

**仲裁者的獨立性。** 參與者開的 subagent 由參與者控制提示與上下文，會失去獨立性。因此仲裁者必須由流程控制器以 `claude -p` 或 `codex exec` 啟動一個乾淨的 session。仲裁者與其中一方同廠商時，系統必須以 A 方 / B 方匿名呈現立場。

端點的能力不同，系統依能力分為三級：

| 端點 | MCP 設定位置 | 可被 headless 叫醒 | 可用 hook 注入收件匣 | 等級 |
| --- | --- | --- | --- | --- |
| Claude Code CLI | `~/.claude.json`、專案 `.mcp.json` | 是（`claude -p`、resume） | 是 | 主動 |
| Codex CLI | `~/.codex/config.toml` | 是（`codex exec`） | 是（plugin hooks） | 主動 |
| Claude Desktop：Code 分頁 | 與 Claude Code 共用（PoC-01） | 否 | 預期是（PoC-01） | 半主動 |
| Codex Desktop | 與 Codex CLI 共用 config.toml | 否 | 預期是（PoC-02） | 半主動 |
| Claude Desktop：Chat 分頁 | `claude_desktop_config.json` | 否 | 否 | 被動 |

需要自動多輪往返的討論，由流程控制器驅動 CLI 端點執行。桌面版端點主要用於人的參與與簽核；桌面版仍可遠端控制 CLI 進行開發。

## 6. 功能需求

功能需求共 16 項，每項必須對應至少一個驗收測試（見第 13 節）。

| ID | 需求 |
| --- | --- |
| FR-01 | 建立 thread 時，系統必須記錄專案、主題與影響範圍（上游與下游 repo）。 |
| FR-02 | 訊息必須寄給角色（例如 `maintainer@engineering-workflow-core`），不可寄給個別 session。 |
| FR-03 | 端點啟動時必須登記 agent、介面、專案與能力等級，並定時回報 heartbeat。 |
| FR-04 | 同一角色有多個 session 在線時，session 回覆前必須認領該回合；認領逾時後系統必須釋放。 |
| FR-05 | 訊息必須帶類型：position、question、answer、evidence、arbitration-report、decision。 |
| FR-06 | 在 POSITIONS 階段，參與者提交前不可讀到對方的立場書。 |
| FR-07 | 立場書必須包含五個欄位：方案、受阻或受限的問題、建議解法、證據、對下游的影響。 |
| FR-08 | 仲裁者必須對每一方至少提出一個質詢，可提出替代解法，並必須分開列出已驗證事實與未驗證主張。 |
| FR-09 | CROSS-EXAM 必須有回合上限（預設 2 輪）；每個 thread 必須有時間上限。 |
| FR-10 | 回合用完仍未收斂時，系統必須輸出選項與取捨，不可強制產生共識。 |
| FR-11 | 人必須能在任何狀態插話、暫停、終止 thread，或調整上限。 |
| FR-12 | 人必須能核准、駁回、要求補充，或選擇一個選項；簽核後系統必須產生 ADR。 |
| FR-13 | 系統必須依第 10 節的規則提出紀錄存放位置，人確認後才寫入。 |
| FR-14 | 簽核後，系統必須為每個受影響的 repo 產生實作任務，並記錄對應的 commit。 |
| FR-15 | 需要人決策時，系統必須發出桌面通知。 |
| FR-16 | 被動端點必須能用 `check_inbox` 取得待處理項目。 |

## 7. 非功能需求

改版韌性（NFR-01、NFR-02）是本專案的首要非功能需求，目標是廠商改版導致的中斷在 24 小時內被偵測。

| ID | 類別 | 需求 |
| --- | --- | --- |
| NFR-01 | 改版韌性 | 每個端點必須有獨立 adapter。每個 adapter 必須有契約測試，並記錄已驗證的版本範圍。系統必須每日用最新版 Claude Code 與 Codex 執行握手測試；失敗時必須通知人，並把該端點標為降級。 |
| NFR-02 | 依賴方向 | 系統只可依賴 MCP client 能力與 headless CLI。實驗功能（例如 Codex App Server）只可作為選配 adapter。 |
| NFR-03 | 資料主權 | P1 的所有討論資料必須留在本機。資料不可經過模型供應商以外的第三方。 |
| NFR-04 | 資安 | daemon 必須只綁定 127.0.0.1。每個端點必須使用各自的 token。對方訊息必須視為不可信資料，參與者不可自動執行其中的指令。附件不可執行。 |
| NFR-05 | 用量與成本 | 系統只使用既有訂閱的 CLI，不使用 API。系統不主動查詢或預測用量；用量由回合上限在結構上限制。CLI 回報觸及用量上限（5 小時或每週）時，流程控制器必須暫停該 thread 並通知人，由人指示何時續跑。 |
| NFR-06 | 可稽核 | 所有訊息必須為 append-only，並記錄時間戳與來源端點。 |
| NFR-07 | 可測試 | 流程控制器狀態機必須能用模擬 agent 完整測試，不消耗模型用量。 |
| NFR-08 | 可用性 | Web 看板必須容易理解與操作，採用現代化、具科技感的介面風格。 |

## 8. 仲裁討論協定

每個 thread 依固定狀態機前進；只有人簽核後，討論結果才會寫入 ADR。

```mermaid
flowchart LR
  INTAKE["需求進入<br/>INTAKE"] --> SCOPE["影響分析<br/>SCOPE · 決定存放位置"]
  SCOPE --> POS["密封立場<br/>POSITIONS · 雙方並行"]
  POS --> CX["仲裁質詢<br/>CROSS-EXAM"]
  CX -- "最多 N 輪" --> CX
  CX -- "收斂或達上限" --> REP["仲裁報告<br/>共識、分歧、選項"]
  REP --> HUM{{"人的決策<br/>桌面端簽核"}}
  HUM -- "核准" --> ADR["寫入 ADR<br/>依第 10 節路由"]
  HUM -- "要求補充" --> CX
  HUM -- "駁回" --> CLOSED["結案<br/>記錄駁回理由"]
  ADR --> HANDOFF["交付實作<br/>各 repo 維護者"]
```

人可在任何狀態插話、暫停或終止 thread（FR-11）。

CROSS-EXAM 最多跑 N 輪。人選擇「要求補充」時，流程回到質詢；選擇「駁回」時，thread 結案並保留理由。

仲裁報告必須包含以下欄位，流程控制器依此格式向人呈現結論：

1. 共識點。
2. 分歧點，及各方的理由。
3. 已驗證事實與未驗證主張，分開列出。
4. 仲裁者提出的替代解法（可無）。
5. 選項與取捨；仲裁者建議的選項及理由。
6. 對上游與下游 repo 的影響與風險。

## 9. 系統架構

Claude 與 Codex 只當 MCP client 連到本機 daemon；所有廠商介面的差異必須收在 adapter 內。

```mermaid
flowchart TB
  subgraph EP["端點（MCP client）"]
    CD["Claude Desktop<br/>Code / Chat 分頁"]
    CC["Claude Code CLI<br/>skill + hooks"]
    XD["Codex Desktop<br/>plugin（共用 config）"]
    XC["Codex CLI<br/>plugin + hooks"]
  end
  subgraph D["agent-council daemon · 只綁 127.0.0.1"]
    MCP["MCP server（council_* 工具）<br/>Streamable HTTP；Desktop Chat 經 stdio shim"]
    FC["流程控制器<br/>確定性狀態機，不含 LLM"]
    BR["Broker<br/>append-only 本機儲存"]
    WEB["Web 看板<br/>人的主要介面"]
    AD["Adapters（防腐層）<br/>claude -p、hooks ｜ codex exec、plugin"]
    CP["相容性檢查<br/>每日握手測試、告警"]
  end
  CD & CC & XD & XC --> MCP
  MCP --> FC
  MCP --> BR
  FC <--> BR
  BR --> WEB
  FC --> AD
  CP --> AD
  CP --> WEB
  AD -- "headless 啟動" --> ARB["仲裁者<br/>獨立 session、高階模型"]
  AD -- "storage adapter 寫入" --> REPO["各專案 repo<br/>docs/adr 與摘要"]
  AD --> GD["Google Drive<br/>非專案技術研究"]
  AD -.-> WIKI["LLM Wiki<br/>未來接入"]
```

廠商改版時，只需修改對應的 adapter；流程控制器、broker 與討論協定不必變更。

MCP 工具初版清單（名稱待 API schema 定稿）：

| 工具 | 用途 | 使用者 |
| --- | --- | --- |
| `council_register` | 登記端點與 heartbeat | 參與者 |
| `council_open_thread` | 建立 thread | 人、參與者 |
| `council_check_inbox` | 取得待處理項目 | 參與者 |
| `council_claim_turn` | 認領回合 | 參與者 |
| `council_post` | 提交立場書、回答、證據、插話 | 參與者、人 |
| `council_read_thread` | 讀取 thread（依狀態過濾密封內容） | 參與者、人 |
| `council_status` | 查詢 thread 與端點狀態 | 人 |
| `council_sign_off` | 簽核決策 | 人 |

Claude 端以 skill 定義討論協定；Codex 端以 plugin 打包 skill、hooks 與 MCP 設定。

## 10. 紀錄存放與路由

SCOPE 階段由流程控制器依影響範圍提出存放位置，人確認後系統才寫入。

| 情況 | 存放位置 | 路徑範例 |
| --- | --- | --- |
| 只影響單一專案 | 該專案的文件目錄 | `docs/adr/NNNN-<slug>.md`、`docs/council/<thread-id>.md` |
| 變更 engineering-workflow-core 的規範 | engineering-workflow-core 的文件目錄；各下游專案放連結 | 上游 `docs/adr/`，下游 `docs/upstream-decisions.md` |
| 跨專案但不動上游規範 | 主要受影響專案；其他專案放連結 | 同上 |
| 與專案無關的技術研究 | Google Drive；未來接 LLM Wiki | Drive 資料夾待定 |

所有存放位置必須透過 storage adapter 寫入；repo、Google Drive、LLM Wiki 各自是一個 adapter。這樣未來接上 LLM Wiki 時，核心協定不必修改。依 D-10 的提議，repo 只存 ADR 與摘要，完整討論紀錄留在 broker，避免 repo 膨脹。

## 11. 人的介面

人的主要介面是由 daemon 提供的本機 Web 看板；桌面版對話內的 MCP 工具只負責查狀態、插話與簽核。

| 畫面 | 功能 | 桌面版對話也可以做 |
| --- | --- | --- |
| 總覽 | 依專案列出 thread、狀態、受影響的下游 repo | 是（`council_status`） |
| Thread 詳情 | 時間軸、雙方立場書並排對照、質詢與回答、仲裁報告 | 部分（摘要） |
| 決策佇列 | 待簽核項目；核准、駁回、要求補充、選擇選項 | 是（`council_sign_off`） |
| 插話 | 對進行中的 thread 補充需求或約束 | 是（`council_post`） |
| 控制 | 暫停、終止、回合上限、仲裁模型 | 否 |
| 端點與相容性 | 在線端點、能力等級、adapter 健康度、每日相容性檢查結果、已驗證版本 | 是（摘要） |
| 稽核 | 完整紀錄、匯出、ADR 與 commit 連結 | 否 |

介面原則：深色主題為預設；thread 狀態以顏色與文字同時標示；待人決策的項目必須在每個畫面可見。視覺設計另在 M5 以 mockup 確認。

## 12. 風險與待驗證假設

六個 PoC 必須在實作前完成，因為它們決定各端點的等級與仲裁者的執行方式。

| ID | 假設或風險 | 驗證或緩解方式 | 失敗時的影響 |
| --- | --- | --- | --- |
| PoC-01 | Claude Desktop 的 Code 分頁讀取 Claude Code 的 MCP 與 hooks 設定 | 註冊測試 server 與 hook，在兩種介面各執行一次 | 該端點降為被動 |
| PoC-02 | Codex Desktop 透過 plugin 載入 MCP 與 hooks | 建立測試 plugin，在 Desktop 與 CLI 各執行一次 | 該端點降為被動 |
| PoC-03 | Claude Desktop Chat 分頁可連接 localhost HTTP MCP | 直連測試；失敗則改用 stdio shim | 需要 stdio shim |
| PoC-04 | `claude -p` 與 `codex exec` 可指定高階模型，以乾淨上下文執行仲裁 | 以固定輸入執行三次，比較輸出格式 | 仲裁者改走 API，產生額外費用 |
| PoC-05 | CLI 觸及用量上限時，回傳可辨識的錯誤訊息或結束碼 | 查閱兩家 CLI 文件，並記錄實際觸及上限時的輸出 | 改以逾時判定並通知人 |
| PoC-06 | headless 執行不會卡在核准提示 | 測試各 CLI 的唯讀沙箱與核准設定 | 該端點無法自動多輪 |
| R-01 | 兩個 LLM 互相附和 | 密封立場、獨立仲裁、不強制共識（FR-06、FR-08、FR-10） | 討論流於形式 |
| R-02 | 跨 agent 的 prompt injection | NFR-04；訊息以資料標記包裝 | 參與者執行未授權操作 |
| R-03 | 仲裁者偏袒同廠商的一方 | 匿名呈現；評估「雙仲裁」選項 | 結論偏頗 |
| R-04 | 觸及訂閱用量上限（5 小時或每週） | NFR-05 的回合上限與暫停續跑機制 | 日常開發受影響 |
| R-05 | 廠商 CLI 旗標或設定格式變動 | NFR-01 的契約測試與每日檢查 | 端點中斷 |

## 13. 開發計畫

P1 分為 M0 至 M6 七個里程碑；每個里程碑必須通過其驗收關卡後，下一個才開始。日期待規格簽核後訂定。

| 里程碑 | 交付內容 | 測試 | 驗收關卡 |
| --- | --- | --- | --- |
| M0 規格定稿 | 本文件 v1.0、API schema 草案 | — | 維護者簽核 |
| M1 PoC | PoC-01 至 PoC-06 結果報告，更新端點能力矩陣 | 手動驗證 | 每個端點的等級已確定 |
| M2 核心 | daemon、broker、MCP server、流程控制器狀態機 | 單元測試；以模擬 agent 跑完整流程 | 模擬流程從 INTAKE 到 ADR 全部通過 |
| M3 Adapter | 四個端點 adapter、Claude skill 與 Codex plugin | 契約測試；四端點端對端測試 | 四個端點都能登記、收發訊息 |
| M4 仲裁與路由 | 仲裁者啟動、匿名化、ADR 產生、storage adapter | 用一個真實的 engineering-workflow-core 需求試跑 | 產出可簽核的仲裁報告與 ADR |
| M5 Web 看板 | 第 11 節的畫面 | 使用者驗收測試 | 維護者可只用看板與桌面版完成一個 thread |
| M6 相容性自動化 | 每日握手測試與告警 | 以模擬版本變動觸發告警 | 告警在 24 小時內送達 |

P1 整體驗收標準：

1. 四個端點中任意一個都能參與同一個 thread。
2. 一個真實的上游變更需求能從 INTAKE 跑到 ADR 寫入，且人只在簽核時介入。
3. 未收斂的 thread 產出選項與取捨，而非強制共識。
4. 停用任一端點時，系統降級運作且不遺失訊息。
5. 沒有任何討論資料離開本機（模型供應商除外）。

## 14. 未決問題

M0 簽核前必須回答以下問題。

- [ ] D-09：流程控制器不含 LLM，仲裁者為獨立 agent，是否接受？
- [ ] D-10：完整紀錄留在 broker、repo 只存 ADR 與摘要，是否接受？
- [ ] 專案名稱（暫稱 Agent Council）與 repo 位置（GitHub 或 GitLab）。
- [ ] 實作語言：TypeScript（MCP SDK 成熟、開發快）或 Rust / Go（單一 binary、常駐服務較穩）。
- [ ] CROSS-EXAM 回合上限的預設值。
- [ ] 高影響 thread 是否提供「雙仲裁」選項（Claude 與 GPT 各一，用量加倍）。
- [ ] Google Drive 存放技術研究的資料夾位置。
