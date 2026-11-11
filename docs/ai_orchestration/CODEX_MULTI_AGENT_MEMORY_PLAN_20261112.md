# Codex × OpenRouter NVIDIA × Gemini：共用記憶與任務調度實作計畫

日期：2026-11-12  
狀態：**待 Codex 實作、尚未驗收**  
主要執行環境：使用者的 Windows 電腦、已安裝的 Codex。  
既有倉庫：`Bigbearbo/Rasengan_Binary_Creator`；這是**公開倉庫**，不得放入秘密、私人對話、未授權資料。

## 0. 任務與權限界線

目標不是把三個模型的所有歷史塞進每次提示，而是讓 Codex 能以「索引 → 相關專案現況 → 必要證據」按需載入，並以單一任務格式呼叫 OpenRouter 上的 NVIDIA 模型與 Gemini，最後留下可重現的工作回報。

- **Codex**：本機協調者、程式編輯者、測試者、Git 整合者。Codex 保留最終合併、更新已驗證記憶的權限。
- **OpenRouter/NVIDIA worker**：低成本候選分析、資料整理、程式靜態審查；實際模型 ID 必須由本機配置指定，不得猜測。
- **Gemini worker**：第二意見、文件與結果獨立審查；優先調用使用者已可操作的 Gemini CLI／官方 API，而非脆弱的瀏覽器點擊。
- 兩個 worker 初版皆**唯讀**專案，僅回傳結構化報告；不自行改檔、推送、合併或派生無限任務。
- 原有倉鼠世界、螺旋語的程式／測試／`AGENTS.md` 規則繼續有效；不得重做已驗證成果。

## 1. 分階段交付

### P0 — 盤點與最小基準（第一步）

1. Codex 盤點 Windows 環境：Codex 工作目錄、`gemini` CLI 可用性、Python 版本、OpenRouter endpoint/API key **是否存在**（只輸出有無，不輸出值）、Git 分支與已有未提交變更。
2. 確認倉庫下是否已存在相同用途的任務系統／記憶檔；有則沿用或遷移，禁止直接覆寫。
3. 用三個小型、可比的既有專案任務建立**未使用共用記憶**基準：成功率、用時、API 用量（若可取得）、輸入上下文大小、重複解釋次數、人工介入。
4. 交付 `docs/ai_orchestration/ENV_AUDIT.md`（僅記錄非敏感環境事實與缺口）。

### P1 — 共用記憶 MVP

建議初期只用 Markdown + Git，**不先開發獨立向量資料庫**：

```text
ai_orchestration/
  README.md
  memory/
    INDEX.md                    # 入口索引，應保持簡短
    PROJECTS.md                 # 專案清單 / 入口
    projects/<project>/
      current.md                # 當前事實、下一步、版本
      decisions.md              # 決策與被取代方案
      evidence.md               # 可追溯測試/文件連結
  schemas/task.schema.json
  schemas/report.schema.json
  dispatch.py                   # 單一調度入口；先支援 dry-run
  workers/openrouter_worker.py
  workers/gemini_worker.py
  tests/
  samples/
  runtime/                      # 本機狀態、任務佇列，不納入 Git
```

- `AGENTS.md` 是 Codex 入口；`GEMINI.md` 可作 Gemini CLI 入口。它們只指向**同一份** `memory/INDEX.md`，不複製大段專案背景。
- 記憶條目至少記錄：`id`、`topic`、`status`（confirmed / hypothesis / superseded）、`source_type`（user / repo / test / model）、`source_ref`、`updated_at`、必要時 `replaces`。
- **區分原作者設計、AI 建議、可重現測試與待驗假說**。不可把 worker 的自信語氣當成證據；推翻時保留舊結論及變更理由。
- 公開 Git 僅放非敏感的索引、規則、公開研究摘要；使用者的私人 Library、聊天、API 回應或包含機密的完整任務資料留在本機私有空間，未經篩選不得同步。
- 先從既有 `docs/spiral_language_research_index.md` 建立一個小型範例索引，不複製全倉庫文檔；ChatGPT Library 不是本機自動同步來源，若要同步另列專項。

### P2 — 任務封包與模型適配器

統一輸入契約（JSON Schema + 範例任務）：

```json
{
  "task_id": "EXAMPLE-001",
  "project": "spiral_language",
  "goal": "Review parser test coverage",
  "context_refs": ["ai_orchestration/memory/INDEX.md", "docs/spiral_language_research_index.md"],
  "constraints": ["read_only", "do_not_modify_existing_tests"],
  "acceptance": ["Name evidence files", "State unknowns"],
  "worker": "nvidia",
  "budget": {"max_input_chars": 12000, "max_output_tokens": 1500}
}
```

統一輸出包含：`task_id`、`worker`、`model_id`、`status`、`summary`、`findings[]`、`evidence_refs[]`、`unknowns[]`、`usage`（可缺省）、`elapsed_ms`、`recommended_next_step`。worker 回答是**候選報告**，不是指令。

- OpenRouter adapter 透過 HTTPS API，憑證只從本機環境變數或祕密管理載入，不寫到 log/命令列參數/倉庫；對 429、超時、無額度提供明確錯誤與有限重試。
- Gemini adapter 使用已驗證存在的 Gemini CLI 非互動呼叫或官方 API，先確認實際 CLI 版本及輸出格式；不假設每台機器相同。
- `dispatch.py` 只讀取 task 中指定的檔案，應檢查路徑是否在允許根目錄、限制 bytes/token、去重；禁止未經授權掃描整台電腦、擅讀 .env 或憑證。
- 對 prompt injection 採資料／指令隔離；外部檔案與 worker 回覆不能提高權限。
- 獨立審查場景：Gemini 先看原始題目和證據，再看 NVIDIA 報告，避免前一模型污染第二判斷；同意不代表證實。
- 不要把 API key、私人對話或研究未公開內容傳至免費模型；未授權不進行外部實際呼叫。

