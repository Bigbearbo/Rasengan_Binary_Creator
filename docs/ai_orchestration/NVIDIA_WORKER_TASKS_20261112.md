# NVIDIA／Nemotron 研究員派工規則（2026-11-12）

狀態：**立即採用的調度規格與首輪任務包；未聲稱 OpenRouter live 呼叫已成功或 Codex 本機 worker 已存在**。

## 目的與角色

作者確認本機 Codex 已配置可用的 OpenRouter NVIDIA Agent，依使用者敘述每日約有 1,000 次呼叫可用，但 Codex 經常忘了指派任務。本文件解決「忘了派工」而不是鼓勵無差別消耗全部額度。

- **Codex**：協調、讀寫本機檔、執行程式和測試、整合結果、Git commit，決定是否採納。
- **NVIDIA Nemotron（設定以本機為準）**：積極執行**範圍明確的獨立推理、數學題型規劃、SLE 靜態審查、反例構造、競爭編碼設計、失敗結果研判**。只給它必要的可公開 GitHub 檔案片段和無敏感信息的任務封包。
- **Gemini（若已配置合規 API）**：重要結論的獨立第二意見，優先先給它原始材料再呈現 NVIDIA 評論，以免意見先行污染。
- 資源：OpenRouter 的 `:free` 端點在符合帳號條件時最高 1,000 次/日、20 次/分鐘，**不假設本機實際每日可用數必定 1,000**，上限是帳號級、失敗也會消耗次數；對429應停並記錄，不可用多帳號規避。以 provider/API 的真實 rate limit 與可用額度為準。
- 免費 Nemotron 3 Ultra 目前可接受 tool calling，但 OpenRouter 端點**不支援強制 `response_format`**；Python adapter 必須自行檢查 JSON schema，失敗時有限次重試/降級，不把不合法回覆標成已驗收。
- 相關來源：https://openrouter.ai/collections/free-models/ ; https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b:free

## 必須執行的 Codex 開工路由（非後台自動化）

當 Codex 開始一個具有實質研究內容的工作回合（SLE、倉鼠 VM、題庫、實驗、編碼比較、神經網路訓練），應**先檢查** OpenRouter NVIDIA worker 是否已在本機可用：
1. 讀 `AGENTS.md`、本檔與 `CODEX_MULTI_AGENT_MEMORY_PLAN_20261112.md`，辨認本次任務可以切出的**一項不依賴寫入權限的有價值子任務**。
2. 若 worker + key + 額度 + 使用授權可用，**優先委派至少一項** NVIDIA 子任務，而不是默默由 Codex 重複分析所有問題。若不適合（例如只有機械性格式修正）可不派，但需簡短記理由。
3. 若 worker / key / live API 不可用，**繼續 Codex 本地主要工作**，記 `nvidia_status=skipped_unavailable`、缺的是哪個能力；不准假稱已派，也不准因沒有 NVIDIA 阻塞題庫實作。
4. 發送有限的文件片段與輸出要求，等待帶有來源位置、反例、可驗證預期的報告；Codex 再實際跑測試、審查、接受或駁回。
5. 在本次研究報告增加一小段 **NVIDIA 派工帳**：`task_id / model_id / status (accepted, rejected, skipped, failure) / 呼叫次數 / 成本或額度 / 重要反例 / Codex 驗證方式`。每輪都要留下痕跡，讓「忘記」有可觀察指標。

**不要製造假工作來湊 1,000 次**。初期可限制單項研究子任務 1–3 次請求、每次最多數千字的資料切片；可視實際成功率調整。應以「每個請求產生多少可採納、可驗證的成果」為效率，而不以用滿額度為目標。

## 2026-11-12 優先順序更新：P032 第一，國小題庫第二（U）

作者最新指定 P032 神經網路容量／教學比例研究為最高優先。本文件 N-01 的「目前最高優先」是**前一個工作順序**，已被此決策暫時覆蓋；國小數學題庫工作保留、順延，不取消。

- 立即派 NVIDIA 一個 P032 唯讀審查任務：閱讀實際 P030 報告（PR #4）與 P032 事前計劃，尋找 holdout split 太小、位置編碼、重複訓練題和 H72/H128 比較偏差。交付可重現反例及處理建議；不要只提出「再增加參數」。
- Codex 同步**真正執行** P032 診斷與受控訓練，不等待 NVIDIA 記憶系統落地，也不因外部 worker 不可用而停止。
- 等 P032 初步結果有記錄後，N-01 國小教材設計接續進行；兩學生依然共用 SLE 題庫。

## 首批分工任務：按需要取用，優先前兩項

### N-01｜國小數學入門 → SLE 題庫語義需求（目前最高優先，U 修正）

**必讀**：[NVIDIA_ELEMENTARY_MATH_MEMORY_20261112.md](NVIDIA_ELEMENTARY_MATH_MEMORY_20261112.md)。作者要求先教國小，不從國高中起跳；兩學生（NN/倉鼠 VM）共用**同一份 SLE raw bitstream 題庫**。對照 plain binary 是另行實驗，不是 VM 的教材。

第一輪：由 NVIDIA 設計 P0/P1/P2 共 24 個短、可驗證的**候選題**，包含讀數、Echo、Zero、比較／後繼、無進位簡單加減及必要邊界；附中立 AST、教師正解、需要的 SLE 語義、已分配/待分配詞碼狀態、舊知識保留、未見數字泛化期待。若原有 SLE 尚無合法比較/加法算子，只標 `pending-vocabulary`，**不得猜造正式原詞碼**。**24題只作實作和測試種子，不是夠訓練的資料量**。

