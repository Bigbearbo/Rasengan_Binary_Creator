# NVIDIA 小學數學教學研究員 × 共用記憶實施計劃（2026-11-12）

狀態：**作者研究方向修正 U + Codex 下一輪工作規格 A；尚未在使用者本機啟動 NVIDIA、尚未證實 SQLite 索引／真實工作流已實作**。

## 0. 使用者最新要求

「額，先國小的？你計劃一下，順便看看該用什麼記憶系統給他。」

**修正優先級：國小數學優先，國中／高中、AMC 競賽、模乘偏科題後移**。研究重心是極小神經網路和倉鼠 VM 如何從最初數字規律逐步學會數學，而非一開始就參加比賽。

兩條主線讀取**同一份 SLE 原始 0/1 數學題庫**，由教師/出題器離線從中立數學題意轉為 SLE。NN 和倉鼠 VM 不共用學生權重／程式／學習演算法，但共用題目 raw bits、答案語義、測試切分、詞典與版本。NVIDIA 是**外部教學研究員與候選審查員**，**不是第三個已經學會數學的學生**。Codex 實作/測試/驗收。

## 1. 國小數學課程：小題、逐步上升，不一開始灌進整張課表

| P階 | 內容 | 小模型題型與邊界 | 優先檢驗 |
|---|---|---|---|
| P0 | 讀數/原樣複製，零和一 | Echo、Zero、長度1–2位的合法 SLE 資料詞 | 已知詞/資料/控制位能否分清 |
| P1 | 計數、大小比較、增一 | 0–3 的比較、後繼；新算符尚無 SLE 合法 ID 時先產中立 AST，不得偷分配 | 未見值／詞碼增位 |
| P2 | 單位加減 | 1–3 bit 無進位加法、簡單減法，教師 oracle 先產答案，學生推論不得用外部計算器 | 正確率與跨例泛化 |
| P3 | 進位／借位 | 2–4 bit，刻意平衡 0→1 進位鏈、跨位借位、輸出寬度變化 | 真正學到進位還是記住題 |
| P4 | 乘除 | 2–4 bit 乘法、重複加法、整除與餘數 | 是否能組合 P2/P3 的知識 |
| P5 | 分數與簡單應用 | 分數等價、簡單分數加法、用結構化簡短題敘述數量關係 | 新數學資料型別與運算語義 |
| P6 | 混合運算／短型國小應用 | 2–3步混合運算，記錄作用域、括號或等效樹表示 | 跨算符組合、舊技能保持 |

**不應機械對應學校每一學年、也不要求一次完成所有階**。Codex 第一輪最小交付只需 P0/P1/P2 的**24個候選可辨識案例**（每階8例），其中至少8個是未見值/詞寬/缺詞典/不合法輸入的邊界。這些只是教學/測試種子，不是「24題已足夠訓練」的結論。各階可依掌握情況擴成大量獨立 train/test 題庫；樣本數由實驗測定。

### 教學輸入與原始語法界線

- 原始論文 Q1–Q3 的 Echo、初期無句號；Q6 才啟用 `110` END，n=1 的 `10` **可以是合法資料**；STOP 是 NN 外部輸出行為而非 SLE 語詞。
- 數字資料詞升階只在高位擴充，舊值與舊 ID 不重配。依分支語法 `k,n,offset,profile/version` 驗證，不隨機猜 bitstream 詞界。
- P1/P2 需要的新算符（比較、加減）在原 SLE 詞典**若尚未合法分配**，NVIDIA 必須列 `pending-vocabulary`、數學語義與需要哪種算子/參數/返回值，不得自創詞碼直接冒充當前協議。
- 保留 P030 作者提出的 `11110` 升階儀式作**獨立可選控制課程**，先不混入第一輪 P0–P2 的正式數學正確率；先有合法 framing 和 oracle 再測。
- 逐次教學可用短 bitstream，小模型不必讀自然語言國小應用題；數學文字→SLE 可由離線教師轉換，未來才另訓**輸入翻譯 NN** 和 **輸出翻譯 NN**。
- 語義題庫先建，再轉 SLE，**數學答案 oracle 只在教師側**。不能把 Codex、NVIDIA 的解題能力算作 NN/VM 自身學習效果。

## 2. NVIDIA 第一輪實際派工：取代 N-01 的國高中起跳設計

N-01-PRIMARY：先讀 `docs/ai_orchestration/NVIDIA_ELEMENTARY_MATH_MEMORY_20261112.md`，再讀 P031 共享 SLE 題庫章、原中文論文實際詞表、`experiments/spiral_parser/README.md`。輸入只給**已確認可公開的相關文件片段**。

任務 A：提出 P0/P1/P2 共 24 個中立數學教材案例，每個帶：
`case_id, level, skill, math_AST, canonical_result, difficulty_reason, required_sle_operators, sle_profile_if_known, code_status(validated/pending-vocabulary), edge_case, expected_generalization, source_ref, evidence_status`。
**不得自行編造「當前已定義的 SLE bitstream」；可建議新詞義，但必須標候選。**

