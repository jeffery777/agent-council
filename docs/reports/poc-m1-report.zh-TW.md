# Agent Council：M1 雙 CLI PoC 報告

狀態：進行中 · 2026-11-16 · 對應 [M1 雙 CLI PoC 計畫](../plans/poc-plan-m1.zh-TW.md)（2026-11-10 草案）與規格 v0.6

目前已填：環境紀錄、PoC-04 與 PoC-06（M1-2），以及 PoC-15 中 Claude 的部分（M1-3）。其餘各節的「待填」不代表任何結果。

## 1. 填寫規則

- 報告不可包含 token、帳號名稱、本機路徑或主機名稱。路徑以 `<repo>`、`<home>` 代替（計畫規則 6）。
- 只記錄實際執行過的指令與觀察到的結果。推論與未驗證的事項要標明。
- 每個指令第一次使用前，先以 `--help` 確認旗標；與計畫不同的地方記在該項目的「與計畫的差異」（計畫規則 5）。
- 各項目的通過條件以計畫第 5、6 節為準。mock 只用於檢查腳本本身，不能作為 CLI 能力的證據。
- 重試另記一筆，不覆寫原紀錄。
- 每次 headless 執行的紀錄欄位依 Issue #11 的 Common Contract（契約版本 m1-r2；M1 用的草案，不是正式版 schema）。

## 2. 環境紀錄

依計畫第 4 節。

| 項目 | 紀錄 | 記錄日期與來源 |
| --- | --- | --- |
| 作業系統與版本 | macOS 27.2（build 26B123），arm64 | 2026-11-15，`sw_vers` 與 `uname -m` |
| Claude Code CLI 的版本 | 2.1.312 | 2026-11-15，`claude --version` |
| Codex CLI 的版本 | codex-cli 0.169.0 | 2026-11-15，`codex --version` |
| Claude Code 的登入方式 | 訂閱登入：`authMethod` 為 `claude.ai`，`apiProvider` 為 `firstParty`。環境中沒有 `ANTHROPIC_API_KEY`。 | 2026-11-15，`claude auth status --json`（只取這兩個欄位）與環境變數檢查 |
| Codex 的登入方式 | 訂閱登入：輸出為「Logged in using ChatGPT」。 | 2026-11-15，`codex login status` |
| Claude 使用的模型 | `claude-sonnet-5-5`。維護者於 2026-11-15 在開發對話中確認。 | 2026-11-15，PoC-04 與 PoC-06 每次執行的 init 事件都回報這個名稱 |
| Codex 使用的模型 | 請求值 `gpt-6.1-sol`；實際回報值為未知。五次的 harness JSONL 與 stderr 均未提供模型名稱，不採用模型自述或模型清單推定。 | 2026-11-15，PoC-04 三次、PoC-06 兩次的原始輸出 |

- CLI 版本在 M1 期間改變時，新增一列並註明日期，不覆寫舊紀錄。
- 測試 repo：只存在本機的 Git repo，位置是 `<repo>/../agent-council-poc-testrepo`，沒有 remote。內容由 `poc/scripts/create-test-repo.sh` 產生。

## 3. 結果總表

| 項目 | 結論 | 執行日期 | 對規格的影響 |
| --- | --- | --- | --- |
| PoC-04 headless 啟動與受控的設定 | 部分通過。Claude：通過；Codex：部分通過。 | 2026-11-15 | Codex 三次 JSON 符合格式，但模型、完整工具與載入設定的觀察不足；暫不認定 Codex 仲裁者可自動啟動，保留人啟動的方案。見該節。 |
| PoC-05 用量上限的回報 | 待填 | | |
| PoC-06 headless 不卡在核准提示 | 通過。Claude、Codex 的部分均通過。 | 2026-11-15 | Codex 讀檔不需人介入，patch 寫入請求被拒後指令會結束，符合計畫第 5 節的通過條件；直接工具名稱、精確目標及不經 shell 的路徑仍列為限制。adapter 須同時檢查 JSONL、stderr 與 repo 比對。 |
| PoC-13 投遞到 Claude Code 的既有 session | 待填 | | |
| PoC-14 `codex queue` 投遞到既有 session | 待填 | | |
| PoC-15 跨廠商的唯讀審查 | Claude 的部分：通過。Codex 的部分：部分通過。 | 2026-11-16（Claude）、2026-11-17（Codex） | 兩邊三次輸出均符合格式且找到三個已知問題；Codex 的完整實際權限邊界仍未證實，整項不記為通過。 |
| 整合測試：兩家 CLI 的問答往返 | 待填 | | |

結論填「通過」、「部分通過」、「不通過」或「未完成」。「未完成」要說明原因（計畫第 7、9 節）。

## 4. PoC 項目

每一節的問題、步驟與通過條件以計畫第 5 節為準，這裡不重複。

### PoC-04：headless 啟動與受控的設定

固定輸入是 `poc/poc-04/prompt.md`，輸出格式定義是 `poc/poc-04/output.schema.json`。兩家使用同一份。

#### Claude 的部分

- 執行日期與 CLI 版本：2026-11-15，Claude Code 2.1.312。
- 與計畫的差異（旗標、步驟）：
  - 計畫沒有指定旗標。實際使用的旗標先以 `claude --help` 確認，列在下方的指令中。
  - 在三次執行之外，另外執行三次記憶探測，用來回答步驟 4。維護者於 2026-11-15 在開發對話中同意。
  - 執行腳本只傳入少數必要的環境變數（`HOME`、`PATH` 等）。原因：腳本由另一個 agent session 啟動，那個 session 的環境變數不應傳給受測的 CLI。
  - 沒有使用 `--bare`。依 `--help`，`--bare` 只接受 API key，不讀取訂閱登入。
- 實際執行的指令（已移除敏感資料）：全部由 `poc/scripts/run-claude-headless.py` 在 `<testrepo>` 中啟動，提示由 stdin 傳入。`<testrepo>` 是第 2 節所記的測試 repo。第一次執行之後，腳本增加了紀錄欄位；審查後又調整了紀錄的寫法，並加上每次執行後（包含正常結束）的行程群組清理。啟動 CLI 的指令與旗標沒有改變，調整後沒有重新執行真實 CLI。

  ```text
  # PoC-04，三次
  claude -p --model claude-sonnet-5-5 --output-format stream-json --verbose --no-session-persistence --tools Read,Grep,Glob --strict-mcp-config --permission-mode dontAsk --safe-mode --json-schema <poc/poc-04/output.schema.json>

  # 記憶探測：預設
  claude -p --model claude-sonnet-5-5 --output-format stream-json --verbose --no-session-persistence --tools '' --strict-mcp-config --permission-mode dontAsk --include-hook-events

  # 記憶探測：加上 --safe-mode
  （同上，加上 --safe-mode）

  # 記憶探測：加上環境變數
  CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 （同「預設」）
  ```