### P3 — 調度與驗收

- 建立本機單一 dispatch 入口，先依 worker 明確派遣；之後才考慮按成本/成功率自動路由。
- 若有平行 worker，僅並行唯讀分析；**寫入、Git commit、記憶合併必須序列化**。可用本機 SQLite/WAL 管理 queue、attempt、lease；資料庫不納入公開 Git。
- 任務狀態：`queued → running → reviewed → accepted/rejected`；失敗可重試但需保留 attempt，不得把未驗收結果直接寫入 confirmed memory。
- 完成至少三種測試：mock worker 與 schema、缺少金鑰/CLI 時降級、記憶變更衝突及錯誤回滾。實際 OpenRouter/Gemini smoke test 需用戶既有授權與可用額度。
- 使用**相同任務集**比較原始 Codex 單獨工作與共享記憶／分工方案，統計任務成功率、人工修正、牆鐘時間、輸入/輸出 token（若可得）、實付費用、錯誤率。不預設共用記憶必然省錢。
- 完成一項 end-to-end demo：`任務建立 → NVIDIA 靜態分析 → Gemini 獨立檢查 → Codex 人/程式驗證 → 產生報告 → 提議記憶更新`。先不允許自動合併未驗證結論。

## 2. 本輪 Codex 執行順序（請優先完成最小可用版）

1. 讀本計畫與根目錄 `AGENTS.md`，檢查已有未合併 PR／分支與同名程式，勿踩到其他進行中作業。
2. 完成 P0 環境盤點與安全前置檢查。
3. 建立 P1 的最小索引（可以只含 Spiral Language 一個非敏感專案）和資料契約。
4. 做 P2 的 mock/dry-run 最小閉環；能呼叫外部服務時再加 live mode。優先 Python 標準庫，避免為小工具加入重型依賴。
5. 執行測試並回報逐檔變更、命令、實際結果、未解決問題及後續建議。**沒有跑過不能寫 PASS**。
6. 在本 Issue 留下進度與 commit/PR 連結；若環境或憑證不可用，完成可離線驗證部分，不能以臆測代替實測。

## 3. 第一版完成定義（DoD）

- 原有程式、測試與工作分支未被破壞。
- 同一任務可以派給 mock NVIDIA / mock Gemini，符合 JSON Schema，並且兩者共用索引、只按 refs 讀取相關記憶。
- 缺少實際 API key、模型 ID、Gemini CLI 時有清楚錯誤／跳過標記，不洩露機密。
- 至少完成一個可重現 demo 和自動測試，紀錄實測結果；live 能否成功須另列。
- Codex 可從 `AGENTS.md` 找到本計畫，並從本 Issue 知道首要任務。
- 不宣稱本 Issue 自動喚醒本機 Codex：本機 Codex 須先同步倉庫並開啟工作，或由已配置的自動化環境讀取任務。

## 4. 非目標

本次不改動 Hamster VM 或 Spiral Language 協議，不把私人 ChatGPT Library 全量上傳公開 Git，不建立多模型自動改碼／自動推送權限，不保證 OpenRouter NVIDIA 的特定免費端點一定長期可用。

## 5. [更新] 2026-11-12：Gemini CLI 個人訂閱與第三方調度限制（本節優先於前文 P0/P2 的舊建議）

[更新] **不要再預設 Google AI Pro/Ultra 的舊 Gemini CLI 個人 Google 登入可用，亦不得讓 Codex 在消費者訂閱底下包裝 `agy -p` 作為第三方模型後端。** Codex 自動分工給 Gemini 時，優先使用使用者自行配置且允許的 **Google AI Studio / Gemini API Key** 或合規企業 API；Gemini CLI/Antigravity CLI 留作使用者獨立操作或其他允許的直接工作流程。OpenRouter/NVIDIA 仍使用其 API Key；Codex 可以以 ChatGPT 訂閱登入。

[取代] 前文「Gemini worker 優先調用使用者已可操作的 Gemini CLI」與「Google 訂閱可直接當程式化第三方 worker」的隱含假設。**舊的 `workers/gemini_worker.py` 名稱可保留，但內部應以合法 Gemini API adapter 為準**，不能直接 subprocess 包裝個人 Antigravity CLI。

[原因] Google 2026-06-18 起停用 Gemini CLI 個人免費／Google AI Pro／Ultra 的舊 Google 登入服務，改推 Antigravity CLI。Google Antigravity FAQ 表明，在消費者方案下，將 Antigravity CLI headless 包入第三方 coding agent/application 並不受支援；要整合第三方 coding agent，Google 建議 Gemini API Key。

[狀態] 官方政策來源已核對；Codex 本機環境是否配置 Gemini API Key 尚未知，不能聲稱 live worker 已可執行。此限制不影響 mock/dry-run MVP。

官方來源：
- https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals
- https://antigravity.google/docs/faq
- https://antigravity.google/docs/cli/overview/
- https://antigravity.google/docs/cli/headless/
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan

Codex 工作順序同步修正：先盤點本機 Gemini API 是否已獲合法授權及免費/付費額度；未配置便做 mock，**不要為繞過限制而自動抽取 Google 個人帳號 token、操控 UI 假裝人工、輪轉帳號**。Antigravity 可另列「人類直接使用」模式，不納入 MVP 的第三方 subprocess worker。