任務 B：針對題庫驗收設計12個不易靠死記/猜零過關的反例（例如同值不同詞寬、進位/不進位邊界、同算符不同資料、非法句號），給出分層測試預期。

任務 C：Codex 在派工後將候選拿去執行 `TaskCase→SLE encode→decode→TaskCase` round-trip 和數學 oracle，**不通過不加入正式題庫**；寫清現有詞表與待定擴詞。避免要求 NVIDIA 自己在遠端「執行」沒有提供的本地程式。

**第一輪驗收**：候選有沒有實際可用的題型、缺哪些語法、錯誤例是否可測、Codex 改了幾處；不是 NVIDIA 回覆字數或用完 API 配額。第二輪才委派 P3/P4 的進位與乘除拆解。

## 3. 先檢查既有記憶研究；不另建一座孤島

已知研究來源：

- GitHub `docs/ai_orchestration/CODEX_MULTI_AGENT_MEMORY_PLAN_20261112.md` 已定 Markdown + Git 的共用記憶 MVP（`ai_orchestration/memory/INDEX.md` 等）與 `dispatch.py`。**這是規格，不可假定本機已實作。**
- Library `/AI研究記憶/README.md` 與 `記憶維護規程與台帳.md` 定義來源證據 L0、索引 L1、已核實 L2、當前工作 L3、假說 L4；原始碼與真正實測優先於摘要。**Library 主記憶不能自動同步到公開 GitHub**。
- GitHub `experiments/spiral_memory/research_archive_20261102/README.md` 是公開的、去識別化 SNL-MEM 平行研究副本；Library 原本 `/AI研究記憶/螺旋語記憶_平行實驗/` 是獨立影子研究。2026-11-02 v0.1 比較 **14 筆/15 組查詢/29項檢查 PASS**；UTF-8 Markdown 4,816 bytes、SNL 6,622 bytes（+37.5%），因此**不能先假設 SNL 較短或跨模型有優勢**。v0.2「AI 直接理解語法、程式輔助」尚未做跨模型盲測，不能當本地 worker 的可靠唯一記憶。

**第一版選型：Markdown + Git 為共享權威知識／人工可查證的決策層；本地 SQLite（可選 FTS5）管理任務、候選發現、呼叫日誌和全文索引；SNL-MEM 是唯讀影子比較，先不要讓它取代權威記憶。**

### 分層架構：避免 NVIDIA 每次重新讀全部研究，又避免不受控自我記憶

```text
[public repo, versioned] ai_orchestration/memory/
  INDEX.md                             # 超短入口；不搬整份歷史
  PROJECTS.md                          # 倉鼠 VM / 螺旋語題庫 / NN 分流
  projects/sle_math/current.md          # 現行 SLE 數學主線、P0–P2 進度
  projects/sle_math/grammar.md          # 已確認詞典/版本 + pending-vocabulary
  projects/sle_math/decisions.md        # 作者決策、被取代方案（引用 U 和 repo）
  projects/sle_math/evidence.md         # 原始檔、實跑測試及限制
  workers/nvidia.md                    # NVIDIA 角色/讀取/輸出規則，不放秘密

[local, private, excluded from Git] ai_orchestration/runtime/
  agent_memory.sqlite                   # 具體任務/執行/研究候選/來源與狀態
  reports/<task_id>.json                 # 模型候選輸出；未驗收不寫 confirmed
  work/<task_id>/                        # 短暫工作資料與不含秘密的備註
```

**NVIDIA 不是「自己需要一套獨立長期權威記憶」**：它每次被呼叫接收相同全體已確認的簡短 current、與任務相關的來源片段、最近**已審核**的同題工作結果，然後產生候選報告。Codex 才能合併進 shared memory。worker 的私有暫存心得可保存在 `runtime`，但不因模型自稱「我記住」就改 confirmed。

### 任務／記憶寫入契約（單一作者，避免串改）

`tasks`: `task_id, project, parent_task_id, model_id, task_kind, context_refs, context_hashes, created_at, status, attempts, usage, updated_at`。

`findings`: `finding_id, task_id, claim, evidence_ref, status(candidate/accepted/rejected/superseded), source_type, reviewer, reviewed_at, replaces, depends_on`。

`runs`: `run_id, task_id, attempt, model_id, prompt_hash, response_path, success, elapsed_ms, input_tokens, output_tokens, rate_limit_event`。

每條長期**重要知識**需可追溯 `topic, statement, scope/profile, status, source_type(U/F/T/A/E), source_ref, updated_at, replaces/depends_on`；不確定時保留 hypothesis，不能自動升 confirmed。

`memory_handoff(task)` 的最小讀取次序：
1. 永久規則 `AGENTS.md` + `workers/nvidia.md`（短）
2. `INDEX.md` + 指定 project `current.md` + `grammar.md`（適用才給）
3. 按 `task.context_refs` 和候選關鍵字（SQLite FTS5）取**最多5–8則已核對相關證據**，連同版本/來源；需要時才擴原檔
4. 引入此 task 最近的已審查結果或失敗反例；禁止未審核候選透過 retrieval 當「真相」寫入系統指令
5. 模型輸出 JSON（若模型不能強制 JSON 仍由 Codex validate），Codex 執行驗證並提議更新記憶。

