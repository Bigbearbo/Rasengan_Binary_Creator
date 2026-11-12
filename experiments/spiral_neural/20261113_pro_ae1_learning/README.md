# Pro AE1 神經學習：先凍結設計，再執行

日期：2026-11-13（Asia/Taipei）。作者：ChatGPT Pro／受指派本機 agent。

這一輪承接 [AE1 格式設計](../../../../docs/ai_orchestration/PRO_ADVANCED_ECHO_DESIGN_20261113.md)，回答固定五階、多詞回音能否被現有純 01 小網路學會，並檢查回覆詞數是否能控制 STOP。使用者提出多詞回音與先研究後實驗的工作方式；以下精確資料、課程、預算及判準是 Pro 的具體設計。

本次是一個課程、三個 seed 的能力篩查。沒有直接混教比較臂，不估計課程優越性；流程耗時另作觀察，不把單次執行當成效率提升的因果證據。

## 事前固定內容

[protocol.json](protocol.json) 是機器可讀規格。固定採既有 P030 Model，L80/H64、10,499 參數；Adam 與初始化規則不改，不擴網、不移植既有學生或人工 copy 權重。學生只接收 raw Q 與答案前綴，輸出 0／1／STOP。自主作答接自身輸出，固定 cap32，宿主不按 r 截斷或補 STOP。

符號 ID0..29、每詞五資訊位加尾零；END=`111100`、UP=`111110` 保留。r 從一開始就表示回覆詞數；前四階段取 r=N，最後加入 N4 的 r1、r2、r3。固定 n5，不測跨位寬或未教詞數。

| 階段 | 教材 | 題數 | 每輪 target | 輪數 | 本階段更新 | 累計更新 |
|---|---|---:|---:|---:|---:|---:|
| 1 | 一詞完整回音 | 30 | 210 | 24 | 5,040 | 5,040 |
| 2 | 一至二詞完整回音 | 150 | 1,770 | 8 | 14,160 | 19,200 |
| 3 | 一至三詞完整回音 | 270 | 4,050 | 8 | 32,400 | 51,600 |
| 4 | 一至四詞完整回音 | 390 | 7,050 | 8 | 56,400 | 108,000 |
| 5 | 上述複習＋四詞內容的不同 r | 750 | 11,730 | 8 | 93,840 | 201,840 |

每輪完整 target 多重集合只洗一次順序；不是逐題連續教完所有答案位置。所有階段帶著原權重、Adam moments 與更新年齡往下走。固定 seed101／202／303，每學生 201,840 更新；三學生主訓練共 605,520 更新、12,749,829,120 training dense MAC。另預先指定 seed101 完整重播一次，成本單列，不能算第四個獨立學生。

訓練不依成績加長、跳階、換 seed 或選 checkpoint；無 validation split。保存初始化及五個階段末。三條主訓練和指定重播完成後，才離線評估全部已存狀態。早期 checkpoint 的最終訓練題庫含尚未教的題目，報表另列 `taught_so_far_metrics`，不把未來題目說成已教未學會。

## 資料分組與判讀

[dataset.py](dataset.py) 產生固定 [dataset.json.gz](dataset.json.gz) 與 [data_checks.json](data_checks.json)。JSON 以固定 gzip 時戳壓縮保存，解開即為完整 raw 題單、答案、曝光帳與 target 池；不省略任何題目。N1 教全部 30 個符號；N2／N3／N4 各有 120 個訓練 payload 與 60 個測試 payload。在每個輸入位置，訓練每 ID 恰出現四次、測試兩次。完整 payload（含長度）作為分組單位，同一 payload 的所有 r 歸同一 split。先前公開四詞示例 `[1,6,11,17]` 排除於本次所有題單。

合計 750 訓練題、360 測試題。主測為 N4 測試：60 個未教完整 payload × 四個 r，共 240 題。每個 r 的問題只改 count 欄；四題都完整正確、都在不同正確位置自行 STOP，比分開的總分更能排除忽略參數的捷徑。

