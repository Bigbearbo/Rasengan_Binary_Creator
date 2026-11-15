# R57 執行結果｜新 exact-Q 合法 r1/r2 角色配對（固定 checkpoint）

**結果：事前聯合 gate FAIL，4/6 PASS。** R52、R55、R56 在全新完整 raw Q 的測試中均未顯示 value-conditioned gate 的增益。這個結果不是「新數值域」盲測：0..29數值及運算語意已見過，只是96條完整問題未出現在1740條歷史Q中。

事前凍結 [PREREG.md](PREREG.md) Git commit `0a428f23669d4e76b9c26a4c83e2b046cf981716` 已在任何 R57 神經前向之前發表並反向fetch確認。來源 R56 Draft #107（head `793920dab695dba9a8e1fe53010c65fd59cb3723`）；不更動舊 checkpoint、不重訓。唯一新變因：**評估資料從已曝光舊Q移至新 exact-Q 雙角色配對**。48組同一 `a,b,c,d`，每組 r=1/r=2 各一題；16組validation、32組test；每層b低0..5與高24..29各半。80條曝光舊題作retention。合法 `SLE-AE1-n5-v1`，39原生01輸入，答案 6或12 bits+S。

| 完整自由答案包含S | R52固定閘門 | R55條件式斜率 | R56等額續訓固定閘門 |
|---|---:|---:|---:|
| validation，32 Q ×3 | 37/96 | 34/96 | 37/96 |
| test，64 Q ×3 | **54/192** | 50/192 | 53/192 |
| retention，80 Q ×3 | 220/240 | 219/240 | 220/240 |
| test r1完整 | 30/96 | 28/96 | 30/96 |
| test r2完整 | 24/96 | 22/96 | 23/96 |
| test r2第二詞 | 68/96 | 68/96 | 68/96 |
| test r1+r2同組都正確 | 19/96對×seed | 15/96 | 17/96 |

Test逐seed R52=18/16/20、R55=18/14/18、R56=18/16/19 (每seed64條)。R55相對R52新增答對2、失去6；R56新增答對1、失去2。test 兩個b層：R52 22/96低、32/96高；R55 17/96低、33/96高；R56 20/96低、33/96高。STOP結束數均179/192，正確長度且以S結尾均171/192；不等於完整答案正確。三者r2第二詞完全同分，差異主要來自其他生成步驟，不足證明來源權重已經自主識別語義。

事前6 gates：(1) 96條合法新Q與48配對PASS；(2) R55相對R52 test +8/192 FAIL；(3) R56相對R52 test +8/192 FAIL；(4)(5) 每seed比R52至多下降4題PASS；(6)兩種重播全部一致PASS。**沒有調後驗門檻。**

真實執行：三個 Seed101/202/303、三個原 checkpoint，各10,465模型參數（R55另8 frozen gate buffers）；**新增訓練0 update、0 train MAC**。共1,584筆原生01完整回答，自回歸推論17,985次前向、理論 dense inference MAC=196,396,200；PyTorch完整重播1,584/1,584，獨立NumPy重播1,584/1,584，sample logit最大差3.814697265625e-6。raw SHA256 `3875df4209ebf085dae3aea3d799a5a409b61b884d775d151e345e7fd77904c2`。

R57驗收中，凍結runner的 NumPy sampled logit 比較忘了包 `torch.no_grad()`，第一次因 RuntimeError 停止；模型輸出沒有因此更動。保留原runner SHA不變，另設 `r57_verify_erratum.py` 僅修唯讀驗收呼叫環境；重跑 PASS。沒有修改教材、結果、gate或任何權重。負例：`Q=010100010111000001010010100110010111100`，seed101，r1，標準 `111000S`，R52實際 `100000S`。

資料來源／可重播包：`sle_ae1_r57_role_pair_holdout_20261116.zip`，ZIP SHA256 `61a863a0a209a43a15366e62db3b34494d52bd273f191aaddeef304984b82fea`；含來源R56封存351檔逐byte相同、新runner、96題manifest、3組原模型state、1,584條回答、錯誤、雙路重播、公開校驗器、359項SHA驗證清單。本Git紀錄和校驗器不足以神經重播；仍需完整ZIP。原始固定源 SHA：manifest `fb08b8da670c8837fd99ddc54011268f18e00e820dc6b941bfd7200cedaaa420`、runner `fcf5383423c9d586b81606ce0f17217f757a54b1d44f73b9725d2bad758838d3`、prereg `5c5423c442007d06d9a88c51bb2a03a7cf2bbbbb6174755c8152ee020c0b26d3`。

實際執行命令（完整ZIP解壓後在 `r56_workspace`）：
```bash
python r57_role_pair_frozen_holdout.py static
python r57_role_pair_frozen_holdout.py replay
python r57_verify_erratum.py
python verify_r57_public.py /path/to/sle_ae1_r57_role_pair_holdout_20261116.zip
```

U：使用者限定獨立SLE原生01 NN研究、先凍結再驗證。F：原Codex P030～P035／Pro UR1 #12 及 R52/R55/R56 checkpoint；P031 #5僅是共享題庫語義驗證。T：本輪新Q及1,584筆真神經回答、雙重重播。A：條件式gate可改善角色遷移是低信心假設，這批結果未支持。NVIDIA=skipped/no callable authorized worker，actual0；Codex本機=0；Gemini=0。不觸碰Pro/Codex/VM分支、不合併、不上傳私人材料。

**下一棒 owner：獨立 NN 研究員**。保留這批題目為已曝光；建構未見數值/運算元角色域及相同資源的普通二進位對照，再測完整自由輸出、STOP、跨階與舊能力，而非在本組Q後驗調來源閘門。
