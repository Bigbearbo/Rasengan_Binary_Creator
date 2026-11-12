# UR1 target 更新次序診斷

唯一變因是把每 epoch 原12題共212個 teacher-prefix/target 配對全部洗牌。原 Pro 七份科學來源、模型、教材、Adam、三個初始完整 state、128 epochs 與 training dense MAC 全部保留。控制組重用固定結果；Codex Windows 重現不是另一份獨立科學證據。

`protocol.json` 是新事前規格。driver 必須以 `--source-root` 指向原 source repo、`--control-root` 指向已驗控制結果。所有模式都要求全新 `--out`。不會自行呼叫外部模型。

1. `python -X utf8 -B run_target_order.py --preflight --source-root SOURCE --control-root CONTROL --out NEW_CHECKS`：7次合成 optimizer 更新，0正式 target 更新、0正式 heldout 神經評估。
2. `python -X utf8 -B -m unittest -v test_target_order`：離線結構與合成介面測試。
3. `python -X utf8 -B run_target_order.py --make-manifest --source-root SOURCE --control-root CONTROL --out NEW_PREREG`：凍結 pool、三份完整128×212課序與其 SHA、初始 NPZ、原來源與控制證據哈希。
4. 對可審 manifest 完成獨審及 Git 事前提交後，才允許一次 `--execute --source-root SOURCE --control-root CONTROL --manifest NEW_PREREG/manifest.json --approved-manifest-sha SHA --out NEW_SCIENCE`。

正式入口會先完成三條 primary，再完整重播三條，最後才離線重算18 checkpoint×18題。每個 target 留 prediction/loss/完整 state hash／metadata/counters；checkpoint與最終 p/m/v/birth/t/RNG 直接逐元素比較。失敗保存 evidence 並停，不自動重跑。

主要結果是 epoch128 已教 whole/address 和相對固定控制的逐seed差；strong fit要求每seed兩者皆12/12。附列96/128穩定性及所有保留題。六題保留組合已查看，是曝光診斷，不能稱新盲測。相同 training dense MAC 不表示推論、IO或總牆鐘成本相等。
