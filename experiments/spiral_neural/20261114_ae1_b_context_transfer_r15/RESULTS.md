# AE1 R15：未教過的高位組合，換第二詞上下文後能否保留？
2026-11-14。Owner：獨立 SLE 原生 01 小型 NN。這不是 Pro UR1、Codex F3 或倉鼠 VM 的重跑。

## 事前定案
唯一變因為第二答案資料詞 b：R14 先前檢查的是 b0,1,2,3,18,19,22,23；R15 固定第一詞 a25..27、r2、c0、d1、9份真實 checkpoint，在新 b4,5 驗證、b15,16,17,20,21 正式測試。新 b 在母教材第二詞位置已見，但新整題未教；另外 a0..5×正式 b 構成校準面板。合法 SLE-AE1-n5-v1：39 個 raw 01 問題 bit，第一及第二詞各6bit加 STOP。每模型6題驗證、15題測試、30題校準；3 seeds × 3 課程＝459題。參數10457／模型，新增0次 optimizer、0個訓練 target。

Git 先於任何 R15 forward 凍結：
- `manifest.jsonl` commit `c065c96eb7820eeabcc6e7e88865a6017473e3d9`
- `prereg.json` commit `4173c3397fc2d8322379f1cdeaffd7963fde7e6f`
- `FROZEN_BEFORE_RUN.md` commit `6d775015acda37d1cd049dc92a35554c6d79e624`

預先成功門檻：至少2/3 seeds 的平衡混教學生，在正式15題中，第一答案詞≥10，整串含STOP≥7，且第一詞優於每個單高位控制≥8。沒有追加測試或修訂門檻。

## 真實新推論結果（各 seed 正式15題）
| Seed | 只教 bit16 整串/首詞 | 只教 bit8 整串/首詞 | 混教整串/首詞/次詞 | Gate |
| --- | --- | --- | --- | --- |
| 101 | 0/0 | 0/0 | 6/7/12 | FAIL |
| 202 | 0/0 | 0/0 | 4/10/8 | FAIL |
| 303 | 0/0 | 0/0 | 4/11/5 | FAIL |
| 合計 | 0/45、0/45 | 0/45、0/45 | **14/45、28/45、25/45** | **0/3 FAIL** |

驗證 b4,5：混教13/18完整正確；正式 b15..21：混教14/45。b20：完整0/9；b15：5/9。校準已見 a0..5 + 新 b：混教43/90，兩控制47/90及46/90。所有459題停止位置都正確，內容錯誤仍必須計入。R14 在另一組 b 得52/72，與本輪題域不同，只能說不同上下文下效果不穩，不能用兩率當同分布下降量，更不是輸出層病因證明。

實際反例 seed202 混教：a25,b16 expected `110010100000S`, actual `110010000000S`；a25,b20 expected `110010101000S`, actual `100010101100S`。

T：實跑 PyTorch 459 個 greedy 原生01完整答案，5,967 neural forwards、65,159,640 inference dense MAC、0 optimizer、0 training MAC。另一份沒有 Torch 的 NumPy 推論引擎使用原九權重，重算 **459/459完整回答與5,967 forward一致**、九份 checkpoint SHA PASS；是推論重播，不是 optimizer 逐步重播。原始答案SHA256 `6315ece03bdc472568bfd2d52aaa27df60b406183a5fd8b24f4e3eb2285d21e8`，完整附檔 ZIP SHA256 `ac361c7a439133df46ed90ae42a38f4f77ab1861089b0b53aec0ea015eefbe0d`。已在乾淨解壓副本通過26個檔案SHA、靜態 gate 與NumPy重播。**Git只有規格／程式／摘要，九模型、逐題 raw bits、全部證據需搭配 ZIP**。

## U / F / T / A 與下個 owner
U：使用者要求獨立小型 SLE 01 NN 的真正學習、泛化與課程。F：#63 真實 R14 原檔、9 checkpoint；P030–P035、Pro UR1/#12、Codex續教/#61 均已分別查閱且未重跑。T：以上本輪固定權重新原生01推論與獨立回放。A：雙高位混教形成有限跨 b 組合遷移，但未形成可靠的通用複製能力；輸出層、輸入背景、教材覆蓋的作用仍未辨明。a25..27 已被研究者在 R14 看過，本次不是研究者全盲。

NVIDIA：0（本運行環境沒有授權的OpenRouter端點）；本機Codex：0；Gemini：0。無LLM替學生算答案，沒有UR1 manifest 核准、沒有自動merge、沒有私人資料及key上傳。

Next owner：獨立 NN reviewer；先審視 b20 相關教材覆蓋與錯誤分布，再把真正新 a/b 域和等成本位置交錯課另行預註冊，不能拿本輪見過的題目稱盲測。完整可重播包 `sle_ae1_b_context_transfer_20261114_r15.zip` 由研究回報單獨交付。
