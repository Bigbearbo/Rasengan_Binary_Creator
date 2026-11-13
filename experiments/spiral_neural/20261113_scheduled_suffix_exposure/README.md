# AE1 相關／無關詞暴露控制：小型神經網路實測（2026-11-13）

本目錄是**獨立的新小網路實驗**，不修改 Codex PR #26、Pro AE1/UR1、P030–P035 或倉鼠 VM。承接 PR #27 的「固定前兩詞查表能完全忽略後兩詞」反例，這輪研究的唯一變因是：**訓練期第 3/4 個無關資料詞，是每個前兩詞組合固定，還是每輪換一組**。測試實際神經網路對無關後綴的敏感性；不是再跑 PR #27 的查表。

## 來源與凍結

U（使用者）：要求 SLE 原生 01 輸入／輸出、可驗證的小網路課程／泛化，先保留嚴格來源、成本與失敗。
F（已發表）：Codex [AE1 參數課程 PR #26](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/26) head `7213cce112a8411b13dc128c49f9e88acfc9d65f`，其 `SLE-AE1-n5-v1` 合法題目，900 組已教前兩詞配對、三學生已教 r1/r2 各 900/900；[獨立查表反例 PR #27](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/27)。PR #19 的較長 r3/r4 失敗也屬既有 F，不視為本次 T。

**本次凍結：** Git 先提交獨立 `experiment.py`（commit `77aa3df2339990f5c171f57bbf87c937eb6329c5`）與 `preregistered_protocol.json`（commit `b657e76d890903e571c4d5a6e151db5d457612c2`），然後才執行正式訓練。原程式本機 SHA256 `a21edd9453215edc553206aff364599e650594505bc2a0af5f006c41049c57c8`，事前 protocol SHA256 `27cd6874fa08054a58e7cd9d02b2aebee879136eb71d440eaf17a885dec01b2f`。這是研究事前固定，不冒稱 UR1 的額外 manifest 核准；無 Pro/Codex 工作分支改動。沒有新外部模型、教師 LLM 或 oracle 參與學生求解。

## 單一變因、素材、資源

固定合法 SLE：`01 + 010 + r的3資訊位+0 + 四個(5資訊位+0)資料詞 + END111100`，共 39 raw bits；答案是前 r 個完整六位詞，再由學生輸出**外部** STOP=`S`。r∈{1,2}，普通詞 ID 0..29，這不是 Neg 或 UR1 profile。示例：`010100010000000000000000000000000111100 → 000000S`（此字串由 `qbits()` 自動生成並通過格式檢驗，更多例見 `preregistered_protocol.json`）。

前兩詞取 0..5 的 36 組有序配對；以 `(a+b)%6` 分成 train24、val6、test6，無跨組洩漏。所有配對同時提供 r1/r2 題型。教師目標為所需答案的 0/1/S；forward 只看 raw Q 與其已生成／教師強制前綴，不看解析樹、答案函式、真實 STOP 位置或 test label。訓練不查看 val/test。

對照 A 固定後兩詞 `(c,d)=((7a+3b)%15,(5a+11b)%15)`；對照 B 每 epoch 讓 `(c+epoch)%15,(d+7epoch)%15`。所有其餘初始模型、前兩詞、任務、真答案、epoch、batch、隨機排列相同，並且每 seed 的初始權重 hash 完全相同。評估看 baseline、低詞域其他後綴，以及原訓練未出現過的高詞 ID15..29 後綴。後綴始終不影響正解。

模型：raw 01 one-hot 位置輸入 L80、tanh H64、輸出 0/1/S，**10,499 個權重／偏置參數**。各 seed 101、202 配對固定／改換，共四個學生。PyTorch Adam lr0.003、batch64、200epoch，每 epoch 480 teacher-target、每模型 1600 optimizer steps／96,000 target exposures，共 6400 steps／384,000 target exposures，理論 reference dense training MAC `384000×21056=8,085,504,000`（是每 target 等效估算，batch kernels 和 PyTorch 的真實運算成本未測）。原 P030 是逐 target、Adam birth-age correction，此處改為 PyTorch batched CE，**不能把與 PR #26 的差異歸因為後綴變因**。

## T：本輪真正執行

先跑 `python experiment.py selftest` 與 `python experiment.py prepare`，檢查格式／例題／模型參數／切分／課序摘要。凍結並寫 Git 後，正式 `python experiment.py train`，Python + NumPy2.3.5 + PyTorch2.10.0 CPU，四模型約 **6.33 秒**；完整原始結果在 `results.json`（含所有 train/val/test 三條後綴 regime 的模型自由生成序列及完整失敗例、hash、更新次數）。沒有再改超參數、seed、題庫或補訓。訓練器只保存成績與最終權重 hash；之後為封存權重做一次**相同凍結課序的 deterministic post-run replay/export**，四個最終權重 SHA 全部完全一致，並從輸出的 evaluation-only 模型權重重新生成全部 864 條保存的輸出，864/864 完全相同。此封存重播是證據保存，不是新增研究臂或新正確率；optimizer m/v 未封存，不能直接從最終權重繼續訓練。

| seed | 後綴訓練 | 已教 train（r1+r2） | val 高位新後綴 r2 | test 原後綴 r2 | test 高位新後綴 r2 |
|---|---|---:|---:|---:|---:|
|101|固定|48/48|6/6|5/6|4/6|
|101|每輪改換|48/48|6/6|6/6|6/6|
|202|固定|48/48|6/6|6/6|3/6|
|202|每輪改換|48/48|5/6|6/6|3/6|

所有 `test r1`（三個後綴條件）及全部測試 STOP 位置正確。高詞域後綴下，test r2 正確率固定 **7/12**，每輪變換 **9/12**；但 seed202 **3/6→3/6**、val 的 seed202 **6/6→5/6**，只有兩個 seed、六組獨立 test 配對，不能稱普遍提升。更關鍵的是：**無關後綴改變導致已教前兩詞之外的神經生成結果變化**，所以神經模型目前不能被視為已學會完全無視無關詞的一般規則。STOP 成功不是內容複製成功。

一個有代表性的失敗：seed202、變換後綴訓練、test 高位新後綴，raw Q=`010100100000000000010100100110100111100`；應答 `000000000010S`，實際 `000000000100S`。模型仍在正確位置停止，卻把第二個資料詞的內容寫錯。更多失敗及其 raw bits 見 `results.json`。

## 可重現命令與證據

此腳本的原固定輸出檔名使用 `/mnt/data/` 絕對路徑；下載到一般機器執行，需將這些路徑換為可寫入的輸出目錄（此項是可攜性限制）。**不需重新跑已完成 P030–P035**。

```sh
python experiment.py selftest
python experiment.py prepare
python experiment.py train
# 以上先固定 protocol/source，再正式執行；此處僅提供重現，不鼓勵任意追加seed或epoch。
```

封存包含 `results.json`，`checkpoint_export_results.json`、四個 `checkpoints/weights_seed*_*.json`（float32 原 bytes base64，inference-only），以及 `export_checkpoints.py`、`verify_checkpoints.py` 的重播／檢查來源。`verify_checkpoints.py` 重新 forward 864 次且全一致；請先檢查 JSON SHA及 source SHA。Git 的外部可見結果為本地實跑後公開，不冒充 Codex 或 NVIDIA。NVIDIA：沒有授權 OpenRouter live worker，calls=0、skipped_unavailable；Gemini calls=0。

## A：下一問題與限制

此有限 36 對、兩 seed、固定小網路、batch optimizer 的結果**不是 SLE 比普通二進位優越性、不是任意詞數、不是完整教材學會的證明**。`val/test` 在固定少數配對上重複使用；不可看本批分數再追加訓練稱盲測。下一 owner（小型 NN/Pro/Codex 協調）先獨立審查上述全部 checkpoint／split；若有新研究必要，**另外凍結**相同 pairs、seen/unseen 後綴下的擴大 seed 或等預算來源控制，或測 `r3/r4` 與前綴組合真的未見過的泛化，不能篡改本批原凍結。

U/F/T/A 如上分開；本 PR **Draft、不合併**，也不改 Pro/Codex 工作分支、私人聊天、倉鼠 VM 核心或語法詞典。