- 結束碼：六次都是 0。沒有逾時（上限 180 秒），stderr 都是空的。
- 輸出的格式：stdout 是 JSONL 事件串流。第一個事件是 `system`／`init`，最後一個是 `result`。符合 `--json-schema` 的最終輸出在 `result` 事件的 `structured_output` 欄位；`result` 欄位另有同一份 JSON 的字串。
- 觀察與證據：

  | 次數 | 耗時 | 輸出符合格式 | 回報的模型 | 可用的工具（init 事件） | 權限模式（init 事件） | 實際的工具呼叫 | 測試 repo 是否未被修改 |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | 1 | 7.9 秒 | 是 | `claude-sonnet-5-5` | Glob、Grep、Read、StructuredOutput | `dontAsk` | Read ×2、StructuredOutput | 是 |
  | 2 | 7.8 秒 | 是 | `claude-sonnet-5-5` | 同上 | `dontAsk` | Read ×2、StructuredOutput | 是 |
  | 3 | 5.9 秒 | 是 | `claude-sonnet-5-5` | 同上 | `dontAsk` | Read ×2、StructuredOutput | 是 |

  - 格式由腳本依輸出格式定義檢查，並另外確認三個需求 ID 各出現一次。三次的判定內容相同（三項都是 `implemented`）。
  - 模型：指定值是 `claude-sonnet-5-5`。init 事件的 `model`、assistant 事件的 `model` 與 `result` 事件的 `modelUsage` 都只出現這個名稱。這些是 harness 回報的欄位，不是模型的自述。
  - 工具：`StructuredOutput` 不在 `--tools` 的清單中，是 `--json-schema` 帶來的。init 事件的 `mcp_servers` 是空的。
  - API key：init 事件的 `apiKeySource` 是 `none`；環境中沒有 `ANTHROPIC_API_KEY`；`claude auth status` 回報 `claude.ai` 登入。
  - 測試 repo：每次執行前後比對 HEAD、`git status`（含 untracked 與 ignored）與 `.git` 以外所有檔案的雜湊，都相同。
  - 每次實際載入的設定檔類別、可用的工具與使用的模型：
    - init 事件沒有列出載入了哪些設定檔或指示檔，所以「實際載入的設定檔」只能間接觀察，直接的清單記為未知。
    - 加上 `--safe-mode` 的執行：init 事件列出 19 個 skill、5 個 agent。其中只有記憶探測那一次要求輸出 hook 事件，那一次沒有 hook 事件。
    - 沒有 `--safe-mode` 的探測：init 事件列出 41 個 skill、10 個 agent，並出現 `SessionStart`、`UserPromptSubmit`、`Stop` 三種 hook 事件。由此推論：預設會載入使用者層級的設定與外掛。
    - 兩種情況下，init 事件的 `plugins` 都列出一個使用者安裝的外掛。加上 `--safe-mode` 時，這個外掛的 skill 與 agent 沒有出現在清單中。它是否完全沒有作用，尚未驗證。
  - headless 模式是否載入記憶，以及關閉的方法（NFR-11）：
    - 探測方法：在測試 repo 暫放一個含 canary 字串的 `CLAUDE.md`，要求模型回覆這個字串，沒有就回覆 `NONE`。模型沒有任何工具，不能自己讀檔。探測結束後已移除這個檔案。

      | 探測 | 回覆 | 結束碼 | 耗時 |
      | --- | --- | --- | --- |
      | 預設 | canary 字串 | 0 | 2.6 秒 |
      | `--safe-mode` | `NONE` | 0 | 2.5 秒 |
      | 兩個環境變數 | `NONE` | 0 | 2.3 秒 |

    - 結果：headless 模式預設會載入專案的 `CLAUDE.md`。`--safe-mode`，或 `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` 加上 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`，都能讓它不進入模型的上下文。
    - 兩種方法的差別：`--safe-mode` 同時停用 hook、外掛的 skill 與 agent；環境變數的做法保留它們（探測中仍有 hook 事件，skill 與 agent 的數量與預設相同）。
    - 文件依據：官方文件說明 `-p` 不加 `--bare` 時會載入 `CLAUDE.md` 與自動記憶，並列出上述兩個環境變數與 `autoMemoryEnabled` 設定（2026-11-15 查閱 code.claude.com 的 headless、memory 與 env-vars 頁面）。
    - `--include-hook-events` 沒有輸出指示檔載入的事件，所以不能用它列出載入了哪些指示檔。
    - 自動記憶的間接觀察：預設探測的 init 事件有 `memory_paths` 欄位（內含自動記憶的路徑）；另外兩次探測沒有這個欄位。這是 harness 回報的設定，不等於記憶內容有沒有進入模型的上下文。
- 結論（通過、部分通過、不通過）：Claude 的部分通過。三次輸出都符合格式；可用的工具只有讀取類工具與輸出用的 `StructuredOutput`；回報的模型與指定的相同；沒有使用 API key。記憶預設會載入，可以關閉。
- 對規格的影響：
  - 規格 PoC-04（仲裁者能否由 Flow Controller 自動啟動）：Claude 這一側可以。整項結論見結果總表與 Codex 的部分。
  - NFR-11：`claude -p` 的仲裁者可以關閉記憶。建議在能力矩陣記錄兩種關閉方法與各自的副作用。自動記憶是否確實關閉尚未單獨驗證（見下方限制）；驗證前，仲裁報告應註明這一點。
  - D-25、FR-22：模型、工具與權限模式的觀察值來自 init 與 `result` 事件。adapter 應從事件取得這些值，不從傳入的參數推定。
- 限制與未驗證事項：
  - 只在一台主機、一個模型上各執行三次。
  - 「工具確實是唯讀」的證據是 init 事件的工具清單、實際的工具呼叫紀錄與測試 repo 的前後比對。Read 類工具能否讀取測試 repo 以外的檔案，沒有測試。
  - canary 只驗證了專案層級的 `CLAUDE.md`。使用者層級的 `CLAUDE.md` 沒有觀察。自動記憶只有上述 `memory_paths` 的間接觀察；測試 repo 沒有自動記憶的內容，所以內容是否載入沒有驗證。兩個環境變數是一起設定的，不能分辨各自的效果。
  - 九次執行使用調整前的腳本：主行程結束後就比對測試 repo，沒有等候行程群組內可能剩餘的成員。
  - 逾時路徑沒有被真實 CLI 觸發。腳本的終止行為只以假的 CLI 做過離線測試（`poc/scripts/test-run-claude-headless.py`），這不是 CLI 能力的證據。
  - 執行時 CLI 寫入了測試 repo 以外的位置：更新使用者層級的狀態檔並留下備份，也為測試 repo 建立了一個專案資料夾，裡面只有一個空的記憶子目錄。`--no-session-persistence` 之下，這個資料夾裡沒有對話紀錄檔；其他位置沒有檢查。執行前向維護者詢問並取得同意時，說法是 CLI 會更新使用者層級的狀態檔；備份與專案資料夾是執行後才觀察到的，事前沒有逐項列出。
  - 事件串流中有 `rate_limit_event`，六次的 `status` 都是 `allowed`。它的欄位可作為 PoC-05 的線索，尚未列入 PoC-05 的結論。

#### Codex 的部分

- 執行日期與 CLI 版本：2026-11-15，`codex-cli 0.169.0`，macOS arm64。任務基準為 PR #17 合併後、經遠端核對的 `33598174b9f7573c58f5ec8ed3bea766f8171b43`。共用輸入與 schema 未修改。
- 與計畫的差異（旗標、步驟）：
  - 先讀 `codex --help`、`codex exec --help`、`codex login --help`、`codex login status --help`、`codex features --help` 與 `codex features list --help`，再使用對應指令。`exec` 沒有逾時旗標，也沒有獨立的 `--ask-for-approval` 選項；用外層 180 秒時限及 `-c approval_policy="never"`。
  - 只執行原訂三次；未另做記憶探測或重試。記憶採文件、設定與既有輸出的有界查核，沒有預設／關閉的內容對照測試。
  - 外層腳本只傳入 `HOME`、`PATH`、`LANG`、`LC_ALL`、`TMPDIR`、`SHELL` 中存在的變數。父 session 的其他服務 API-key 變數未傳入；每次確認子環境及 CLI 會另載入的 `<home>/.codex/.env` 沒有 API-key 變數。dotenv 只檢查變數名稱，不保存內容。
  - 每次以官方 `codex login status` 確認 `Logged in using ChatGPT`，並指定 ChatGPT 登入與 OpenAI provider。沒有複製、輸出認證檔或憑證，也沒有改用 API 計費。
  - 維護者事前同意七項測試 repo 外的寫入範圍：獨立 worktree 與 Git metadata、程式／報告、本機證據、CLI 狀態／快取、CLI helper 暫存及清理、官方 CLI 必要的訂閱憑證刷新、獨立發布檢查。這是允許範圍，不表示每一類均觀察到寫入。
- 實際執行的指令：`<repo>` 在本節代表 Codex 的獨立 worktree。外層呼叫如下；提示由固定檔案原樣經 stdin 傳入，cwd 為既有 `<testrepo>`。測試 repo 位置只由 `create-test-repo.sh --print-path` 取得，未執行建立或重建。

  ```text
  python3 -B <repo>/poc/scripts/run-codex-headless.py poc-04 --model gpt-6.1-sol --attempt 1
  python3 -B <repo>/poc/scripts/run-codex-headless.py poc-04 --model gpt-6.1-sol --attempt 2
  python3 -B <repo>/poc/scripts/run-codex-headless.py poc-04 --model gpt-6.1-sol --attempt 3

  # 每次實際啟動的 CLI argv 相同；<run> 是不同的本機結果目錄
  codex exec --model gpt-6.1-sol --sandbox read-only --json --color never \
    --ephemeral --ignore-user-config --ignore-rules --strict-config \
    -c 'forced_login_method="chatgpt"' -c 'model_provider="openai"' \
    -c 'approval_policy="never"' -c 'history.persistence="none"' \
    -c memories.use_memories=false -c memories.generate_memories=false \
    -c features.memories=false -c features.shell_snapshot=false \
    -c features.apps=false -c features.plugins=false -c features.hooks=false \
    -c features.multi_agent=false -c features.multi_agent_v2=false \
    -c 'web_search="disabled"' -c project_doc_max_bytes=0 \
    --output-schema <repo>/poc/poc-04/output.schema.json \
    --output-last-message <repo>/poc/local/codex/<run>/final.json -
  ```

- 結束碼與輸出格式：三次 CLI 與外層腳本均為 0，stderr 為空。stdout 是 JSONL；`thread.started`、`turn.started` 後有工作相關的 `command_execution` 與最終 `agent_message`，最後為 `turn.completed`。格式驗證分開檢查事件是否為 JSONL、最後訊息是否與保存的 JSON 相同、最終 JSON 是否符合共用 schema，以及三個需求 ID 是否各出現一次。
- 觀察與證據：

  | 次數 | 耗時（含清理） | 最終 JSON 符合格式 | 請求模型／回報模型 | harness 記錄的工作 | CLI 結束碼 | 清理後 repo 比對 |
  | --- | --- | --- | --- | --- | --- | --- |
  | 1 | 11,219 ms | 是 | `gpt-6.1-sol`／未知 | 一次 shell 讀取兩個指定檔案 | 0 | 相同 |
  | 2 | 13,480 ms | 是 | 同上 | 同上 | 0 | 相同 |
  | 3 | 11,584 ms | 是 | 同上 | 同上 | 0 | 相同 |

  - 三次實際 shell 指令都是 `/bin/zsh -lc 'cat docs/requirements.md src/wordcount.py'`，工具結束碼 0。回覆均判定三項需求為 `implemented`，檔案清單與讀取輸出相符。開始工作的證據是這些工作相關的呼叫與結果，不是 thread 建立或 CLI 結束碼。
  - 模型：JSONL 沒有模型欄位，stderr 也沒有模型名稱。因此 `model_reported=unknown`；指定值與模型清單不是實際執行模型的證據。
  - 設定：請求略過使用者 config 與 execpolicy rules，停用記憶、apps、plugins、hooks、協作工具與 web search，並不載入專案指示文字。五次都未因 `--strict-config` 拒絕參數；但輸出沒有設定載入清單，所以實際載入的類別仍為未知。這不證明系統／管理層、內建指示或其他來源全部停用。
  - 工具：事件證明讀檔 shell 可用；沒有完整工具 inventory，也沒有 MCP／外部服務全通道的權限證據。`--sandbox read-only` 的 help 只描述模型產生的 shell 指令，不能用它宣稱所有 MCP 或外部服務唯讀。PoC-06 另觀察到 patch 政策拒絕，仍不能泛化成所有通道的保證。
  - 每次正常結束後仍清理整個行程群組；確認不存在後，才比對 HEAD、含 ignored／untracked 的 Git status，以及含 `.git` 的檔案內容、模式、symlink 與空目錄雜湊。三次都相同。無法確認停止時，腳本不取 after snapshot，結果記為 `unconfirmed` 並以非零碼停止。
- headless 記憶與關閉方法（NFR-11）：
  - [官方設定文件](https://learn.chatgpt.com/docs/config-file/config-reference) 說明 `memories.use_memories=false` 停止注入既有記憶，`memories.generate_memories=false` 停止將新 thread 納入記憶生成；兩者文件預設均為 true。本機 `codex features list` 也回報 `memories` feature 為 true，但這不是本次 headless 已載入內容的證據。
  - 本次五個新 session 均傳入上述兩個 false，並加上 `features.memories=false`；不 resume／fork。`project_doc_max_bytes=0` 另用於抑制指示文件，不能與自動記憶混為一談。
  - `--ephemeral` 只承諾不保存 session rollout，並不單獨證明關閉記憶或全部狀態寫入，見[官方 CLI 文件](https://learn.chatgpt.com/docs/developer-commands?surface=cli)。
  - 未做 canary 或額外推論，未讀取原生記憶內容。預設 headless 是否實際注入內容、上述請求是否完全阻斷內容注入，本次輸出均不足以確認。NFR-11 的仲裁報告應保留這項限制。
- 結論：Codex 的部分為「部分通過」。三次 headless 與固定格式輸出已驗證，使用訂閱登入；實際模型、完整可用工具及載入設定仍有證據缺口，不能宣稱滿足所有通過條件。記憶結果依計畫只記錄，不單獨決定通過與否。
- 對規格的影響：PoC-04 的 Codex 仲裁者自動啟動資格尚未完整證實，暫保留人啟動；D-25 應容許觀察值未知。FR-22 的開始證據可取工作相關的工具執行，不能取 `thread.started`。NFR-11 應記錄關閉請求與尚未驗證的內容隔離，不把 `--ephemeral` 當作隔離保證。
- 限制與未驗證事項：
  - 單一主機、單一請求模型，三次皆未觸發逾時或用量上限。真實 CLI 的逾時／上限路徑未實測；離線假 CLI 測試只驗證外層腳本。
  - 依 zsh login shell 的行為推論（未實測），`/bin/zsh -lc …` 可能讀取 `<home>` 下的 zsh profile，因此環境白名單只約束 `codex` 行程本身，不能保證模型執行之 shell 指令的環境；這也是尚未列入「實際載入的設定」的來源。
  - 原始輸出與每次 m1-r2 記錄保存在 `poc/local/codex/`，不提交。五次執行使用的 runner SHA-256 為 `1db78fe354f67d5914370bf68a55f214aebfa7ad691c4f876afcdfd8f89a4b63`。執行後補上 stderr 拒絕解析，僅以既有五份輸出離線核對，沒有重跑 CLI；原始 record 保留，補充分析以相同 run_id 寫入 `analysis.json`。
  - CLI 外寫位置沒有做全主機追蹤；不能宣稱事前同意的清單已逐項發生或完全沒有其他變動。helper 暫存、SQLite／快取與必要憑證刷新不受模型 shell 的唯讀設定一併保證；憑證僅由官方 CLI 使用。
  - 指令 `--help`／版本與登入查詢在父 sandbox 內曾回報 PATH aliases 建立遭權限拒絕，但仍正常結束；正式五次由核准的執行環境啟動，沒有這項警告。

### PoC-05：用量上限的回報

- 執行日期與 CLI 版本：待填
- 與計畫的差異（旗標、步驟）：待填
- 實際執行的指令（已移除敏感資料）：待填
- 結束碼：待填
- 輸出的格式：待填
- 觀察與證據：待填
  - 文件描述的行為與來源：待填
  - M1 期間實際觸及上限的紀錄（沒有時填無）：待填
- 結論（通過、部分通過、不通過）：待填
- 對規格的影響：待填
- 限制與未驗證事項：待填

### PoC-06：headless 不卡在核准提示

讀檔工作是 `poc/poc-06/read-task.md`，寫檔嘗試是 `poc/poc-06/write-task.md`，輸出格式定義是 `poc/poc-06/output.schema.json`。兩家使用同一份。

#### Claude 的部分

- 執行日期與 CLI 版本：2026-11-15，Claude Code 2.1.312。
- 與計畫的差異（旗標、步驟）：
  - 寫檔嘗試執行了兩種設定，比計畫多一次。唯讀設定下模型沒有寫檔工具，不會產生需要核准的呼叫；所以另加一次「有 Write 工具、沒有人核准」的設定。維護者於 2026-11-15 在開發對話中同意。
  - `--help` 列出的 `--permission-mode` 選項中沒有 `default`；沒有指定模式時，init 事件回報的名稱是 `default`。
- 實際執行的指令（已移除敏感資料）：由同一個腳本在 `<testrepo>` 中啟動，提示由 stdin 傳入。

  ```text
  # 讀檔，以及唯讀設定下的寫檔嘗試（與 PoC-04 相同的唯讀設定）
  claude -p --model claude-sonnet-5-5 --output-format stream-json --verbose --no-session-persistence --tools Read,Grep,Glob --strict-mcp-config --permission-mode dontAsk --safe-mode --json-schema <poc/poc-06/output.schema.json>

  # 有 Write 工具、沒有人核准（不指定權限模式）
  claude -p --model claude-sonnet-5-5 --output-format stream-json --verbose --no-session-persistence --tools Read,Write --strict-mcp-config --safe-mode --json-schema <poc/poc-06/output.schema.json>
  ```

- 結束碼：三次都是 0。沒有逾時（上限 180 秒）。
- 輸出的格式：與 PoC-04 相同的 JSONL 事件串流；三次的 `structured_output` 都符合格式。被拒絕的工具呼叫列在 `result` 事件的 `permission_denials`。
- 觀察與證據：
  - 讀檔工作與寫檔嘗試各自的行為與耗時：

    | 案例 | 可用的工具與權限模式（init 事件） | 實際的工具呼叫 | `permission_denials` | 行為 | 結束碼 | 耗時 | 測試 repo 是否未被修改 |
    | --- | --- | --- | --- | --- | --- | --- | --- |
    | 讀檔 | Glob、Grep、Read、StructuredOutput；`dontAsk` | Read、StructuredOutput | 無 | 完成，不需人介入 | 0 | 4.0 秒 | 是 |
    | 寫檔，唯讀設定 | 同上 | StructuredOutput | 無 | 略過：沒有寫檔工具，模型沒有嘗試 | 0 | 3.3 秒 | 是 |
    | 寫檔，有 Write 工具、沒有人核准 | Read、StructuredOutput、Write；`default` | Write、StructuredOutput | Write 一筆 | 失敗後繼續：Write 被拒絕，模型回報後結束 | 0 | 4.5 秒 | 是 |

  - 讀檔的回覆內容與檔案相符（第一行與需求數量 3）。
  - 兩次寫檔嘗試之後，測試 repo 中都沒有 `poc-06-write-probe.txt`。
  - 模型的 `outcome` 分別是 `completed`、`not_available`、`denied`，與上表的觀察一致。判定依據是上表的事件欄位與 repo 比對，不是模型的回覆。
- 結論（通過、部分通過、不通過）：Claude 的部分通過。唯讀工作不需人介入即可完成；寫入的嘗試被拒絕或無法發起，指令都在數秒內結束，沒有等待。唯讀設定下沒有發生寫入的呼叫；「被拒絕」的證據來自另加的那一次。
- 對規格的影響：
  - 規格 PoC-06：`claude -p` 這個端點可以自動多輪。整項結論見結果總表與 Codex 的部分。
  - FR-22 與結果契約：寫入被拒絕時結束碼仍是 0，`result` 事件的 `is_error` 是 false。adapter 必須讀 `permission_denials` 才能知道有呼叫被拒絕，不能只看結束碼。
  - 契約 m1-r2 的 `error_class`：這種「被拒絕後正常結束」的情況，腳本目前記為 `none`，並在 `permissions_summary` 記錄被拒絕的工具。是否改記為 `approval_blocked`，留給 M2 定稿時決定。
- 限制與未驗證事項：
  - 每個案例只執行一次，使用一個模型。
  - 只測試了 Write 工具。Bash 等其他會寫入的工具、`--permission-prompts none`、`acceptEdits` 與 `auto` 模式都沒有測試。`dontAsk` 加上寫入工具的組合也沒有測試。
  - 「沒有人核准」的案例從腳本啟動，stdin 不是終端機。從終端機直接執行時的行為沒有測試。
  - 提示要求模型被拒絕後不再嘗試其他方法。模型自行改用其他途徑的情況沒有測試。

#### Codex 的部分

- 執行日期與 CLI 版本：2026-11-15，`codex-cli 0.169.0`；沿用 PoC-04 的訂閱登入、環境白名單與受控設定。
- 與計畫的差異：只執行讀檔一次、寫檔嘗試一次，沒有追加工具探測或重試。先用本機 harness 模型 metadata 與官方版本原始碼確認有 `apply_patch` 的候選路徑；這不是實際曝光的證明，是否真正發起仍以本次 harness 輸出判定。
- 實際執行的指令：

  ```text
  python3 -B <repo>/poc/scripts/run-codex-headless.py poc-06-read --model gpt-6.1-sol --attempt 1
  python3 -B <repo>/poc/scripts/run-codex-headless.py poc-06-write --model gpt-6.1-sol --attempt 1
  ```

  兩次實際 CLI argv 與 PoC-04 所列完全相同，只有 `--output-schema` 改為 `<repo>/poc/poc-06/output.schema.json`，`--output-last-message` 使用各自的 `<run>` 目錄。stdin 分別原樣使用 `poc/poc-06/read-task.md` 與 `write-task.md`；cwd 為 `<testrepo>`。
- 結束碼與格式：兩次 CLI 與當時的外層腳本皆為 0；都沒有逾時，最終 JSON 均符合共用 schema，且與 JSONL 最後的 `agent_message` 一致。兩次實際模型均未由 harness 回報，記為未知。
- 觀察與證據：

  | 案例 | harness 的工作／拒絕證據 | 行為 | CLI 結束碼 | 耗時（含清理） | 清理後 repo 比對 |
  | --- | --- | --- | --- | --- | --- |
  | 讀檔 | JSONL：一次 `command_execution`，執行 `cat docs/requirements.md`，工具結束碼 0 | 完成，無人介入 | 0 | 8,314 ms | 相同 |
  | 寫檔嘗試 | stderr：`codex_core::tools::router` 回報 patch 因唯讀／核准政策被拒；JSONL 無 `file_change` 或 shell 呼叫 | 寫入請求被拒後繼續回覆並結束，沒有等待 | 0 | 10,736 ms | 相同 |

  - 讀檔最終內容為 `# Requirements: wordcount | 3`，與檔案第一行及需求數量相符。
  - 寫檔 stderr 的 harness 診斷為 `patch rejected: writing is blocked by read-only sandbox; rejected by user approval settings`。同次 JSONL 只有 thread／turn 與 agent 訊息，沒有 `file_change` 或 shell 事件。測試 repo 沒有產生 `poc-06-write-probe.txt`；缺少 shell 事件不等於已證明沒有 shell 路徑。
  - [對應版本的 patch 權限程式](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/apply_patch.rs) 在 patch action 的安全判定回傳 Reject 時建立 `patch rejected` 錯誤。結合本次 harness router 診斷，判定有 patch 請求被政策拒絕；不是因模型回覆 `denied` 才判定，也不能因缺少 `file_change` 就記為工具不可用。這證明 harness 權限檢查的拒絕，未證明 OS 層真的收到寫入系統呼叫。
  - harness 診斷可觀察到一筆 patch 拒絕，未提供呼叫參數與目標路徑；不能獨立核實 patch 的精確內容，或把這一筆紀錄當成完整工具 inventory。模型聲稱使用 `apply_patch` 僅作輔助，不作單獨證據。
  - [同版 shell handler](https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/tools/handlers/unified_exec/exec_command.rs) 也能在啟動命令前攔截 patch，進入相同拒絕路徑。因此本次證據足以認定有寫入請求被拒，不能記為「只有模型自述／工具不可用」；但不足以獨立確認它是直接 `apply_patch`，或已遵守「不用 shell 繞道」。拒絕發生在檔案套用前；未驗證安裝 binary 與官方同版 tag 的位元一致性。
  - 原始 m1-r2 記錄只解析 JSONL，將寫檔案例的 `error_class` 記為 `none`。離線複核 stderr 後，在同 run_id 的補充分析記為 `approval_blocked`；原始記錄與輸出均保留。交付腳本已增加這項解析及離線測試，沒有因此再跑一次真實 CLI。
  - 兩次都先確認整個行程群組停止，再作與 PoC-04 相同的完整 repo 比對。沒有讀取／複製認證檔、改用 API key、重建測試 repo 或追加推論。
