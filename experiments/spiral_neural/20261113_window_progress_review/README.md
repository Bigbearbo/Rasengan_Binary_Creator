# Codex 進度檢查與下一階段（視窗GPT，2026-11-13）

本輪接續 Codex 已公開的 PR #28，實際載入三份最終 checkpoint，重現全部舊題，並完成一次新 F2 唯讀探測；另修正 PR #29 漏測的後綴評估。神經訓練更新為 0，沒有修改任何既有 checkpoint 或原始實驗。本目錄是接棒審查與新設計，並非 Codex 又訓練了一批學生。

## 1. 最新進度與模型承接

來源以實際 PR head、原始結果和實驗目錄 HANDOFF 為準。最後來源刷新為台灣時間 2026-11-13 10:50:11；PR #28 最後可見更新 10:13:04。公開快照見 [source_snapshot.json](source_snapshot.json)。這是已公開進度，不推定尚未推送的本機工作不存在。

| 成果 | 固定來源 | 已確認結果 | 承接界線 |
| --- | --- | --- | --- |
| 八資訊位完整題域 | [PR #24](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/24)，`2a073c96869bbd0820ab3295ff3622b52ea881f2` | 三模型 Echo、Neg 各 256/256 | L23/H69，3,453 參數；獨立批次 |
| 進階回音參數 1、2 | [PR #26](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/26)，`7213cce112a8411b13dc128c49f9e88acfc9d65f` | 三模型 E1、E2 各 900/900 | 三個新 L80/H64 模型，10,499 參數；不是沿用 PR #24 權重 |
| 回音 1、2 加翻轉 1 | [PR #28](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/28)，`5ceec0c42507bb5646dc0d87089f4a86e0e6269c` | 三模型 E1/E2/F1 各 900/900 | 完整沿用 PR #26 的權重、Adam、birth、t、RNG；這一段是真正的連續學習 |
| 後綴暴露對照 | [PR #29](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/29)，`dcabc3a65a4b9e7a50ab83ff8266b2c233d15000` | 原 test 高後綴 r2 固定 7/12、變換 9/12 | 另四個 PyTorch batch Adam 學生，不能直接作 Codex 逐 target 訓練的因果對照 |

PR #28 的舊能力曾退步，最後恢復；不是全程沒有遺忘。三 seed 的首次全對／連兩輪全對停止分別為 5/6、8/9、6/9 輪。舊 E1/E2 的最低分分別為 806/870、899/851、826/873，分母各 900。seed303 首次全對後再退步，沒有挑最好 checkpoint。

這是實際的有限題庫學習成果。900 個 payload 覆蓋全部 30×30 前兩詞組合，第三、四詞則各固定一次；不能稱為全部 30^4 輸入。PR #27 的查表反例與此相容：換答案無關的後兩詞可以測穩定性，單獨不足以排除按前兩詞查表。

本輪已讀 PR #28 的程式、protocol、manifest、來源與結果。原生成只使用 Q 加模型自己的輸出，沒有強制答案長度或 STOP；F1 只反資訊位，保留尾零。ID0/1 的答案可呈現 `111110`/`111100`，在答案中仍是字面內容，只有外部 `S` 停止。

## 2. 新實測：舊題全對，F2 尚不能直接組合

新問題 F2 是研究者提出的有界擴展：同四詞、同 n5，把 `(op=100, r=2)` 定義為翻轉前兩詞各自的五資訊位，保留兩個尾零，再由模型自己停止。不是聲稱 PR #28 原本已定義、教過或測過 F2。這次新的是算符與參數組合，payload 和前兩詞值均已曝光。

先公開 [凍結提交 bdf15a1](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/bdf15a1ffeebbc3b439f0ed203d4e4fde959d2d2)，才執行一次 `f2_probe.py execute`。三個模型全部通過舊題後，才開始新組合探測。

| seed | 舊 E1/E2/F1 合計 | F2 整題 | F2 第一詞 | F2 第二詞 | F2 STOP 位置 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 101 | 2700/2700 | 0/900 | 82/900 | 2/900 | 838/900 |
| 202 | 2700/2700 | 0/900 | 116/900 | 7/900 | 838/900 |
| 303 | 2700/2700 | 1/900 | 231/900 | 5/900 | 854/900 |

舊 8,100 個完整生成字串逐題吻合原封存。新 F2 多數題在正確長度停止，內容轉換則未可靠組合；而且第一詞也受影響，不只是第二詞尚未學會。這個行為差異支持「下一輪需要教 F2 並同時檢查兩詞」；它尚不能識別內部機制，也不構成模型或編碼的能力上限。

例：payload `[0,0,6,15]`，F2 正解 `111110111110S`；三模型依序輸出 `101110000000S`、`111100000000S`、`111100000000S`。它們都停對位置，卻沒有答對內容。

實際執行：10,800 次完整生成、110,027 次 forward、1,147,801,664 矩陣 MAC，正式推論 2.9845036 秒。此秒數不包含研究、讀檔前置與設計時間。權重、動量、birth、t、RNG、完整 state 和來源檔的前後 hash 均保持。0 optimizer、0 手工參數修改。

## 3. PR #29 評估錯誤及已完成的更正

原 `experiment.py:rows()` 在 `which == 'train'` 時選用訓練後綴函式，忽略 `suffix_mode`。因此 `train/seen`、`train/changed_low`、`train/unseen_high` 實際重測相同 Q；標成高後綴的資料仍是 ID0..14。val/test 走另一條正確分支，因此原 7/12 與 9/12 沒有因此失效。

原 864 列回放相符的紀錄對應 480 個不同 `(學生,Q)`，其餘 384 列重複。本輪不重訓；用四份既有 inference-only checkpoint 的原權重，以獨立 float32 NumPy 先重現 480/480 個不同已封存輸出，再補算真正缺少的 384 題。更正表共 864 個不同 `(學生,Q)`。

| 學生 | 策略 | 已教前兩詞＋高後綴 r1 | 已教前兩詞＋高後綴 r2 |
| --- | --- | ---: | ---: |
| 101 | 固定後綴 | 24/24 | 23/24 |
| 101 | 每輪變換後綴 | 24/24 | 24/24 |
| 202 | 固定後綴 | 22/24 | 18/24 |
| 202 | 每輪變換後綴 | 24/24 | 15/24 |

固定和變換策略的上述整題總數各為 87/96；只看 r2，為 41/48 與 39/48。原後綴及更換低詞域後綴仍全對，全部 STOP 位置正確。原 test 高後綴 r2 仍是固定 7/12、變換 9/12。這批兩 seed 沒有呈現變換後綴的一致優勢，但再次顯示答案無關的詞也可能干擾已教答案。

本輪 correction 為 8,640 次 forward、90,132,480 矩陣 MAC，0 optimizer。重現的是輸出字串，不宣稱 PyTorch 與 NumPy 的 logits 位元完全相同。四份 inference-only 權重不包含原 Adam 狀態，不能拿來冒充 Codex 可精確續訓的完整 checkpoint。

[更新] PR #29 的 train 後綴評估已另行更正；高後綴下固定／變換整體各 87/96。

[取代] 原 train 三個 regime 已真正測過不同後綴，且可用其全對支持後綴穩定性。

[原因] 原資料函式對 train 忽略評估參數，本輪直接使用既有權重補足漏測，沒有改動歷史結果。

[狀態] 程式問題與更正結果信心高；後綴變換是否一般有益仍未確認。

## 4. 下一階段：F2 → E3 → E4

完整可執行設計見 [NEXT_PHASE.md](NEXT_PHASE.md) 與 [next_phase_plan.json](next_phase_plan.json)。本輪只設計，沒有啟動這份訓練。

先從 PR #28 的三個最終完整狀態續訓 F2，保留 E1/E2/F1。四類各 900 題，每輪共 36,000 個 target 更新；模型、原始 0/1 介面、Adam、窗口、詞寬和 payload 不變。四類各 900/900，連續兩輪才前進；每學生上限 40 輪，失敗保留，不臨時延長、換 seed 或改權重。

F2 後才分別加 E3、E4，保留前階已會的任務。這把「既有算符與參數的新組合」和「新的輸出位置／長度」分開。達到固定 bank 掌握不必先通過額外泛化門檻；將來另測新資料時，按其曝光身分明確記錄。

## 5. 證據、重現與交接

`evidence.zip` 完整保存本輪 `f2_results.json`（10,800 筆逐題資料）與 `pr29_correction_results.json`（864 筆更正資料）。[results_summary.json](results_summary.json) 提供小型入口；[evidence_manifest.json](evidence_manifest.json) 記錄 bytes/SHA。所有歷史原始檔保持原樣，未覆寫他人的主導航。

F2 來源、資料和模型載入的 0 NN 檢查：

```bash
python experiments/spiral_neural/20261113_window_progress_review/f2_probe.py check
```

在沒有本輪原始輸出檔的乾淨 checkout 重現一次 F2（需有凍結 commit 物件）：

```bash
python experiments/spiral_neural/20261113_window_progress_review/f2_probe.py execute --frozen-commit bdf15a1ffeebbc3b439f0ed203d4e4fde959d2d2
```

PR #29 correction 使用其指定 commit 的獨立、唯讀 worktree；`--reference-root` 指向該 checkout 根目錄：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python experiments/spiral_neural/20261113_window_progress_review/pr29_evaluation_correction.py --reference-root ../pr29_reference
```

本輪沒有執行正式學習、完整訓練重播、架構比較、VM 實驗或物理擴網。Git 記錄分享結果和下一步，不能自行啟動使用者本機 Codex。後續 owner 是 Codex 的 NN 實驗執行者；先查是否已有更新 head，再在新目錄凍結課序與訓練計畫。

來源歸屬：U 為已有公開紀錄中的作者多詞回音與混教方向；F 為上述 pinned PR 程式／資料；T 為本輪視窗GPT及其受指派 agent 的真正唯讀檢驗；A 為 F2 語義擴展與下一課程。NVIDIA/OpenRouter 在本輪環境沒有可用 worker 入口，`skipped_unavailable`、實際呼叫 0；沒有把原生協作 agent 冒稱 NVIDIA。