第二輪在第一輪合法性驗收後才提出 P3/P4 進位、借位、乘除；國中高中、AMC、模乘延後。Codex 執行 `TaskCase→SLE→TaskCase` 和教師 oracle、真實 NN/VM 互通驗收，不得將 NVIDIA 會算數冒充學生學會數學。

**記憶規則**：NVIDIA 每次取得相關已確認的 `INDEX/current/grammar/evidence` 資料片段與 task refs，不要每天重新灌整份歷史。候選放本機 SQLite/JSON 任務日誌，Codex 確認後才提升為共用 Markdown confirmed；SNL-MEM 與 Markdown 同題等預算平行比較，不能預設 SNL 更好。見新增的記憶研究計劃。

### N-02｜SLE parser 對抗性檢查（立即優先，P030/P031）

**輸入**：
- `experiments/spiral_parser/spiral_tree_nodes_v06.py` 的 `highwater` / `encode_operator` / `decode_operator`；
- `docs/ai_orchestration/P030_小模型連續學習與句號保留_教學計劃_20261112.md` 中 n=1 無 END、n=2 END=`110`、n=4 `11110` 儀式與角色約束。
  
**任務**：提出 20 個**可重現的反例候選**，涵蓋 `k/n/offset/version`，跨階擴位不重分配 ID、算符與資料分支角色、最高已分配編號刪除後保持、句號啟用時機、`11110` 同詞形不同 role 的合法/非法組合、`STOP` 是輸出行為而非 SLE 語詞。
  
**交付**：每例 `case_id, prior_profile, raw_bits, expected_parse_or_error, reason, relevant_code_ref`。若不確定，標 `hypothesis` 不得假稱實測 bug。**Codex 必須用原程式 oracle 或新增獨立測試判定，不能直接把 NVIDIA 反例列表當 PASS/FAIL。**

### N-03｜強對照的壓縮普通二進位

**輸入**：P031「3A」；相同數學 `TaskCase` 分布；已知的 SLE 詞寬/版本 profile。
  
**任務**：設計 `Flat-Fixed`、`Flat-SelfDelimited`、`Flat-Frequency`、`Flat-Hierarchical` 的可解碼方案，並提供精確 bit 分解、詞典/更新成本、短碼與混合變長的反例。不得用 ASCII 無謂填充讓普通二進位變弱。保留「高位擴張、舊 ID 不重配」的公平能力。
  
**交付**：編碼定義 + 12 個小測例 + 可逆性論證/失敗條件；Codex 獨立實作 round-trip，不能接受純宣稱。

### N-04｜n=4 `11110` 升階儀式實驗審查

**輸入**：P030「六之二」。
  
**任務**：設計 R0/R1/R2/R3 的等預算訓練分組，找出「只是全部回答同一字串」「模型忘記舊技能」「profile 資訊外洩」等捷徑，提出事前驗收指標與消融實驗。不可在算術普通題裡把 `11110` 同時當一般算符和 END。
  
**交付**：分組表、failure modes、至少 6 條檢查可否真正提升泛化的判準；Codex 運行實驗後再回饋 NVIDIA 分析結果。

### N-05｜Codex 新程式／測試失敗的獨立審查（持續）

**輸入**：限定的公開程式 diff、特定失敗測試輸出、實際測試命令、預期行為。先移除任何 API keys/私人路徑/對話。
  
**任務**：指出潛在邏輯錯誤、測試漏洞、錯誤歸因；要給觸發條件與最小反例，而不是籠統讚美/挑文風。
  
**交付**：有優先級的 `findings`、每個的證據位置與可重現驗證方法；Codex 驗證後判定 `accepted/rejected`。

## 有效任務封包

```json
{
  "task_id": "N-02-001",
  "worker": "nvidia",
  "project": "spiral_language",
  "goal": "Identify candidate edge cases in versioned SLE parsing, no code edits",
  "context_refs": [
    "experiments/spiral_parser/spiral_tree_nodes_v06.py",
    "docs/ai_orchestration/P030_小模型連續學習與句號保留_教學計劃_20261112.md"
  ],
  "constraints": [
    "read_only",
    "public_repo_context_only",
    "no_secrets",
    "cite_exact_file_and_location",
    "do_not_claim_tests_were_run"
  ],
  "acceptance": [
    "Return at least 10 distinctive testable cases",
    "State assumptions and unknowns",
    "Distinguish confirmed evidence from speculation"
  ],
  "budget": {
    "max_calls": 2,
    "max_input_chars": 18000,
    "max_output_tokens": 2500
  }
}
```

**輸出驗收**：`task_id / worker / model_id / findings / evidence_refs / unknowns / recommended_next_step / usage / elapsed_ms`。JSON 必須由本機 coordinator 自行校驗；必要時用有限次格式修正。任何 worker 報告不是代碼修正、測試通過或已更新記憶的證據。

## 隱私及操作安全

- 公開 Git 倉庫中可公開的 P030/P031、測試原始碼可給免費端點審查；**不可**把私人 ChatGPT Library、使用者原始對話記錄、`.env`、未公開 ZIP 內容、憑證或本機私有資料送免費 NVIDIA 端點。該免費端點明確限制機密與個人資料：https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b:free。
- 不為了湊額度而重試 429、改帳號、隱瞞需要付費或繞開 API 限制。
- 這只是**下一次本機 Codex 啟動時**的派工規則和可執行任務清單；在此 GitHub 更新步驟中沒有直接連線使用者本機 OpenRouter，也沒有真的呼叫 NVIDIA Agent。

