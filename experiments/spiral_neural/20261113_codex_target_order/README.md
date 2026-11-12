# UR1 target 更新次序診斷

本輪已完成並獨立驗收。固定原序控制的已教分數為7/12、5/12、5/12；target洗牌後為11/12、12/12、11/12（合計17/36→34/36），保留搭配仍各0/6。強擬合gate通過1/3，整組未通過；這批改善限於已教擬合，沒有完整組合泛化。完整成本、固定96/128穩定性及所有失敗見[RESULTS.md](RESULTS.md)。

唯一變因是把每 epoch 原12題共212個 teacher-prefix/target 配對全部洗牌。原 Pro 七份科學來源、模型、教材、Adam、三個初始完整 state、128 epochs 與 training dense MAC 全部保留。控制組重用固定結果；Codex Windows 重現不是另一份獨立科學證據。

`protocol.json` 是新事前規格。driver 必須以 `--source-root` 指向原 source repo、`--control-root` 指向已驗控制結果。所有模式都要求全新 `--out`。不會自行呼叫外部模型。

1. `python -X utf8 -B run_target_order.py --preflight --source-root SOURCE --control-root CONTROL --out NEW_CHECKS`：7次合成 optimizer 更新，0正式 target 更新、0正式 heldout 神經評估。
2. `python -X utf8 -B -m unittest -v test_target_order`：離線結構與合成介面測試。
3. `python -X utf8 -B run_target_order.py --make-manifest --source-root SOURCE --control-root CONTROL --out NEW_PREREG`：凍結 pool、三份完整128×212課序與其 SHA、初始 NPZ、原來源與控制證據哈希。
4. 對可審 manifest 完成獨審及 Git 事前提交後，才允許一次 `--execute --source-root SOURCE --control-root CONTROL --manifest NEW_PREREG/manifest.json --approved-manifest-sha SHA --out NEW_SCIENCE`。

正式入口會先完成三條 primary，再完整重播三條，最後才離線重算18 checkpoint×18題。每個 target 留 prediction/loss/完整 state hash／metadata/counters；checkpoint與最終 p/m/v/birth/t/RNG 直接逐元素比較。失敗保存 evidence 並停，不自動重跑。

主要結果是 epoch128 已教 whole/address 和相對固定控制的逐seed差；strong fit要求每seed兩者皆12/12。附列96/128穩定性及所有保留題。六題保留組合已查看，是曝光診斷，不能稱新盲測。相同 training dense MAC 不表示推論、IO或總牆鐘成本相等。

## 已固定的公開輸入

新事前提交`042bb1097a63da9b39d2d30cc63843d4467c4b83`先公開全部課序、pool及三份完整初態；新manifest SHA256為`db37000543b4e8e7ef4b294883ad2346fddfd61b771a17857a1c525f1df189cc`。原Pro課程與結果來源為`0b6de1d24481c2886833e412d173645fca98609c`／`19ece2819c6c2c1d7ef9fdb2389efaa045b1c35e`。本次Codex實作／執行和Pro原設計／候選分開記。

公開控制輸入只有實際需要的12檔，先還原到全新目錄：

```text
python -B export_results.py restore-inputs --archive baseline-inputs.zip --manifest baseline-inputs-manifest.json --approved-manifest-sha 51253e19dd24e69594b5233ec601dac94b30126a9be186d7bced2c3b3191e015 --out NEW_CONTROL
```

後續用`NEW_CONTROL/baseline`作`--control-root`，以repository根目錄作`--source-root`，以`prereg/manifest.json`作`--manifest`。還原先核全部成員SHA／路徑／NPZ有限值，拒絕覆寫。已在禁止讀取原本機輸入目錄的新根目錄實際驗過manifest。

三位新學生與三條完整逐target重播已完成；獨立只讀審查另核81,408筆target及18 checkpoint×18題，沒有額外optimizer更新。公開選擇完整checkpoint／truth／曲線／失敗與驗收證據，大型target trace保留本機並公開SHA，可用同一固定入口在新目錄完整重建。
