# AE1 第二答案詞位元組合教學：四個新 NN 學生的實際結果

**本分支 source：原 [PR #42](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/42) head `3f6af7aba3c257a8a9fd3ac7728a3b42bc461037`，凍結訓練權重來自 [PR #40](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/40)。事前閘門在本獨立分支 commit `6c8bc78d1bbfe39b1e2c15eb86243c8b9a4907a9` 完成遠端 bytes readback 後，才進行本輪四個新訓練；不改 Pro、Codex、VM 或 UR1 分支。**

## 事前單一干預和結果

SLE-AE1-n5-v1：原生 39 個 0/1 Q、資料詞五資訊位＋尾零、回答 r1/r2 完整詞＋小網路自主生成 S。各臂相同既有 120 次教材（96 個不同 Q、24 個重複），另有16次 r2 教材。**唯一臂間差異**是第二答案詞 b 的值：舊值對照 ID16,17,20,21，組合值教學 ID24,25,28,29（對應恰多一個 bit8），同為 a0–3,c1,d0。

父課程其實有108次 c0、12次 c1。原預登記敘述「parent c0」不精確；沒有改變實際課程、任何已凍結檔案或兩臂比較，原文字不倒填，見後段 erratum。

val：b26/27×a4×c1,d0 共2題；test：b26/27×a5×c1,d0 共2題，兩臂完全同題，所有 b26/27 未在本輪訓練中出現。**原先判準**是兩seed各自組合教學≥3/4且對照≤1/4，未通過也報FAIL，不加seed或epoch。

| seed | 對照 val | 組合教學 val | 對照 test | 組合教學 test | 預先判準 |
|---|---:|---:|---:|---:|---|
| 101 | 0/2 | 2/2 | 0/2 | 2/2 | PASS |
| 202 | 0/2 | 2/2 | 0/2 | 1/2 | PASS |
| 合計 | 0/4 | 4/4 | 0/4 | 3/4 | 兩seed均PASS |

總計本批學生新詞測試：control **0/8**、conjunction **7/8**。唯一主要處理組錯例 seed202 a5,b26,c1,d0：Q=`010100100001010110100000010000000111100`、正解=`001010110100S`、實際=`001010110010S`。對照同題為`001010100100S`，但各模型均能在該位置正確 S 停止。

完整給定題域的另外三項同樣重要的觀察：四模型全保留原base train48/48、val12/12、test12/12和seen high r2 36/36；各新處理學生在加入的16題都16/16，對照0/16。**更重要的限定：原本事前登記的 c0 二級保留測試，b26/27×a0–5，組合教學兩模型各0/12，對照亦各0/12；同時 c1 這12題組合教學各11/12與10/12，對照均0/12。** 這項改善強烈依賴第三個（理論上無關）資料詞 c 的狀態；不能宣稱通用copy規則。原文字的 c0 簡寫修正另見 `ERRATA.md`（在執行後新增而非修改預登記）。

## 實際執行與可重現證據

**本輪 T：** PyTorch2.10.0+cpu／NumPy2.3.5，seed101/202各兩臂，4個新的10499參數模型。每學生 100 epochs × (136 次教材、1408教師targets)，batch64，22更新/epoch，即 **2200次/學生、8800次 Adam optimizer 更新、563200 target presentations、5,875,302,400 訓練前向 dense MAC**，不含 BP、optimizer、其他CPU成本；評估640筆實際自由生成、7168次 NN forward、74776576評估 dense MAC、沒有大模型代答。預登記已有 24 個原課程重複的 preflight FAIL，0 optimizer，修正閘門後仍保留母課程原始順序／重複；第一次正式 train exit0。

已於新的解壓副本執行 `sha256sum -c SHA256SUMS` 全檔PASS，`OPENBLAS_NUM_THREADS=1 python verify_numpy.py` 以**不 import torch 的獨立 NumPy** 解析四份原始 F32 checkpoint、核對所有640筆 Q/A 與 **640/640** 完整模型回答、**7168/7168**生成步數一致。這是輸出重播，**不是** optimizer bit-exact 完整重訓重播。

| Evidence / frozen component | SHA256 |
|---|---|
| original frozen parent 120 rows | `e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a` |
| initial seed101 parent weights | `ac022fdcac1c6e9de5b78e1667519a6443e05c7f8e48fe4b84514432a1576009` |
| initial seed202 parent weights | `048c719e8c2afbbcac579b80a2f820989eb68ba030a1f2ce7c2747474897a157` |
| exact public `run.py` | `ae6c3e0d3c129d86100f1d4d686818fa7f2cf3f4f8631aed9494121fb23efeca` |
| exact `PREREGISTRATION.json` | `1f0442de163b03fffb1e8bfbb0159f2dae2d09c1d9c8a8b3f8c7f98c269af029` |
| 640 raw cases `raw_cases.jsonl` | `b656838d2dbba1739bb653d805fbf6519eb709ed0e7f07314e85058aa1d9dcf9` |
| summary `RESULTS.json` | `fe753783f27499ca08b8acd059333f353b50e670d82c9dd07b5aba7d15e94806` |
| user-delivered reproducible ZIP | `bb377c8f15d5c7861442ce25b29f5a7b52b1b2660426aa42ed0f6b5450bef443` |

Git 有精確、可用 blob SHA驗證的 `run.py`、`PREREGISTRATION.json`、`parent_course.json`、`verify_numpy.py`、事前/事後說明；上述完整版 ZIP 另含兩份母checkpoint、四份新checkpoint、640筆原生raw bits、所有負例以及逐檔 SHA256SUMS；**Git沒有全部checkpoint，不能宣稱只clone就能完整回放**。ZIP已實際重解壓驗收。

來源：U 作者的神經小網路／01 泛化方向；F PR40兩名混教學生、PR42既有新位元失敗與 P030～P035 固定證據；T 本次真正新訓練、自由生成、獨立驗證；A 僅在本類固定第三詞上下文的高位組合教材能影響未教低位組合。另：控制組所加的是已熟高詞、處理組則是新高詞，新增教材的新奇度不是相同的；這是「額外教學詞值家族」政策比較，不是學到抽象組合演算法的證據。研究員已查看鄰近詞域，test不能稱新盲測，樣本僅兩seed、4題/seed。

NVIDIA 0次：本工具環境沒有能直接執行的、已授權 OpenRouter reviewer；本機 Codex 0次，Gemini 0次；沒有洩漏 key、私人聊天／Library 或模型 oracle 給學生。Next owner: independent verifier/Codex 可取ZIP做跨環境測試；新模型與題域另立事前凍結，勿在已查看的b26/27持續調超參數。**Draft，不合併。**