這是**檢索後重建上下文**，不是依賴 OpenRouter 端永久保存對話。不要每次把昨日數百則對話與不相關的 Git diff 全部塞進 prompt。

### 整理、去重、過時與安全

- 每次經 Codex 驗收的有效發現即更新對應 `current/grammar/evidence`，在 SQLite 留 `finding_id + reviewer + repo_sha`；待驗候選在當地 `runtime`，不可自動把 NVIDIA 想法宣告作者原意。
- 同題已有任務先查最近 accepted/rejected 與 input hash，避免每日重做相同分析；按新版本/新題庫重新開工時保留 supersedes 關係。
- 每一批約20–50個**已完成**任務，做一次記憶整理：壓縮 current、封存已驗證報告的簡短結論及原始引用、標記過時版本，絕不直接刪除原始 T/U 證據。不要排死每小時重摘要；由累積量/變更觸發。
- 記憶區分**公開 Git 可以放的去敏研究結論**與**私有 Library、聊天、原始 ZIP、API key 和模型回覆**。不能把全部 ChatGPT Library 同步入公開 repo，也不能把私人或機密原文送免費 OpenRouter endpoint。worker 輸入要限定允許路徑、大小、版本，切掉 .env/私有秘密。
- OpenRouter `:free` 目前帳號額度依條件可達 1,000 requests/day、20 requests/min；失敗計次。參考 https://openrouter.ai/collections/free-models/；不可把「每人有 1,000 次」解讀成每個模型/agent 各有一次獨立額度。先查 `GET /api/v1/key` 的 daily remaining（回應絕不輸出 key），避免服務過載。
- 不要為 NVIDIA 實作全新向量資料庫、外部記憶 SaaS、跨模型神奇同步；初期幾百份任務 Markdown + SQLite 本機全文檢索通常足夠。資料量及實際 query accuracy 變大後再考慮 embeddings。

## 4. 記憶系統的平行競賽（可做但不可延誤教學主線）

以同一批已審核 SLE 數學研究事實與任務，事先封存約 20–30 組回答問題及來源要求，A/B：
- M0：每次只給相同當輪原始材料，無長期記憶；
- M1：短 Markdown INDEX + 關聯檔，人工指定 context_refs；
- M2：M1 + SQLite FTS5 按需檢索與已驗收 findings；
- M3：SNL-MEM 影子副本＋同等索引/來源/上下文預算（若使用者之後要繼續試）。

看**答案正確率、來源/版本引用正確率、是否錯把已取代結論當有效、漏答率、送入 token 總數、實際時間、失敗題**，同一模型、同一任務、不同隨機種子/提示順序；不能把 SNL 大小或程式 29/29 PASS 當已證明會更擅長長期研究。先做 M1/M2，再做 M3。

## 5. Codex 下一輪實際交付順序

1. 本機盤點：檢查 NVIDIA adapter、API 及其 model ID 是否已在設定（只說有無）、查 `ai_orchestration/memory` 是否已有檔案與 Git 未提交變更；**不得臆測它尚未存在，也不得覆寫**。
2. 建立或沿用上面6個簡短 public memory 檔；只初始化**可公開、已核實**的 P030/P031 來源與工作狀態，引用 Git commit，不搬私人 Library。
3. SQLite `runtime` 的 schema + 用最小 mock worker 驗證「同 task 重啟→讀同一狀態」、「candidate 不當 confirmed」、「來源 SHA 更改後標待複查」、「同一 task 不重複派工」及關聯查詢。要真的跑 tests；不能只有設計文件。
4. 模型可用且授權時發送 N-01-PRIMARY，收到候選，再依 P031/原 SLE 詞典建立 P0/P1/P2 的小型 SLE 題庫 seed 與語義 round-trip。
5. Codex 發表逐項結果：派工實際 request 次數/模型 ID/測試結果、每階通過數、候選拒絕理由、記憶讀取多少 bytes/token、下一輪 N-02 計劃；對未實作明說。
6. 之後才讓 NVIDIA 寫 P3/P4 教材，再擴充國中、高中、模乘專題與神經翻譯網路；普通 binary 強對照仍是獨立研究。

**[更新]** NVIDIA 首輪先做國小 P0–P2；記憶採用 Markdown+Git 主知識、SQLite 本地檢索/歷程、SNL-MEM 影子測試。
**[取代]** N-01 首輪直接派 24 個國高中題型與對 NVIDIA另建孤立的大型記憶系統。
**[原因]** 現有 SLE/NN/VM 的數學入門仍需逐階定義，已有私有/公開記憶分層研究與 Markdown對照，且有限測試沒有證明 SNL 已比 Markdown 經濟/可靠。
**[狀態]** 課程與架構規格已擬定；實際本機 runtime、API、SQLite/M1/M2和學生模型成績待 Codex 實測。
