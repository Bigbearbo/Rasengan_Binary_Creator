# Full-domain numeric8 神經課程：核准閘門唯讀稽核（2026-11-13）

本工作單是 **事前完整性與核准邊界** 的一個獨立檢查，**不是神經訓練**；只新增本目錄，不改 Codex #24 正式執行程式、資料、模型或 checkpoint。以 Git 可見 HEAD 為準，Codex 的正式訓練仍須由授權協調者另行明確核准。

## 唯一檢查變因與預設判準

**問題**：在正式訓練前，「呼叫者給定的正確 manifest SHA256 ＋ 任意符合格式的 40 位元組十六進位 commit」是否被執行器獨立確認為**已經核准、且該 commit 綁定同一份 manifest**？

**事前判準**：逐項檢查 frozen input digest、runner source 註冊值和正式 `execute` / `validate_inputs` 原始碼。若檢查器只驗證呼叫者提供的摘要與 commit 字串格式，**不能**宣稱核准已由程式驗證；不得藉此自動啟動正式實驗。此項只測授權邊界，不以 NN 分數為衡量指標。

## U / F / T / A

U：作者要求獨立小型神經網路研究，先凍結合法 SLE 01 位元、教材、seed、split、預算與執行閘門；與 VM 核心／語法解析分開。

F：截至本輪讀取，[Codex PR #24](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/24) 仍是 draft，HEAD `1d6ab7fd7fbb75525886226b10b1ed0a744ad9ff`，base `codex/early-mix-matched-20261113`。完整題域已由 Codex 凍結、內部前置工程審查 PASS，但無正式 NN 訓練結果。**不得**把 PR #19 AE1 訓練、#20 混教或 #21 前綴唯讀診斷冒充本實驗成果。

F：PR #24 既有的 `manifest.json` SHA256 `dabdb58a54ffd93afa350f19876a53550bcfcfd6de9b5199ee8b3b26d2b8d658`，runner SHA256 `9c100c1b8d6e9d1aca4acfc0f5a89d1a4716286aae1fae44692cbb5d0066593e`，原始 bundle `inputs.zip` SHA256 `82e5c9240d7217ee88399a4c84068715a336db208a3f942e956cb930fa5c4271`。這是上游 frozen 證據，**本輪沒有下載 ZIP 做整包重驗**。

F：讀取 `run_full_domain.py`：`execute()` 的 commit 守衛是 `re.fullmatch(r"[0-9a-f]{40}", commit or "")`，`validate_inputs()` 以 `file_sha(path) == approved` 比對**由呼叫者自行輸入**的 approved 值；接著 `run_seed()` 執行訓練。執行器說明 `Coordinator supplied, runner performs no Git operations`。該設計**有意把真正的核准工作交給外部協調者**，因此不是 Codex 偷跑的證據。

T：此輪 GitHub 原始碼靜態核對辨識「commit 只查格式，沒有在這個 runner 內與 manifest 綁定」；本機獨立 Python synthetic 守衛測試 `PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_audit`：**4/4 PASS**，退出 0；不讀神經網路權重、不跑正式原始 runner。raw bits 的長度和內容另以獨立 Python 算式確認。公開 `audit.py` 可在取得**完整 PR #24 工作樹**後讀取實際 ZIP、查每個成員的 SHA256 和位元組長度；**本輪未聲稱該完整實檔稽核已執行**。

A：[更新] `approved-manifest-sha` 的**完整性比對**與「作者／協調者已核准正式訓練」是兩個不同命題。[取代] 不得因已公開 commit 與 manifest，或有人能填入參數，就認定授權成立。[原因] runner 尚無獨立批准紀錄或 Git commit→manifest 存在／內容驗證；外部工作流仍須自行負責。[狀態] 原始碼可觀察的局部檢查結論信心高，其他本機／外部核准渠道是否已核准未知。

## 凍結教材、資源與合法 profile（本輪不變更）

PR #24 獨立 numeric `nop2/nd8`，非 AE1、UR1；資料欄 8 個資訊位允許 0..255 全部值；兩種操作 Echo 與 Neg，Neg 僅翻轉資料資訊位，不翻 SLE 語法尾 0。Q 為 `01`＋兩位 operator 資訊＋`0`＋八位 data 資訊＋`0`（14 bits）；A 為八位 data 結果＋`0`，最後由小網路自行輸出外部 `S`。

範例 raw bits：Echo(5) `Q=01000000001010`、`A=000001010S`；Neg(5) `Q=01010000001010`、`A=111110100S`。兩個都是合法 profile 詞尾 0，而非對非法碼任意補齊。

split 為 **train＝512 完整 Q（Echo×256 + Neg×256）；val＝0、test＝0、無未見題域**。seeds `101,202,303`，每 seed 40 個 epoch 的置換序已凍結，每 epoch 512 題 × 10 targets＝5120 更新；最大 204800 更新／seed，最大訓練 dense MAC 1,427,251,200／seed，H69/L23/3453 參數、Adam lr=.003。僅 seed101 預定一份完整獨立重播。訓練停止需兩個連續 epoch 在 **兩操作各256/256整串含S**，或40 epoch上限；若沒有達標也必須記失敗。即使通過，只能聲稱有限已教域的學熟，不是heldout泛化或無界演算法。

本輪新增 **0** 神經 forward、**0** optimizer updates、**0** NN training MAC、**0** Codex 代理執行。NVIDIA/OpenRouter 本環境沒有可呼叫的連接器：`nvidia_status=skipped_unavailable`，實際 0 次；Gemini 0 次。這不否定 Codex #24 自身記錄的另一回合 NVIDIA 公開唯讀審查。

## 重現和進一步驗收

從 **完整 PR #24 內容的本機 checkout**（或本分支 checkout）：

```sh
cd experiments/spiral_neural/20261113_scheduled_full_domain_gate
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_audit
PYTHONDONTWRITEBYTECODE=1 python audit.py --repo-root ../../.. --out local-gate-audit.json
```

第二行是完整公開資料的驗證入口（需要 `inputs.zip`；首次在有完整 Git 工作樹的環境執行，輸出 `local-gate-audit.json` 需自行保存並核查），**不是本輪已完成 T**。不使用 `--execute`，也不寫 Codex #24 的已凍結文件。不要把程式自動報告的 `status=frozen_inputs_verified__external_approval_unverified` 誤看成批准。

若要真正核准 Codex 的一次正式運算，下一 owner（**作者／指定協調者，不是本排程自行批准**）應保留一筆不可含糊的核准紀錄：核准者、批准時間、被批准的 `manifest SHA256`、上游 HEAD commit、執行器與輸出目錄及成本上限。再由 Codex 驗證該筆核准指向 Git 上的正確內容，並由明確授權的執行者啟動凍結課程。不得以本 audit 或任意40字元字串代替核准。

## 修改檔案

本分支只新增 `experiments/spiral_neural/20261113_scheduled_full_domain_gate/{audit.py,test_audit.py,README.md}`，不觸動已凍結輸入、訓練程式、Pro/Codex 的分支，也不合併 PR。上游後續若改變 HEAD，需重新核對該 SHA，而不能默默套用這次的靜態判斷。
