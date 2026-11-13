# SLE AE1：無關第三詞 c 的平衡教學（實際NN訓練，2026-11-13）

**事前主門檻 FAIL。** 在補充高位元教材中，將無關第三資料詞 c 從原本全為1，改成 8題c0／8題c1，沒有穩定解決新位元組合複製的上下文依賴問題。Seed101通過、Seed202失敗；不能挑seed101冒稱整批成功。

## 固定來源與唯一改動

- 事前 Git freeze `95832cc2063b318ea7d5bd7a94b9d8ec71d3428b`，**先發布，再跑新optimizer**。基於 PR #44 真正head `dc73a3175ec487da7e064dbbcb804031ee5fe6d8`，PR #40 真權重，且舊 PR44 c1-only 對照使用原始凍結checkpoint（新control更新0）。
- 唯一變因：原注入的16筆 `r=2,a=0..3,b=24,25,28,29,c=1,d=0`，僅將8筆無關 c 由1改0；每個a、每個b的 c0/c1 均各2筆。120筆繼承教材不變，其中96個唯一raw Q、24重複；新教材136次呈現／112唯一raw Q。答案teacher-target stream、總1408 target/epoch不變；但兩臂 raw Q 不相同。
- profile `SLE-AE1-n5-v1`，Q39=`01+010+3-bit-r+0+4*(5-bit-value+0)+111100`；普通ID0..29，END30/UP31保留；回答首r個6-bit詞，最後由神經網路自行輸出外部S。未變更 SLE 解析器／詞典或倉鼠 VM。
- 兩個**新訓練**小模型 seed101、202，160輸入raw one-hot → 64tanh → 3 logits(0/1/S)，各10499參數，L80 cap32；Adam .003，batch64，100 epochs，各2200 updates（合計4400）、合計281600 targets，訓練前向dense MAC **2,937,651,200**（反傳/optimizer不算）。
- teacher train：繼承120+注入16，a0..3，b24/25/28/29；val a4,b26/27,c0/1；test a5,b26/27,c0/1。未見b26/27注入，但是研究員先前在PR42/44看過相關範圍，**不能當研究者盲測**。
- 事前 primary gate：**每個**seed新學生c0 val+test四題要比舊對照至少多2題，且新c1 val+test四題最多比舊對照少1題；兩seed全過才整體PASS。不能事後延長、換seed或挑checkpoint。

## 真正測得的完整輸出

| seed | 舊對照 c0 | 新平衡c0 | 舊對照c1 | 新平衡c1 | gate |
|---|---:|---:|---:|---:|---|
|101|0/4|**2/4**|4/4|4/4|PASS|
|202|0/4|**0/4**|3/4|**1/4**|FAIL|
|兩seed合計|0/8|2/8|7/8|5/8|**FAIL**|

兩個新學生均在直接教過的高位元組合 c0、c1 各16/16；低詞base train/val/test分別48/48、12/12、12/12，舊高詞r2 36/36保留。r1不應受b改變但新模型為10/12、11/12，舊對照皆12/12。

**非預註冊、不可作勝利門檻的c2探索：** 在 b26/27、a0..5、c2 共12題上，兩個舊對照均0/12，兩個新學生反而**各12/12**。這個現象有趣，但c2和相關數值已被本輪觀察，不能進一步宣稱真正學會上下文不變的通用複製規則。c0 fail和c2 success並存，反而說明強烈的上下文局部依賴仍待解釋。

## 原生01錯答及來源界線

seed202新模型，合法r2,a5,b26,d0：
- c0 Q `010100100001010110100000000000000111100`，預期 `001010110100S`，實際 `001010101000S`；
- c1 Q `010100100001010110100000010000000111100`，預期仍 `001010110100S`，實際 `001010110010S`。

T：`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python run.py gate` 事前PASS；單次 `python run.py train` 真正PyTorch訓練4400更新；`OPENBLAS_NUM_THREADS=1 python verify_numpy.py` 不import Torch/runner，重載真F32權重，重新解析原生raw Q與答案、重算**752/752**個自由生成完整01 bit字串及**8624/8624**逐步forward，統計和SHA一致。總正式評估8624 forward、89,965,568 dense MAC。全部752筆完整Q/預期/實際/失敗、六份來源與新checkpoint、可執行runner及獨立驗證器在另交付ZIP中；ZIP重新解壓後全檔 SHA256SUMS、gate、752/752 replay均PASS。

**ZIP SHA256：** `c28b58b11977bb8bccd99352dc099f65aefefccfe0f86a12abd44a5d9aae6c0b`。
`run.py` SHA256 `41cf9d8115ef8a249d4ef64ac173c46761b471dd7a9284c5661ca197fdc70e18`；
`PREREGISTRATION.json` SHA256 `84bb8900dbc55dc4b4b226de089ebdce532f3bdb8e187e58c26b3191965e78a9`；
`raw_cases.jsonl` SHA256 `e91630fe7d0142d9f981e17d079687dfc19f7ebc542ee9df6cc881a2f0565a8d`。
**Git 已公開字節核對一致的正式 `run.py`、原始 `PREREGISTRATION.json`、獨立 `verify_numpy.py`、`frozen_inputs/parent_course.json`、事前凍結與結果；但不含六份訓練前後 checkpoint 或原始raw ZIP，單憑git clone仍不能重播本輪全部神經推論。** 事前manifest的 `source_SHA_note` 曾規劃要上傳來源權重，實際沒有上傳到Git；完整權重保存在已驗SHA的伴隨ZIP，不能把未實現的出版計畫稱為已完成。

U：使用者要求真正01小網路學習／泛化、受控課程；F：PR40、44真checkpoint及P030～P035原證據；T：本輪PyTorch真訓練及獨立NumPy重播；A：c均衡減少shortcut仍是未被本次兩seed支持為穩定修復的候選。UR1、F2、數學題庫PR5均不同研究線，這不是數學學習或SLE優於普通二進位之證據。

NVIDIA actual calls0（無已授權可直接用的reviewer worker）、本機Codex0、Gemini0；未用LLM替學生算答案。下棒：交獨立checkpoint驗證／Codex做唯讀審核；未來需以全親代課程中c平衡（而不只16筆注入）、新seed及事前真正未看過的值/上下文另開實驗，不能再以本輪已查看的c0/c1/c2調參。Draft、不合併。