測試新的是完整 payload 題目組合；普通符號、短答案與跨長度片段可能已見。曝光帳逐題保留：N2 的 60 個測試 payload 中 11 個曾是更長訓練 payload 的前綴、21 個曾是其連續片段；N3 分別為 0／1。N4 的 r1 答案全都已出現，r2 有 18／60 曾作訓練完整答案或答案前綴，r3／r4 為 0／60。不能統稱所有角色都未見。

主分數為完整答案連自主 STOP。另報資訊位正確率（不把每詞必為 0 的尾碼算進資訊位）、teacher-forced 位元、STOP 位置、四 r 整組成功、同一正確答案前綴下「短 count 應停、長 count 應繼續」的條件動作，以及舊完整回音保留率。只抄到 END 的程式負控在 N4 至多答對四題中的一題；知道長度卻亂寫內容也不能通過完整分數。這些負控是計分檢查，不是神經學生。

事前篩查通過條件：每 seed 最後每個訓練 N/r 格子的整題率至少95%；N4測試整題至少95%、四 r 全對組至少90%、STOP位置至少99%。三 seed 都過才記本批穩定通過；同時保留所有原始分數，不將門檻當成統計母體保證。

## 可重現入口

所有命令從 repository root 執行。正式使用時，`PREREG_SHA` 應填入已公開的事前凍結 commit 完整 SHA。輸出採 exclusive create；請在新副本／新結果目錄重現，避免覆蓋既有證據。

```bash
python -B experiments/spiral_neural/20261113_pro_ae1_learning/dataset.py
python -B experiments/spiral_neural/20261113_pro_ae1_learning/preflight.py
python -B experiments/spiral_neural/20261113_pro_ae1_learning/run_trial.py prepare
python -B experiments/spiral_neural/20261113_pro_ae1_learning/run_trial.py train --seed 101 --prereg-commit PREREG_SHA
python -B experiments/spiral_neural/20261113_pro_ae1_learning/run_trial.py train --seed 202 --prereg-commit PREREG_SHA
python -B experiments/spiral_neural/20261113_pro_ae1_learning/run_trial.py train --seed 303 --prereg-commit PREREG_SHA
python -B experiments/spiral_neural/20261113_pro_ae1_learning/run_trial.py replay --seed 101 --prereg-commit PREREG_SHA
python -B experiments/spiral_neural/20261113_pro_ae1_learning/run_trial.py verify-replay
python -B experiments/spiral_neural/20261113_pro_ae1_learning/run_trial.py evaluate --prereg-commit PREREG_SHA
```

準備步驟只建立隨機初態、資料、課序與驗收，不做 NN forward 或 optimizer。`preflight.py` 的 STOP／cap 例子用人工 logits 測宿主迴圈，不能當神經回音成功；實際成本在其 JSON 中單列。

`frozen_manifest.json` 保存原始科學碼、資料、初態與每 seed 完整課序的 SHA256。runner 在開跑時同時核對工作檔及指定 Git commit 的 bytes。訓練期間不讀測試表作更新；dataset 雖一併存檔，target 池僅含 train。學習狀態和推論成本分開，離線評估必須證明沒有改動任何學習狀態。

## 本輪工作紀錄

[workflow_observations.json](workflow_observations.json) 紀錄設計與執行階段、事前修正、事後變更、實跑成本及耗時。計時起點是本輪第一次顯式讀時，未包含上一輪 AE1 格式設計的投入；因此本次耗時不能冒充從零開始的完整成本。

NVIDIA／OpenRouter worker 在本環境沒有可呼叫工具或現成 adapter，記為 `skipped_unavailable`，外部模型真實呼叫0。本機平行 agent 負責資料與 learner／研究審查，歸 Pro；與先前 Codex／NVIDIA 的實測分開。

當前此文件為訓練前版本；完成後新增固定結果報告、執行／重播／獨立推論核對與公開封存。歷史 learner、checkpoint、UR1／AE1 codec 和舊研究結果保持原貌。
