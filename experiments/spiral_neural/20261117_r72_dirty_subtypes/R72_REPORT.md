# R72 — B H110 DIRTY-COPY1 子型覆蓋配對實測（2026-11-17）

事前 Git 凍結：`5d4aed9254ea37888d96172738ab1454bd97b99d`。這輪只改一個因素：R71 B 在 LEFT 混教期間，每批 `hand.sample('DIRTY-COPY1', N=2)` 固定只產 `draft` kind0/1，卻以 0/1/2/3 全四種子型評分；R70 舊技能預訓原本使用四種子型。R72 在同一批64題的奇數批，只改原 DIRTY 兩題（index60/61）的 dirty board 為 kind2/3，保留詞值、標籤、mask、其他62題、原 RNG、所有更新與 Adam 超參數。偶數批完全保留原樣，沒有增加 DIRTY 題次或 LEFT 曝光。**這是 Fable151 候選，不是正式核准 SLE-AE1。**

## 真實 CPU 神經訓練（vs 不重訓的 R71 B 同seed控制）

| seed | R71 B DIRTY/256 | R72 B DIRTY/256 | R71→R72 LEFT/96 | R72 首見 LEFT≥95% | R72 首見 LEFT＋九舊技能共同達標 |
|---|---:|---:|---:|---:|---:|
|101|211|**253**|95→95|2048 updates|4096 updates|
|202|220|**253**|96→96|2048|4096|
|303|217|**252**|96→96|2048|4096|

舊驗證 DIRTY kind2 由 R71 B 的 **28/64、41/64、35/64** 提高到 R72 **62/64、64/64、64/64**。全部9項舊技能末輪 ≥95% 且符合自身起點5百分點保留門檻；joint gate 從原R71 B 0/3 變 R72 B 3/3。LEFT首次達標仍需要2048步，未趕上R71手填A的1024步；joint仍晚於手填A的2048步。R72 paired triad validation 末輪91/96、93/96、90/96，分別相對R71 B的93/96、93/96、90/96，細分指標沒有一律改善。不能把局部改善推成全部手填/初始化優勢消失。

每名 B 真正跑4096 Adam更新、batch64、LEFT32、DIRTY2；三seed合計12,288更新／786,432題次（LEFT393,216），每人262,144題次；H110 21,271參數，前向21,120 dense MAC/row。train96／val16／歷史已曝光test16詞池獨立；合法固定 Fable151 7-bit + trailing0。原 R71 其餘原始位元資料不變，三seed整段源串流SHA與R71原始紀錄吻合，僅各有4096筆 DIRTY x 被更換。全部4096步完成後才看原本已曝光test，非新盲測，不能做模型選擇。

## 獨立驗證和失敗

獨立重新計算 21 份 checkpoint 的舊技能、LEFT paired val 和DIRTY四子型、3份末輪exposed test；另獨立梯度/Adam重播三名學生各首128步，state數值最大差 `2.6367796834847468e-14`，**PASS**。這不是12,288步全程雙路重播。記錄全部seed、失敗、checkpoint/Adam/RNG及原始輸出，不挑最好seed。來源鎖版 `run_r71.py` SHA256 `ddee944f7cf134dea99383a4fd1a69733a13850851cf7aa090bfc41b302c9ff6`；R71固定原封存SHA256 `845a16f768c49f9dcc082365466bd75e8726685dc2c2f38bec652739cdc9e530`。NVIDIA、Windows Codex、Gemini API均 **0** 真正呼叫。

## 可重播證據和限制

Library私人完整ZIP（Fable原始源碼/權重不放公開Git）：

`/SLE_NN_Exchange/archives/sle_nn_r72_b_dirty_subtype_coverage_20261117.zip`

SHA256 `65a74278d625a2f4e26ace2bbdd92a7aefcb65455d78e36b55c510538a6a824a`，9,131,680 bytes，58 ZIP members；原本ZIP CRC及其中57檔SHA逐一PASS。內含 `run_r72.py`、`verify_r72.py`、原始R71/R70來源、預先規格、source states、全部21新增checkpoint和原始bits／FAIL cases。解壓後在隔離副本的根目錄可用 `python run_r72.py --out new_r72_run` 重播；`python verify_r72.py` 驗證封存原結果。不得直接公開私有 Fable ZIP；Windows ACK 由 Dot 獨立查驗。

[更新] 本批 B 遺忘大部分可以透過**零額外題次／相同預算**、補足 DIRTY 四種子型覆蓋修復。[取代] R71 B 只能學 LEFT 卻無法保住舊技能。[原因] 原 LEFT 混教實際上意外漏了 DIRTY kind2/3，而不是全部學會後仍練同一家族。[狀態] 對三組配對觀測高信心，不能廣推到其他網路/正式螺旋語。下一步應以另外的預註冊實驗拆分已學技能保留與寬度/詞數成長；不再重做同一子型補課。

U＝使用者優先「手填＋真學習」與幾題學會效率判準；F＝Fable原件與 R69–R71 checkpoint；T＝本輪三seed真正CPU訓練/獨立數值核算；A＝子型缺席影響遺忘的因果機制解釋。