- 結論：Codex 的部分為「通過」。讀檔無須人介入；有 harness 證據的 patch 寫入請求遭唯讀／核准政策拒絕，CLI 隨後結束，repo 未變，符合計畫第 5 節的兩項通過條件。此判定依維護者的審查後決定修正，不代表新增執行或補足其他未驗證事項。
- 對規格的影響：PoC-06 的 Codex 端點在本次設定下符合不卡在核准提示的條件，自動多輪仍須滿足其他 PoC。FR-22 與 D-25 的 adapter 應同時收集 JSONL 與 stderr，分開記錄程序成功、工作開始與工具拒絕；CLI 結束碼 0 不等於寫入成功，也不能只等 `file_change` 才識別拒絕。
- 限制與未驗證事項：直接寫檔工具名稱、精確目標及不經 shell 的呼叫路徑未獨立確認。每個案例一次；未測互動終端機、其他 approval policy、其他寫入工具、外部 MCP／服務、shell 繞道或模型不遵守提示的情形。唯讀與核准設定同時存在，未分別量測各自效果；不宣稱全部通道技術唯讀。無法驗證的載入設定、模型及記憶限制同 PoC-04。

### PoC-13：投遞到 Claude Code 的既有 session

- 執行日期與 CLI 版本：待填
- 與計畫的差異（旗標、步驟）：待填
- 實際執行的指令（已移除敏感資料）：待填
- 結束碼：待填
- 輸出的格式：待填
- 觀察與證據：

  | 機制 | 啟用條件 | idle | 忙碌 | 已關閉 | 是否開始新的回合 | 失敗時的錯誤訊息 |
  | --- | --- | --- | --- | --- | --- | --- |
  | hooks 注入收件匣 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |
  | `asyncRewake` | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |
  | 自訂 Channels（選配） | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |

  - 開發用旗標在 `claude -p` 下是否有效：待填
