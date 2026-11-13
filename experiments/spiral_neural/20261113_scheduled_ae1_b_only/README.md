# AE1：第二資料詞 b 單變因介入（2026-11-13）

本輪以 PR #29 的四個已訓練神經模型 checkpoint 實際執行 288 題新推論，不是重訓；不修改 UR1、倉鼠 VM、詞典或既有教材。承接 PR #31 第二詞錯誤定位，將輸入的第二個資料詞 b 單獨改變，觀察網路是否跟著改變答案。

## 事前凍結與來源

初版 manifest commit: abeac6aa0231b391fdadd06bb1d7960f600f1379；在任何新 NN forward 前，於 63ceac6cff808101c46e4041c8be7159e2d58a36 校正示例 raw Q，不改研究問題。執行器事前提交 f2f226f5a8504a5be3752a9e844b08965e47d312。

原始 checkpoint 源頭是 PR29 head dcabc3a65a4b9e7a50ab83ff8266b2c233d15000；每模型 10,499 參數，seed101/202 × fixed/varied，先前各200 epochs／1,600 Adam optimizer steps，本輪 0 更新。4個源權重 blob 和 results.json blob SHA 均固定在 preregistered_protocol.json。

合法 profile SLE-AE1-n5-v1：Q = 01 + 010 + r(3資訊位+0) + 4×(5資訊位+0) + 111100；r 為 1 或 2，普通詞 ID0..29，完整答案前 r 個六位元詞加 S 停止。Q 長39 bits。原始 train/val/test 分割由 (a+b)%6 決定：0 val、1 test、其他 train。

從六個原始 test (a,b0) 作為 anchor，每個 anchor 固定 a、原 test 的高後綴 c,d（範圍15..29），每次只換 b=0..5，並分 r1/r2。4模型×6 anchors×6 b×2 r = 288 題；其中改動 b 的配對共 240 個。新的 b 可能是先前在其他後綴上已教的 (a,b)，不是未見答案組合的盲測。

## 真正執行結果 T

在可用 GitHub connector 的隔離 JS/V8 執行環境，以原始 float32 權重重建 dense-tanh 前向傳播，先和 archive 864 筆逐題輸出核對：864/864 PASS，然後新增 288 個完整 01 問答。每筆 raw Q、標準答案、模型回答與失敗均在 results.json。

| 情境 | 整題正確 |
| --- | ---: |
| r1，原 test/high anchor | 24/24 |
| r1，只改 b | 119/120 |
| r2，原 test/high anchor | 16/24 |
| r2，只改 b | 99/120 |

r1 換 b 後輸出保持不變 119/120；r2 換 b 後第一個輸出詞仍保持原模型輸出 119/120，第二詞確實等於新 b 99/120，而誤回原 b0 的只有 3/120。全部 288/288 題 STOP 位置正確。

各學生 r2 changed-b 完整正確：seed101 fixed 27/30、seed101 varied 30/30、seed202 fixed 25/30、seed202 varied 17/30。無法宣稱 varied 對所有 seed 都比較好。依 (a,b) 原分割標籤統計，r2 train 79/96、val 20/24、test 16/24；僅為事後分層描述。

Raw 失敗例：seed101 fixed，a=0、b=1、c=18、d=26、r2。

Q: 010100100000000000010100100110100111100
預期: 000000000010S
模型: 000000000100S

同一個 a,c,d,r 下，把 b 改成2，模型回答 000000000100S 反而符合新題。另一反例：seed202 fixed，a=2，原 b0=5 改成 b=4，r1 應答 000100S，卻輸出 000110S；所以不能宣稱 r1 完全不受答案無關的 b 干擾。

## 成本、重現、限制

本輪實際 11,520 次新計算的神經 forward：其中 8,640 用於歷史輸出重現 gate，2,880 用於 288 題新增介入；每次線性層10,432 dense MAC，新增介入30,044,160 MAC，連重現 gate 共120,176,640 MAC（不含 tanh/bias/I/O）；0 optimizer 更新。

完整 Git checkout 可用下列命令重跑：

    node experiments/spiral_neural/20261113_scheduled_ae1_b_only/probe.cjs

probe.cjs 具備完整輸入 Git blob SHA、tensor state SHA、864 output gate、法定 SLE bits 約束及288筆案例輸出。本輪真正運算在 GitHub connector 的 JS/V8；Node CLI 在完整 checkout 尚未獨立執行，不宣稱該命令已 exit0。第一次 connector 嘗試因工具腳本人工抄錄 seed202 fixed SHA 少最後一字元，在來源 gate 階段正確拒絕；校正後才執行推論。

U：作者要求獨立原生01小 NN、單一可辨因變因與可信資源數字。F：PR29 四權重與864封存結果、PR31定位、PR30原 train suffix label 別名修正。T：此次實算的864 archived gate + 288新問答。A：[更新] 對 b 的可觀察輸出敏感性存在，不能只用舊 b0 照抄解釋。[取代] 只依整串得分與無關後綴便推定位置複製能力。[原因] 固定其他三詞及參數，只動 b。[狀態] 本四模型推論觀察信心高，一般規則泛化仍低。

Next owner：NN 研究協調者審查 b-only 失敗；若值得，再為真正沒有訓練曝光過的答案相關 (a,b) 組合另凍結新訓練，不能修改 PR29 原分割或覆寫 Pro/Codex 工作。NVIDIA 0 呼叫（沒有獲授權的可用 worker），Codex 本機 0 呼叫。研究分支保持獨立，不自行 merge。
