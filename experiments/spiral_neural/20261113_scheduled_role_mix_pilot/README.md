# AE1 原生 01 小網路：固定教材量的高詞跨答案位置混教（實測）

2026-11-13；獨立 NN 研究。此目錄 **新訓練兩名小網路學生**；不修改 VM、螺旋語詞典、Pro UR1 或 Codex F2。建立在已完成 [PR #36](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/36) 的固定四學生對照上。該批證實高詞值 ID6..14 經單一答案位置教學後，在相反答案位置為 0/18。本批問：**在每學生仍只有36筆高詞補充題、相同 seed／初態／訓練預算下，對每一高詞同時教兩個答案位置，能否在未教組合中正確使用？**

## 事前固定與唯一變因

事前實驗文件 `protocol.json`、`run.py`、`verify.py` 已在 **任何本批 NN 訓練之前** 提交於本獨立分支，固定提交 `38fd871840c70ea322328b4996fd73f73ac0f2af`。來源 PR36 固定 head `0b4a39342ee4ef00a0775ece7a2c20a1dfa08b25`；原 runner Git blob `ef24e2f5fd2515e5b5c0d0a593e5a9db9cca24b9`、原 runner SHA256 `05e2d730eecefcb50fa92392697556ffde313f5ecb59c2f4e583aad52e321303`。這批不是把原模型拿來續訓，也沒有重新跑 PR36 四份舊訓練。

唯一教學政策差異：針對合法高詞 v=6..14、低詞 s=0..3 共36組，舊控制組將高詞一律放第一／一律放第二答案詞，本組則依 `(v−6+s) mod 2` 對半分配：偶數放第一，奇數放第二。每高詞出現四次、每位置各兩次，低詞 s 各出現九次。**改變的是教材位置分配政策，不是孤立的一個 raw input 位；此比較不能拆出輸入位置、答案前綴、位置曝光三者的個別因果。**

Profile 為 `SLE-AE1-n5-v1`：`Q=01+010+r(3資訊位+尾0)+4×(5資訊位+尾0)+END(111100)`，題目39個 0/1 位，r=1或2，普通ID0..29，30/31保留為END/UP；學生自行逐位輸出前 r 個完整六位元詞，再以外部 `S` 停止。不給模型 parser、額外詞界或教師答案。c=d=0 保持不變。模型160 one-hot槽→64 tanh→3 logits，10,499參數；seed101/202 每組 fresh model 與父組**同一完整初始權重SHA**，Adam lr.003、batch64、clip1、250epochs、shuffle種子固定。每學生3,750 Adam更新、237,000個訓練target；本批兩學生總7,500更新、474,000 target。訓練 forward dense MAC共4,944,768,000（未含 backward/optimizer）。

Base36對(a,b∈0..5)依 `(a+b)%6` 分為24train／6val／6test，r1/r2各一題，train 48題；高詞補充36題只教r2；每epoch恆定948個 `(Q+正確答案前綴,target)`。另外逆向未教36題、低詞s=4保留18題、s=5保留18題，**都沒有混進訓練**。但s4/s5值域已由前批研究人員查看，不是全新盲測。

事前 gate：每學生混教方向至少33/36、base train至少46/48，才解釋跨位置測試；兩seed必須各在高詞第一及第二位置的18道s4+s5題中至少12/18，並各在36個反向未教配對中至少25/36，才稱此批達成預定成效。不能事後調 seed／epoch／答案集挑結果。

raw 例（單一高詞相同，只換位置）：
```text
Q(r2,a0,b6,c0,d0)  010100100000000001100000000000000111100
正解                  000000001100S
Q(r2,a6,b0,c0,d0)  010100100001100000000000000000000111100
正解                  001100000000S
```

## 本輪 T：兩名新學生實際訓練／自行生成

| seed | 原域train / val / test | 受教36題 | 未教反向36題 | 高詞第一s4+s5（18題） | 高詞第二s4+s5（18題） |
| --- | --- | --- | --- | --- | --- |
| 101 | 48/48、12/12、12/12 | 36/36 | **36/36** | **16/18** | **16/18** |
| 202 | 48/48、12/12、12/12 | 36/36 | **36/36** | **16/18** | **18/18** |

事前擬合 gate 及預定兩個泛化門檻都通過。受教36題與未教反向36題在兩seed均全對；四種低詞s4/s5保留組合72筆合計66/72整串連 `S` 正確，6題錯誤皆完整保存。**對照 PR36 原角色專教，每個seed/專教模型跨兩角色只能18/36；本批混教每個seed為32/36或34/36**。已由 `audit_comparison.py` 對原 PR36 的 Q、expected 做逐題配對，720筆舊輸出不重做神經 forward。此比較並非等角色單獨曝露量：混教兩位置各只2次，高詞專教在單位置4次；這是等總課數的課程政策比較。

若只挑兩道代表性失敗例，seed101：
```text
Q(r2,a10,b4) 010100100010100001000000000000000111100
正解          010100001000S
本批錯答      010100000100S

Q(r2,a4,b11) 010100100001000010110000000000000111100
正解          001000010110S
本批錯答      000110010100S
```

這是 **此一固定任務分布的小網路跨位置能力**，不等於任意詞寬、任意長回音或一般算術已學會；兩seed很少，也沒有測試位置不變的純 bitwise copy 機制。原域與後綴固定，無法歸功 SLE 優於普通二進位。尤其先前看過低詞s4/s5配對的結果，這次是配對診斷而非新盲測。對「高詞角色混教能提升有限域跨位置結果」信心中高（限這兩學生）；對「學會通用複製規則」信心低。

## 可重播性、資源與失敗紀錄

```bash
cd experiments/spiral_neural/20261113_scheduled_role_mix_pilot
python run.py selftest
python run.py train
python verify.py
python audit_comparison.py
```

前置 `selftest` 在訓練前真正執行 PASS，包含父 runner SHA、原始資料SHA、39bit合法性、24/6/6分割、36混教／36反向、每高詞雙位置等量、初始權重配對、948 targets、10,499參數。第一次訓練呼叫遇到容器超時中斷，未留下結果／checkpoint，也沒有評分可選；其耗費的運算時間不明，不能算進可核對的正式訓練成本。修正進程環境 (`OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1`) 後獨立正式啟動一次，完成兩名新學生，輸出如下：

```text
MODEL 101 fitted 36 /36 inverse 36 /36 hold s4 first/second 7 7 hold s5 first/second 9 9
MODEL 202 fitted 36 /36 inverse 36 /36 hold s4 first/second 8 9 hold s5 first/second 8 9
RESULT 360 raw 7500 new updates 4248 evaluation forward 6.446 sec
PASS 360/360 independent checkpoint reload + native Q/answer + free generation, exact per-case; splits and costs verified
PASS: 72 paired holdouts matched exactly to old PR36 Q/expected; new MIX 66/72; old role-exclusive each 36/72 across both seeds.
```

PyTorch與NumPy版本見 `results.json`；6.446秒是該次成功正式訓練及評估的程式時鐘，不含下載、Git或超時嘗試。新評估 4,248 次 NN forward、44,315,136 dense MAC；另有 checkpoint 重載後逐條評估360例的驗證推論，**不包含在前述正式評估呼叫數，額外 forward 成本未由驗證器計量**。optimizer更新總7500、forward train MAC僅正向估算，不把梯度與optimizer開銷算進去。所有360題原生Q、完整期望答案、模型實際答案、停止資訊、兩份float32權重均保存，失敗未刪也沒挑早期權重。獨立驗證器重新寫native Q、answer、forward/free生成計算，核對360/360自由生成及checkpoint；不是完整重新訓練replay。

固定 SHA256：

- `protocol.json` `e695547810d8c15c15ec5608261bf08dab9eea3f09cd0e917efe41c43a707e41`
- `run.py` `e5b6f8b0c382b2720efdfa8acaa75c8352a41226045cc7768824e1630b47024c`
- `verify.py` `f447c38f25bc65e31083083c69d0ab70ea2df269097e722e9ac478bd719f5f81`
- `raw_cases.jsonl` `768c010b22b61325d1d14e85a58e9a286e2e02fad111e2525290a3a0c94c7349`
- `results.json` `46b3f81b90b59f18c2f756d085c5fc520a403d1e7f8cca85f2f959f4ca438f95`
- `weights_seed101_mix_parity.json` `2adc0388bc6e2b4c076453bff6534221bee46542282dc9aa167fefe471dd2d16`
- `weights_seed202_mix_parity.json` `c8d2d9f3abd6b78856e623aec923c1ea2af86da31e0de3896daedb394ffc4941`
- `audit_comparison.py` `b1c9bded604260bab63fee855528990562cb34b7e431fa3f1eefe9fcd97c7047`

## U/F/T/A 與下一棒

U：使用者指定 SLE 原生01、教學與泛化、成長與小型神經網路的可辨因研究，並要求不重做 VM／詞典及不冒稱外部模型。F：PR36 完整 checkpoint 與前輪負結果，P030～P035及UR1／F2相異分支現況。T：本輪上述事前閘門、真實 PyTorch 訓練、配對唯讀核對和重載驗證。A：混合位置曝光是改善此有限題域的可能機制；沒隔離絕對位置與上下文作用、未測算術、尚非通用推理。

NVIDIA 實呼0（此執行環境沒有取得本機 OpenRouter 授權 worker，不讀私人 API key）；Codex本機0、Gemini0。發布只在本獨立研究分支，Draft PR 待人審核，不合併、不覆寫 PR36／PR33／PR12 的分支。

**Next owner：** 獨立 NN reviewer 先檢查原始360條與兩 checkpoint 的可攜重播，尤其是不應誤把 `S` 和合法詞中 `111100` 混為控制；若後續真正要驗通用位置規則，凍結新的完整 `(v,s)` 詞域與新 seed/數值域作新盲測，再考慮多回音詞數、算術或增長；不在已看s4/s5上調參補訓。