- 結論（通過、部分通過、不通過）：待填
- 對規格的影響：待填
- 限制與未驗證事項：待填

### PoC-14：`codex queue` 投遞到既有 session

- 執行日期與 CLI 版本：待填
- 與計畫的差異（旗標、步驟）：待填
- 實際執行的指令（已移除敏感資料）：待填
- 結束碼：待填
- 輸出的格式：待填
- 觀察與證據：

  | session 狀態 | 結束碼 | 輸出 | 訊息是否送達 | 是否開始工作，以及判定方式 |
  | --- | --- | --- | --- | --- |
  | idle | 待填 | 待填 | 待填 | 待填 |
  | 忙碌 | 待填 | 待填 | 待填 | 待填 |
  | 未載入 | 待填 | 待填 | 待填 | 待填 |
  | 背景服務不存在 | 待填 | 待填 | 待填 | 待填 |

- 結論（通過、部分通過、不通過）：待填
- 對規格的影響：待填
- 限制與未驗證事項：待填

### PoC-15：跨廠商的唯讀審查

受審的變更、審查工作與輸出格式兩家使用同一份：

- 受審的變更：`poc/poc-15/change/` 的內容，由 `poc/scripts/prepare-poc-15-change.sh` 提交到測試 repo 的 `poc-15-change` 分支。base 是測試 repo 的初始 commit `6cc46aa598a7a63957485d087a787c39c386e0cc`，head 是 `d0c104fea561442870968015ea3de270460f97d0`。作者身分與時間固定；內容相同時，重建後的 commit ID 相同。
- 變更的內容：在 `docs/requirements.md` 新增 REQ-4、REQ-5，並在 `src/wordcount.py` 新增三個函式與對應的測試。埋入的三個已知問題列在 `poc/poc-15/known-issues.json`，這個檔案不交給審查方：

  | 類別 | 位置 | 問題 |
  | --- | --- | --- |
  | 邏輯錯誤 | `longest_line` | 違反 REQ-4：沒有換行結尾的最後一行被略過；只有一行且沒有換行時丟出例外。變更附的測試只測有換行結尾的輸入，測試會通過。 |
  | 安全問題 | `count_file` | 路徑直接串接進 shell 指令（命令注入）。 |
  | 超出需求範圍 | `word_frequencies` | 沒有任何需求對應。`docs/requirements.md` 寫明未列出的都不在範圍內。 |

