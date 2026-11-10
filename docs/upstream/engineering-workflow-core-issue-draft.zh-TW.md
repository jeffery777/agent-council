# 給 engineering-workflow-core 的 Issue（繁體中文版）

狀態：已於 2026-11-10 提交為 [engineering-workflow-core#39](https://github.com/jeffery777/engineering-workflow-core/issues/39)

本檔是該 Issue 的繁體中文版本，留作紀錄。提交的版本是英文，依上游近期 Issue 的慣例撰寫，並引用相關的 #38。兩個版本的問題相同。這個 Issue 只作記錄與討論，不要求立即修改 Core。

依據：Core v0.5.0 的 [review-and-security 契約](https://github.com/jeffery777/engineering-workflow-core/blob/main/contracts/review-and-security.md)；agent-council 規格 v0.4 的 D-22 與第 13 節「外部相依」。

---

## Issue 內容

**標題**：討論：另一個接口的 reviewer 路徑（跨廠商審查）需要 Core 補充哪些條件

### 背景

[agent-council](https://github.com/jeffery777/agent-council) 計畫讓一個接口（例如 claude-dev-skills）在 merge 前，把必要的獨立審查與 Security Diff Scan 交給另一個接口（例如 codex-dev-skills）執行，再取回結果。agent-council 只負責投遞、狀態與紀錄。關卡、審查深度與升級條件仍由 Core 與各接口定義。

`review-independent` 已允許使用「獨立服務」作為 reviewer。所以這個 Issue 不提議新增 gate 或 review framework。它只確認既有條文如何適用於另一個接口的 reviewer，並找出需要補充的地方。

### 希望 Core 回答的問題

1. **路徑的資格**：另一個接口執行的 reviewer，是否屬於 `review-independent` 所說的「獨立服務」？
2. **有效唯讀的證據**：`review-required-read-only` 要求接口以當次可核實的控制與生效證據，確認 reviewer 沒有有效的寫入通道。reviewer 在另一個接口執行時：
   - 由哪一個接口負責核實？
   - 請求的一方只能取得對方回報的證據（例如沙箱模式與實際生效的權限）。這種轉交的證據是否足夠？還是請求的一方必須另做比對（例如審查前後的內容雜湊值）？
3. **exact-head 的綁定**：跨接口的審查結果必須帶哪些身分資料，才能符合 exact-head 的要求？目前的構想是：commit、完整 diff 的雜湊值、scope 與需求來源。
4. **讀回**：`review-independent` 規定主代理讀回並驗證整合成果。跨接口的結果是否適用同一條？
5. **資料邊界**：跨廠商審查會把 diff 送到另一家模型供應商。Core 規定缺少能力不授權外傳資料。這條路徑是否必須有明確的專案政策或使用者決定才能啟用？
6. **適用的關卡**：哪些關卡使用這條路徑，是否由 `review-security` 所說的「有效專案政策」決定，而不寫進 Core？
7. **退回**：這條路徑不可用時，接口退回同一 runtime 的 reviewer 路徑。Core 是否需要規定這次退回必須記錄？
8. **findings 的格式**：跨接口的結果沿用 `review-findings` 的欄位（穩定 ID、disposition、`requirement_relation`）。是否需要補充來源接口的欄位？

### 不在這個 Issue 的範圍

- 傳輸與紀錄的實作（屬於 agent-council）。
- 各接口的接合點（屬於各 dev-skills 包）。
- Council 的正式討論與仲裁流程。

### 時程

- 現在：只收集意見。
- agent-council 完成 M1 的 PoC（PoC-15：跨廠商的唯讀審查）之後：依實測能取得的證據，提出具體的條文修改。
- 條文發布之後：各 dev-skills 包在 merge 關卡加入接合點。

### 相關文件

- agent-council 規格 v0.4：D-21 至 D-24、FR-34 至 FR-39、第 13 節「外部相依」。
- agent-council M1 PoC 計畫：PoC-15。
