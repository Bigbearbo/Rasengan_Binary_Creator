# AE1 r1→r2 前綴角色一致性：封存推論的分段核對（2026-11-13）

## 問題與來源

本輪選擇**不同於 PR #29「訓練期無關後綴暴露」**的單一問題：同一個合法四詞 SLE 問題，僅把指令參數從 r=1 切為 r=2，學生回答的第一個資料詞是否被擾動？若 r2 失敗，是第一詞、第二詞，還是 STOP？

U：使用者要求小型 NN 對原生 01 的可歸因學習、泛化與真實失敗例；不得重跑已完成 P030–P035、Codex PR #26/#28、Pro UR1。

F：既有 [PR #29](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/29) frozen head `dcabc3a65a4b9e7a50ab83ff8266b2c233d15000`；其 4 個真實訓練過的 10,499 參數 NN、完整 archived free-generation `results.json`，Git blob `7d87bfc417564c4af08892534d15b1b3af96e104`，profile 繼承 PR #26。**沒有重新訓練任何學生，也不載入/推論 checkpoint。**

實驗前先提交 `analysis.cjs` (commit `dee980832994943e96794277bbfa1de0f5e94402`) 和 `preregistered_protocol.json` (commit `1811d6fd6302e618aea2c11ccee1ca54a20f4c2c`)；實際 gate 的失敗與修正保存在 [GATE_FAILURE.md](GATE_FAILURE.md) 和 Git 歷史，沒有事後刪除。

## 格式、分割、預算

SLE-AE1-n5-v1：`01+010+r(3資訊bit+0)+四個(5資訊bit+0)資料詞+END111100`，Q 共39 raw bits；輸出前 r 個完整6-bit資料詞，接外部 STOP `S`。本輪在每個 `(a,b,c,d)` 複用原封存的 r1、r2 回答；兩道 Q 唯一改變 r，並不改教材。

先前學生 seed 101/202，兩種固定／變動訓練後綴，200 epoch，batch Adam(lr=0.003)，每學生1,600 optimizer steps、96,000 teacher-target exposures；train/val/test 先前用 `(a+b)%6` 切成24/6/6 組前兩詞。後綴 seen/changed_low/unseen_high 是先前的評估標籤，來源同一原生 SLE profile。原訓練總參考MAC 8,085,504,000（非本輪）；本輪新訓練、NN forward、訓練 MAC 全部 **0**。

**事前 gate**：只接受已凍結 Git blob、protocol SHA 和四個 model/seed key；檢查 864 份封存輸出、逐組原 exact／bits／STOP 計數、合法 Q 參數與資料範圍、無重複配對／切分混入。保存所有分段分類與錯誤 raw bits；不以觀察結果追加訓練。

## T：本輪真的執行的分析

使用 GitHub 連接器讀取原始封存，在本輪 JavaScript 執行環境中執行逐筆合法性驗證與配對統計，於 36 個 model/split/suffix 子組內全部 PASS。分析輸出在 [results.json](results.json)。Node CLI 實作已提交為 `analysis.cjs` 以便獨立重現，**本輪尚未在本機 Node 直接執行該檔案**，所以不宣稱 Node/平台完整重播已驗收。

**新發現一：分段錯誤局部化。**

| 統計 | 封存 r1/r2 配對評估 |
|---|---:|
| 記錄中的配對次數 | 432 |
| r1 整題正確 | 432/432 |
| r2 的第一個六位詞正確 | 432/432 |
| r2 第一詞與 r1 第一詞一致 | 432/432 |
| r2 整題正確 | 421/432 |
| r2 錯誤 | 11/432，全部只錯第二個資料詞 |
| 第二詞資訊位錯誤 | 22 bit（11次錯誤合計），尾端0錯誤0 |
| 第二詞錯誤時誤複製第一詞 | 6/11 次（其餘5次） |

例如 seed101/fixed 的 test/unseen_high：raw Q `010100100000000000010100100110100111100`，原 r2 正解 `000000000010S`，實際 `000000000100S`。停止與首詞都正確，只把第二詞 `000010` 錯成 `000100`。不能由此推斷具體神經內部因果或演算法。

**新發現二：原評估的 train suffix 標籤實際上是重複同題。** 原 `experiment.py` 中 `rows(which='train')` 不論呼叫者要求 `suffix_mode='changed_low'` 或 `'unseen_high'`，都從 train 分支取 epoch0 固定低後綴，不會使用 `eval_suffix()`。新 gate 初次因此正確拒絕 `train/unseen_high` 的資料 ID15..29 假設。對四學生、兩 r、兩替代標籤進行16次完整序列比對，全部確認 train 三個標籤的 Q、預測結果完全相同，suffix 值仍為0..14。此項**不影響 val/test 真實 high suffix 的結果**，但 `train/high` 分數不應當作獨立 OOD 後綴證據。

因 train 三標籤重複，432 配對次數包含192個同模型同輸入的重複配對；去除重複後為**240 個 model×題目配對情境**，其中 r1 240/240、r2 首詞240/240、r2 整串229/240。不能把432當作獨立樣本做顯著性檢驗。四個模型也不是432個獨立學生。

具體 test/high 的 r2 成績依序 seed101 fixed 4/6、varied6/6，seed202 fixed3/6、varied3/6；合併16/24。test/seen23/24、test/changed_low23/24、val/high23/24。所有失敗例分類與代表性 raw bits 在 `results.json`。

## 重現、修改及限制

新檔只有 `analysis.cjs`、`preregistered_protocol.json`、`GATE_FAILURE.md`、`results.json` 與本 README，**不覆寫 Codex/Pro 模型、題庫或 PR #29 的程式與 checkpoint**。無外部教師模型、Codex本機、NVIDIA/Gemini 呼叫；NVIDIA `calls=0, skipped_unavailable`（本執行環境無授權 worker 通道）。

在包含 PR #29 原封存的本分支目錄，可使用 Node 內建模組重現：
```sh
node experiments/spiral_neural/20261113_scheduled_ae1_cross_role_prefix/analysis.cjs selftest
node experiments/spiral_neural/20261113_scheduled_ae1_cross_role_prefix/analysis.cjs \
  experiments/spiral_neural/20261113_scheduled_suffix_exposure/results.json \
  /tmp/ae1_cross_role_recheck.json
```
結果需符合 source Git blob gate、864源輸出、432配對與上述分段計數。此為**既有四學生讀取封存診斷**，不是新神經NN訓練；沒有機制推斷、長度外推、r3/r4、數學題庫或跨模型 SLE 學習證明。

[更新] 已封存的 r2 錯誤目前都在第二個資料詞，第一詞與STOP穩定；原 train/high 三標籤為相同資料。[取代] 把 r2 失敗籠統稱為「整串沒有複製能力」，以及把 train/high 看成獨立 OOD 測試。[原因] 新 r1/r2 成對分段核對及原始 row 函式／封存 Q 檢查。[狀態] 檔案上觀測信心高；泛化機制推論信心低。

**Next owner：** NN 審查者應先於本機 Node 重跑本新增分析、確認資料別名；若要真正辨識是否學會第二詞位置上的一般 copy，可另凍結同一模型 checkpoint 的 **僅替換 b、固定 a/c/d/r2** 的合法 raw-01 成對挑戰，記錄 second output 是否跟著 b 而不是沿用原 `(a,b)` 記憶。必須先鎖定試題和 split，保持其餘因素與權重不變；不可把本輪 post-hoc 視為盲測或擅自追加 optimizer 更新。