- 審查工作：`poc/poc-15/review-task.md`。執行腳本把其中的 `{{BASE}}`、`{{HEAD}}`、`{{DIFF}}` 換成兩個 commit ID 與 `git diff` 的輸出，再由 stdin 傳入。
- 輸出格式：`poc/poc-15/output.schema.json`。每項發現有 `id`、`severity`、`requirement_relation`、`file`、`line`、`finding`、`evidence`；另有 `reviewed_base`、`reviewed_head`，以及整體的 `deviates_from_requirements`（對應 FR-36）。`severity` 與 `requirement_relation` 的值取自 dev-skills 0.1.0 的 review 報告格式；它與 engineering-workflow-core 的 findings 契約是否一致，尚未核對。這份格式沒有 disposition 欄位：這次的設計假設 disposition 由收到結果的一方填寫。

#### Claude 的部分

- 執行日期與 CLI 版本：2026-11-16，Claude Code 2.1.312。模型 `claude-sonnet-5-5`，維護者於 2026-11-16 在開發對話中確認。
- 與計畫的差異（旗標、步驟）：
  - 唯讀設定與 PoC-04 相同，沒有新的旗標。唯讀設定下沒有 Git 工具，審查方不能自己執行 `git diff`；所以 diff 全文放在輸入中，head 的檔案另可用讀取類工具讀取。
  - 每次啟動前，腳本多執行一次 `claude auth status --json`，確認登入方式是訂閱登入（`authMethod` 為 `claude.ai`、`apiProvider` 為 `firstParty`），不是時不啟動 CLI。這是 Issue #19 第 7 項的處置。`claude auth status --help` 列出 `--json` 與 `--text` 兩個選項。
  - 計畫的題目是審查「另一家產生的 diff」。這份 diff 是 Claude 製作的共用 fixture，所以這三次是 Claude 的 CLI 審查 Claude 製作的內容；跨廠商的方向由 Codex 的部分提供。
