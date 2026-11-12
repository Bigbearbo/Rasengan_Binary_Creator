# Pro：UR1 神經確認回覆的組合保留測試

設計／實作歸屬：**ChatGPT Pro**。本目錄將 UR1 的合法通知實際交給神經學生學習，與先前 scripted codec 驗收分開。正式訓練須先凍結並提交 preregistration，再以指定 manifest SHA 明確啟動；本 README 不把尚未執行的訓練寫成成果。

## 本輪問題與限制

只問：固定的小型 MLP 能否由 raw 通知生成「地址＋一份 UP＋STOP」，並處理**已見地址、已見寬度的未教組合**？不宣稱辨別普通題／通知、拒絕非法訊息、理解地址作用、在正確分支應用新寬度、跨題記憶、升階收益或通知對數學學習的幫助。

沿用 UR1 `a6f4a0943d63a6cba1763f5de095d40aba893bfa` 的 codec，選六個 k1 位置 `[0]`、`[1]`、`[2]`、`[5,0]`、`[5,1]`、`[5,5,0]`，各配目標寬度 m4/m5/m6。按位置分別保留 m4/m5/m6/m4/m6/m5，故 12 train／6 heldout。每個地址在兩種其他寬度受教，所有 UP／END 詞形及最長 prefix 都已在 train 出現；不把它稱為新符號或長度外插。

合法 Q 的總長度和地址 count 本身可能提供目標寬度線索；成功不證明模型一定讀懂 UP 的語義。各 m 每 epoch 都有四題，但不同地址／答案長度使 target 曝光不均：m4/m5/m6 分別 68/68/76 targets，每 seed 累計 8,704/8,704/9,728；這是固定逐題課程的明列特性，沒有看分數後重加權。manifest 另保存輸入、教師答案、STOP 和逐題曝光帳。

每題教師使用**獨立合法的事件前 tree snapshot**，只將目標分支 n 設為 m−1，role／k／普通 ID／highwater 都不變。這些離線合法消息例可以洗牌，但不是把下降的 m 當成同一 live receiver 的連續升階。學生權重與 Adam 在整段訓練中持續，不跨題重設；tree／地址／m／答案長度等 metadata 只供教師產生教材及評分，不進神經輸入。

## 固定學生與預算

P035 封存的原 P030 `Model`、`forward/step/lesson`、Adam 和初始化公式全部原樣使用。從零初始化 L80/H64，共 **10,499 參數**；不在本輪另測成長排程。外部生成 wrapper 將固定上限設為 24 個動作，足以容納最大 A 的 23 bits＋STOP；不改歷史八步 `generate()`，不強迫補 STOP，不截成正確長度。最大 Q＋完整 A 是 75 bits。

| 項目 | 每 seed | 三 seed |
|---|---:|---:|
| seed | 101、202、303 分別執行 | 3 個學生 |
| epoch／每 epoch 不同訓練題 | 128／12 | — |
| 題次 | 1,536 | 4,608 |
| target 更新 | 27,136 | 81,408 |
| training dense MAC | 571,375,616 | 1,714,126,848 |
| p/m/v/birth 陣列 bytes | 209,980 | 不當作 process peak RAM |

每 epoch 恰好 212 targets，每 target 為原 reference 的 `H*(4L+9)=21,056` dense matrix MAC。另完整獨立重播同數更新與 MAC；含重播共 162,816 updates／3,428,253,696 training MAC。診斷 forward MAC／calls 與包含驗收的 walltime 另報；未另外量測非線性、Adam、編解碼或雜湊的硬體成本，dense MAC 不是全部硬體 FLOPs。

每 seed 使用 `default_rng(seed+61000)`，每 epoch 將 12 train 題完整洗牌一次；完整課序先寫進 manifest。全部學生固定跑完，不依分數早停、延長、加 seed 或選 checkpoint。訓練期間只在 epochs 0/16/32/64/96/128 量 train 曲線；三條主軌跡及三條重播全部完成後，才載入這六個固定 checkpoint，離線評估全部 18 題並保存完整曲線及 truth。最終分數直接重用 epoch128 的結果，不額外再推論一次；離線評估的 MAC／calls 獨立記錄。

強 gate：**每個 seed** 的最終自主生成 train12/12、heldout6/6，含正確 STOP。其他分數與所有失敗逐題保留，不把三 seed 對同六題的輸出當成十八個獨立題域，也不只報最好 seed。TF、地址、UP、STOP、首錯位置各自另報，不能替代整串自由生成。

## 先驗工程與凍結

在 repository 根目錄執行，需要 Python／NumPy。正式 manifest 固定本次實際 Python、NumPy 版本及單執行緒 BLAS 設定。

```bash
python -B experiments/spiral_neural/20261113_pro_notice_learning/run_trial.py --preflight
python -B -m unittest discover -s experiments/spiral_neural/20261113_pro_notice_learning -p test_engineering.py -v
python -B experiments/spiral_neural/20261113_pro_notice_learning/run_trial.py \
  --make-manifest experiments/spiral_neural/20261113_pro_notice_learning/frozen_manifest.json
```

每次 preflight 僅在非正式 seed 上作六次 synthetic optimizer 更新，檢查 native lesson 與獨立 target loop、完整 state 存取、生成上限／overflow；不產生正式 heldout 的神經分數。教材的合法性、分割、曝光與 prefix 標籤一致性也會先核對。

`frozen_manifest.json` 完整保存 18 個 Q/A、metadata、三組已抽好的課序及 hashes。`source-freeze.json` 保存 manifest/data/curriculum/source hashes。凍結來源涵蓋 protocol、核心程式、工程測試、原 codec 和原學生，路徑相對於 repository，可攜且不保存使用者本機路徑。已存在的凍結檔不會被命令覆寫。正式入口拒絕 `python -O/-OO`，避免略過驗收 assertions。

## 正式執行與完整重建

只有在 preregistration 已提交並得到執行授權後，使用實際核准的 SHA 與新輸出目錄：

```bash
python -B experiments/spiral_neural/20261113_pro_notice_learning/run_trial.py \
  --execute \
  --manifest experiments/spiral_neural/20261113_pro_notice_learning/frozen_manifest.json \
  --approved-manifest-sha <approved-manifest-SHA256> \
  --out <new-output-directory>
```

此命令會驗證來源／環境／教材／課序未變；三個正式學生全部完成後，用同初始 state 和已凍結課序逐 target 重播，不重抽課序。主程序經原 `Model.lesson()`，重播經獨立 teacher-prefix loop 呼叫原 `Model.step()`；每個預測、loss、p/m/v/birth/t/RNG 及記錄 counter 的 digest 必須一致。重播不是新增學生。

輸出包括初始／固定 epoch／最後完整 checkpoint、訓練曲線及 truth、最終全 18 題 free-run/TF/logits、所有失敗、成本、時序及壓縮逐 target trace。大型 trace 可不加入公開 Git，但保留檔案／未壓縮內容 hash；上述固定命令可在新目錄完整重建。技術中止會保存失敗 state，學習分數不佳不會中止或延長課程。

本輪沒有可用 NVIDIA worker，`nvidia_status=skipped_unavailable`，實際呼叫 0；不將一般模型建議或歷史 Codex 呼叫列為本次成果。