- 實際執行的指令（已移除敏感資料）：由 `poc/scripts/run-claude-headless.py poc-15` 在 `<testrepo>` 中啟動，提示由 stdin 傳入。三次相同。

  ```text
  claude -p --model claude-sonnet-5-5 --output-format stream-json --verbose --no-session-persistence --tools Read,Grep,Glob --strict-mcp-config --permission-mode dontAsk --safe-mode --json-schema <poc/poc-15/output.schema.json>
  ```

- 結束碼：三次都是 0。沒有逾時（上限 180 秒）。外層腳本耗時（不含清理）依序為 9.748、10.201、9.952 秒（四捨五入為 9.7、10.2、10.0 秒）。依 [PR20-Codex-E1 的留存紀錄補核對](https://github.com/jeffery777/agent-council/pull/20#issuecomment-6933823466)，CLI result 事件另回報 8.524、9.467、9.206 秒；兩者計時範圍不同，不可混用。
- 輸出的格式：與 PoC-04 相同的 JSONL 事件串流。三次的 `structured_output` 都符合格式；`reviewed_base` 與 `reviewed_head` 都與輸入的兩個 commit ID 相同；發現的 `id` 沒有重複。三次的輸入相同（提示與 diff 的雜湊相同）。
- 觀察與證據：

  | 審查方 | 次數 | 實際生效的權限（init 事件） | 審查的 commit | 輸出符合格式 | 找到的已知問題（邏輯、安全、超出範圍） | 審查後 repo 是否未被修改 |
  | --- | --- | --- | --- | --- | --- | --- |
  | `claude -p` | 1 | 工具：Glob、Grep、Read、StructuredOutput；模式 `dontAsk`；MCP server：無 | head `d0c104fe…`（base `6cc46aa5…`） | 是 | 三個都找到；發現共 5 項 | 是 |
  | `claude -p` | 2 | 同上 | 同上 | 是 | 三個都找到；發現共 5 項 | 是 |
  | `claude -p` | 3 | 同上 | 同上 | 是 | 三個都找到；發現共 6 項 | 是 |

  - 三個已知問題在三次輸出中的分類相同：
    - 邏輯錯誤：`MUST-FIX`、`in-scope`，指出 `longest_line` 略過沒有換行結尾的最後一行、違反 REQ-4，並指出沒有換行時會丟出例外。
    - 安全問題：`MUST-FIX`、`in-scope`，指出 `count_file` 以 `shell=True` 串接路徑，可被命令注入。
    - 超出需求範圍：`SCOPE-CREEP`、`no-requirement`，指出 `word_frequencies` 沒有需求對應，並引用需求文件的範圍聲明。
  - 「找到」的判定：腳本先比對發現中是否提到對應的函式名稱（超出範圍的那一項另要求標為 `no-requirement` 或 `SCOPE-CREEP`），再由 Writer（Claude 的主 session）讀過每項發現的文字確認；維護者本人沒有核對原始紀錄。三次、三個問題的兩種判定都一致。
  - 三次的 `deviates_from_requirements` 都是 `yes`。
  - 已知問題以外的發現：每次 2 至 3 項，例如 `count_file` 沒有明確以 UTF-8 讀檔、測試沒有涵蓋沒有換行結尾的輸入、`longest_line` 沒有處理 `\r\n`。其中沒有處理 `\r\n` 與沒有明確以 UTF-8 讀檔是 fixture 中確實存在、但沒有列入已知問題的缺陷。這些發現的嚴重度在各次之間不完全相同（例如測試不足那一項分別是 `NIT`、`SHOULD-FIX`、`NIT`）。
  - 實際的工具呼叫：三次都只有 `StructuredOutput`。審查方沒有使用讀取類工具，只依輸入中的 diff 作答。`permission_denials` 三次都是空的。
  - 模型：三次的 init 事件與 `result` 事件的用量都只回報 `claude-sonnet-5-5`，與指定的相同。
  - 登入：啟動前的查詢三次都是訂閱登入；init 事件的 `apiKeySource` 三次都是 `none`。
  - 開始工作的證據：每次有一個 assistant 事件與一次 `StructuredOutput` 呼叫，`result` 事件的 `num_turns` 是 2。
  - 每次結束後，腳本先確認行程群組已停止，再比對測試 repo 的 HEAD、`git status`（含被忽略的檔案）與 `.git` 以外所有檔案的雜湊。三次都相同。
  - 三次都有一個 `rate_limit_event`，狀態是 `allowed`。沒有觸及用量上限。
- 結論（通過、部分通過、不通過）：Claude 的部分通過。三次輸出都符合格式；有實際生效權限的證據（init 事件的工具清單與權限模式）；測試 repo 沒有被修改；超出需求範圍的變更三次都被指出。
- 對規格的影響：
  - 規格 PoC-15：`claude -p` 可以在唯讀設定下審查一份 diff 並回傳固定格式的結果。整項結論待 Codex 的部分。
  - FR-36：這三次中，「是否偏離需求」能以一個欄位回報，各項發現也都能以 `id`、`severity`、`requirement_relation` 表達。提議（待 M2 決定）：規格第 14 節關於結果格式如何對齊 findings 欄位的未決問題，可以沿用這組欄位，不另立分類；disposition 由接收方填寫。依據只有一份 diff、一個模型的三次執行。
  - 審查方在唯讀設定下拿不到 Git 工具。需要它自己取得 diff 時，要由啟動方把 diff 放進輸入，或另外提供唯讀的 Git 查詢方式。
  - 計畫要求每項發現有「穩定的 ID」，沒有定義穩定的範圍。這次採用的解讀是「單次輸出內唯一」，通過的判定也依這個解讀。維護者於 2026-11-16 在開發對話中確認這個解讀即可。發現的 `id` 只在單次輸出內穩定。同一個問題在三次中的編號不同（例如邏輯錯誤是 `F-003`、`F-003`、`F-002`）。需要跨輪次追蹤同一項發現時，不能直接比對 `id`。
  - M2 的未決事項（維護者於 2026-11-16 決定不在 PoC-15 加測）：審查進入下一輪時，同一項發現如何沿用同一個 ID。提議的做法是由接收方在第一輪後替每項發現配固定的 ID，下一輪的輸入附上這份清單，要求審查方逐項回報狀態，新發現另外編號。這個做法沒有測試。它併入規格第 14 節關於結果格式如何對齊 findings 欄位的未決問題。
- 給 engineering-workflow-core 的資訊（跨廠商 reviewer 路徑實際能提供的證據，計畫第 8 節）：以下只涵蓋 `claude -p`，Codex 的部分完成後補齊。
  - 可以取得的證據：
    - init 事件回報的工具清單、權限模式、MCP server 清單與模型。這些是 harness 回報的觀察值，不是從旗標推定的。
    - `result` 事件的 `permission_denials`（被拒絕的工具呼叫）與實際使用的模型。
    - 啟動方自己做的：受審的 base／head commit ID 與 diff 雜湊、審查前後的 repo 比對、行程群組已停止的確認。
  - 不能取得、或這次沒有取得的證據：
    - 工具清單證明沒有寫入類工具，不證明「所有通道都唯讀」。這三次沒有發生寫入的嘗試，所以沒有「寫入被拒絕」的觀察；那一項的證據在 PoC-06。
    - repo 比對偵測不到先改再還原的寫入，也不涵蓋測試 repo 以外的位置。
    - 審查方實際讀了哪些內容：這三次沒有任何讀取類工具的呼叫，審查只依據輸入中的 diff。
- 限制與未驗證事項：
  - 一份 diff、一個模型、三次。三個問題都不隱蔽；這個結果不代表對一般變更的審查品質。
  - 這三次不是跨廠商：diff 與審查方來自同一家。
  - 啟動 CLI 的工作階段環境中有一個指定 API 位址的變數；腳本的環境白名單沒有把它傳給 CLI。CLI 實際連線的位址沒有另外驗證。
  - 依 PR20-Codex-E1 的補核對，init 事件的 `plugins` 項目總數依序為 5、4、4；原報告特別提到的一個使用者安裝外掛不代表外掛總數只有一個。各外掛在 `--safe-mode` 下的實際作用仍未驗證。
  - 記憶與專案指示檔的關閉方法沿用 PoC-04 的結果（`--safe-mode`），這次沒有重測。
  - 沒有測試審查方在輸入之外自行讀檔或嘗試寫入的情況。
  - 已知問題清單放在測試 repo 之外，但與它在同一台主機上。這三次沒有任何讀取類工具的呼叫，所以沒有讀到它；審查方能讀取測試 repo 以外的路徑時，要記錄它實際讀了哪些內容。
  - 腳本對已知問題的初步比對只看函式名稱，會把談同一個函式的其他發現也算進去；表中的結果以 Writer 讀過發現文字後的判定為準。

#### Codex 的部分

- 執行日期與環境：2026-11-17，`codex-cli 0.169.0`，macOS arm64。任務實作基準是 `b7ca30284852f3465ffcdb6267a0e0f5cfc937b8`；規格 v0.6、M1 計畫 2026-11-10 草案；契約 m1-r2 加共用 review schema。請求模型 `gpt-6.1-sol`、reasoning effort `medium`；三次事件均未回報實際模型，記為未知。
- 事前條件與修正：
  - 維護者於開發對話同意最多三次、每次 180 秒、不自動重試，以及測試 repo 外的 worktree／Git metadata、指定腳本與報告、`poc/local/`、官方 CLI 必要狀態／快取／helper 暫存及訂閱憑證刷新。這是允許範圍，不代表已逐項觀察所有寫入。
  - 執行前先修正 Issue #19 第 1 項 PR18-SDS-01：Codex dotenv 只允許 `NO_PROXY`、`no_proxy`；其他名稱、憑證名稱與無法識別的非空非註解行均在任何 Git／CLI 命令前拒絕，不輸出或保存值。15 項離線測試通過，包含非憑證變數與 malformed 行的負向測試；這不證明 shell profile 或所有 CLI 設定來源都受控。
  - 先讀 `codex --help`、`codex exec --help`、`codex login --help` 與 `codex login status --help`，再使用對應命令。每輪以官方 CLI 確認 `Logged in using ChatGPT`；子環境僅保留 `HOME`、`PATH`、`LANG`、`LC_ALL`、`TMPDIR`、`SHELL` 中存在者，不傳 API-key 變數、不讀取或複製憑證。
- 測試 repo 與輸入：
  - 新 worktree 的 `poc/local/bootstrap/` 是固定於任務基準的獨立 clone。在其中執行原始 `create-test-repo.sh` 與 `prepare-poc-15-change.sh`，讓原腳本依其 common Git directory 產生本次專用測試 repo；未沿用或重建既有共用測試 repo。
  - 得到 base `6cc46aa598a7a63957485d087a787c39c386e0cc`、head `d0c104fea561442870968015ea3de270460f97d0`，與 Claude 相同；分支 `poc-15-change`，乾淨且無 remote。三個共用輸入／格式／已知問題檔案均未修改。
  - diff 固定用 `git diff --no-ext-diff --no-textconv --no-color <base> <head>`，再填入原模板三個佔位符。三輪保存的 prompt、diff 均逐位元相同；SHA-256：prompt `2d40a59e4ad899964f2531ed24a2e832f05639a5168ffd76af563ed3a027c0b0`、diff `be40eb31a073664637a96b90cea757e5c80be71081bc40bf5923390ada4c4f17`、schema `67c69dae74a494a704e493a1d522bf39406eef6955e0812a85211c6d16d62784`。
  - `known-issues.json` 不由 runner 讀取，也沒有放進測試 repo 或提示。三輪工具事件未顯示讀取該檔；第 1 輪列出測試 repo 檔案並匯入 `src/wordcount.py`，第 2、3 輪另讀需求、程式、測試與 README。這不是對所有隱含載入及檔案系統讀取的完整追蹤。
- 實際命令：外層依序執行下列命令的 `--attempt 1`、`2`、`3`，每輪成功才啟動下一輪；沒有額外模型探測或重試。`<repo>` 代表本次獨立 worktree，`<testrepo>` 是其 `poc/local/` 下的專用測試 repo。

  ```text
  python3 -B <repo>/poc/scripts/run-codex-headless.py poc-15 \
    --model gpt-6.1-sol --attempt <1|2|3> --timeout 180 --test-repo <testrepo>

  codex exec --model gpt-6.1-sol --sandbox read-only --json --color never \
    --ephemeral --ignore-user-config --ignore-rules --strict-config \
    -c 'forced_login_method="chatgpt"' -c 'model_provider="openai"' \
    -c 'approval_policy="never"' -c 'history.persistence="none"' \
    -c memories.use_memories=false -c memories.generate_memories=false \
    -c features.memories=false -c features.shell_snapshot=false \
    -c features.apps=false -c features.plugins=false -c features.hooks=false \
    -c features.multi_agent=false -c features.multi_agent_v2=false \
    -c 'web_search="disabled"' -c project_doc_max_bytes=0 \
    -c 'model_reasoning_effort="medium"' \
    --output-schema <repo>/poc/poc-15/output.schema.json \
    --output-last-message <repo>/poc/local/codex/<run>/final.json -
  ```

- 執行結果：

  | 次數 | 外層耗時（含清理） | CLI／外層結束碼 | 輸出符合格式 | 已知問題：邏輯／安全／超出範圍 | 實際觀察的權限與工具 | repo 前後比對 |
  | --- | --- | --- | --- | --- | --- | --- |
  | 1 | 56,351 ms | 0／0 | 是；共 6 項發現 | `F-002`／`F-001`／`F-006` | 2 次 shell；Git 建立暫存快取遭 `Operation not permitted` | 相同 |
  | 2 | 52,615 ms | 0／0 | 是；共 6 項發現 | `F-001`／`F-003`／`F-006` | 3 次 shell；相同快取拒絕；fixture 測試無可用暫存目錄 | 相同 |
  | 3 | 57,015 ms | 0／0 | 是；共 6 項發現 | `F-001`／`F-003`／`F-006` | 3 次 shell；相同快取拒絕 | 相同 |

  - 三次 JSONL 均有 `turn.completed`，最後 `agent_message` 與保存的最終 JSON 一致。原 schema 已被真實 `codex exec --output-schema` 接受；`reviewed_base`、`reviewed_head` 正確，finding ID 單次內唯一，`deviates_from_requirements` 均為 `yes`。CLI stderr 三次為空。
  - 已知問題判定由 Writer（Codex 主 session）逐項讀過 findings 與 evidence：每次都指出 REQ-4 的未換行末行被略過／單行拋出例外、`count_file` 的 shell 命令注入，以及 `word_frequencies` 沒有需求依據。前兩類均為 `MUST-FIX`／`in-scope`，範圍外功能均為 `SCOPE-CREEP`／`no-requirement`；不是僅以函式名稱比對。三個已知問題都找到 3／3 次，範圍偏離達至少兩次的條件。
  - 每次另指出 CRLF、路徑字面值與 UTF-8 解碼三項問題。CRLF 的錯誤結果可從三次工具輸出核對；沒有另建 ASCII 編碼環境驗證 UTF-8 那項推論，也未為其他發現追加模型執行。單次 ID 的限制與 Claude 部分相同，不保證跨輪沿用。
  - 開始工作的證據是各輪工作相關的 shell 呼叫、讀取或運算結果及具體 findings，不是 `thread.started` 或結束碼。第 1 輪以 mock 檢查注入參數，第 2 輪實際執行只輸出文字的注入案例；第 3 輪讀取程式並重現行長錯誤。
  - 第 2 輪內部有兩個 shell 結束碼 1：fixture 的 6 項測試有 1 項因不能建立暫存檔而 error；另一個最小重現以預期的 `ValueError` 結束。這些不是 CLI 逾時或重試，也不能把整套 fixture 測試記為通過。三次 Git 的快取拒絕訊息在工具輸出中，不在 CLI stderr。
  - 三次均未逾時，未觀察到用量上限；沒有觸發 PoC-05 的新增紀錄條件。耗時是外層從啟動到清理完成的量測；這次 JSONL 未回報可比的 CLI 自有耗時，不與 Claude 的任一計時欄混用。
- repo 前後證據：三輪都在確認整個行程群組停止後，才保存並比較 `before`、`after` 的 HEAD、完整 status（含 ignored／untracked）與 `tree_sha256`。六份快照的 HEAD 均為上述 head、status 均為空、tree SHA-256 均為 `ad5cee23db090c77ecde00544cb9893d3e7e142f072ed7d6617f84e698bd9133`。雜湊算法使用 runner 的 `repo_state()`，包含 `.git`、相對路徑、mode、檔案內容、symlink 與空目錄；留存紀錄可供另一方重算比對。事後主 session 重新計算也吻合。它仍不能偵測先改再還原或 repo 外的寫入。
- 實際生效權限與限制：
  - 本次可確認 shell 可用、列出的工具實際完成，以及暫存寫入遭拒／無可用暫存目錄。沒有受審檔案寫入成功的事件，也沒有 repo 變動；但 JSONL 沒有完整工具 inventory、完整權限模式或設定載入清單，因此不能由 `--sandbox read-only`、成功回覆或前後 hash 推定所有通道技術唯讀。上述失敗也沒有獨立隔離為單一權限控制的效果。
  - 關閉記憶、專案指示、rules、plugins、hooks、協作與 web search 都是啟動請求；這次沒有取得完整實際載入清單，也沒有追加 canary。`/bin/zsh -lc` 可能讀取 shell profile 的限制仍沿用 Issue #19 第 10 項；未擴修或宣稱已驗證。
  - 一份共用 fixture、單一請求模型、三次；不代表一般程式的審查品質。工具事件與快照沒有涵蓋主機所有檔案、先改再還原、原生載入或外部服務的完整行為。
- 結論：Codex 的部分為「部分通過」。三次跨廠商審查、原 schema 接受、已知問題辨識、開始工作及 repo 未變的紀錄均已取得；完整實際權限邊界仍未證實，因此不宣稱滿足全部通過條件，也不記整項 PoC-15 已通過。依計畫暫保留由人啟動該方向審查。
- 對規格與 engineering-workflow-core 的資訊：FR-36 的偏離欄位、逐項需求關係與單次唯一 ID 在此 fixture 可用；D-25 的 adapter 應同時保存 CLI stderr、工具結果、最終 JSON、固定 commit／輸入 hash 與 repo 前後證據，並容許實際模型／權限未知。這不是上游 reviewer 路徑資格或正式 findings 契約對齊的完成證明。
- 本機證據：三份原始 JSONL、stderr、最終 JSON、prompt、diff 與 m1-r2 record 保存在 `poc/local/codex/`，不進版控。執行使用的 runner SHA-256 為 `7aa41ead9b71fa63b866a8126b2945651f7a86af4f9a79cb51e0f9b197b458c6`；公開文字另作敏感資料檢查，不直接貼原始紀錄。
- 寫作核對：僅補本節、總表對應欄與獲准的 Claude 兩項證據補充；逐項對照本機事件、最終 findings 與前後 hash，保留觀察、推論與未知，不宣稱 STE 符合性。Lesson candidates：none。

## 5. 整合測試：兩家 CLI 的問答往返

做法與通過條件以計畫第 6 節為準。

- 執行日期與 CLI 版本：待填
- 與計畫的差異：待填
- 實際執行的指令（已移除敏感資料）：待填
- 結束碼：待填
- 輸出的格式：待填
- 正常路徑（兩至三輪，沒有人工轉貼）：待填
- 四種情況：

  | 情況 | 訊息是否遺失 | 觀察與證據 |
  | --- | --- | --- |
  | 接收方 idle | 待填 | 待填 |
  | 接收方忙碌 | 待填 | 待填 |
  | 接收方已關閉 | 待填 | 待填 |
  | MCP server 重啟後 | 待填 | 待填 |

- 同一則訊息重送是否產生第二個回覆：待填
- 結論（通過、部分通過、不通過）：待填
- 對規格的影響：待填
- 限制與未驗證事項：待填

## 6. 後續交付

依計畫第 8 節，M1 結束時補上：

1. 更新後的端點能力矩陣（規格第 5 節）：待填
2. 規格修訂清單（每個 PoC 結果對應要修改的條文）：待填
3. 給 engineering-workflow-core 的資訊（來自 PoC-15）：待填
