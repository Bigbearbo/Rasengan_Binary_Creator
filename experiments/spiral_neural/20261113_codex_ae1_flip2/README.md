# F2：四類混合續訓

2026-11-13，Codex，事前版本。參考[PR30下一階段設計](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/1e4812bd48404c8c03f659ed8a8d86dd5aa5852e/experiments/spiral_neural/20261113_window_progress_review/NEXT_PHASE.md)，本輪只加入翻轉兩組F2，保留E1/E2/F1。E3/E4留待另輪凍結。本輪尚未正式執行。

父版本是PR28結果 `5ceec0c42507bb5646dc0d87089f4a86e0e6269c`，沿用三份完整finalstate，父t=297000／400500／441900，p/m/v/birth/t/RNG及舊計數器原樣保留。原P030 Model AST、Adam0.003、L80/H64／10499參數不變；新成本用父狀態差額。

同900個四詞payload、Q39位、每詞五資訊位加尾零，普通輸入ID0..29。新profile `SLE-AEM2-n5-v1` 保持原2700個Q/A bitexact，僅新增Flip100、r2（參數0100），QID2700..3599。回答前兩詞各自的五資訊位反碼，兩個尾零不反，最後模型自行產生S。

|類別|題型／參數|題數／輪|targets／輪|
|---|---|---:|---:|
|E1|010／0010|900|6300|
|E2|010／0100|900|11700|
|F1|100／0010|900|6300|
|F2|100／0100|900|11700|

F2資料[0,1,23,11]應答`111110111100S`，兩個語法零在答案位置5、11，S在位置12，含S共13動作、STOP前輸入51位。答案中111100／111110是字面內容，不執行END／UP，不濾掉輸入0/1。只有外部S停止；raw Q＋已答前綴進NN，沒有解碼特徵或正解長度截斷。沿用cap32／L80 guard，最大待預測prefix70。

正式批次先對全部三模型各做一次四類baseline，驗證舊三類各900/900後才有任何新optimizer；失敗則integration abort、不修權重或換parent。F2是新接線的冷啟動診斷，不依PR30的0／0／1選種、換課或計streak。這是本輪一次baseline，不重跑PR29/30的其他研究。

每pair依E1/E2/F1/F2、各答案位置含S建立canonical pool。以各seed+555000 RNG預先凍結40份實際(QID,pos)排列；每輪3600 Q、36000 targets全域洗牌，類別target權重6300:11700:6300:11700，無長度平權。訓練使用正確前綴CE，輪末自由生成接模型自己的輸出。四類各900/900含S連兩輪才提前停；任何miss清零，最多40輪，不追加／挑最好checkpoint。

新增逐詞資訊位／尾零／整詞、各bit、STOP位置、首錯位置及逐QID正→錯／錯→正統計，全部只讀已有生成字串，0額外forward。首錯以expected A+S逐token比對，0起算；早S／缺token／多token／cap及context失敗明列，缺位算錯。Baseline沒有前一點，轉移為null；第一輪對baseline，後續對前輪，不能用淨分差代替轉移數。

每seed新更新cap1440000／30320640000 training dense MAC；三primary最多4320000／90961920000。每target21056 MAC、非更新forward10432 MAC。沿用已驗證learner，本輪不安排完整訓練重播，三seed均not_planned，replay成本全0；工程僅有界合成接續／步驟重現。獨立rawNumPy驗算全部實際baseline、epoch和最後TF（每學生36000targets），不重生最後free輸出。未存的逐target原始loss、中間gradient／optimizer軌跡不宣稱獨立重算。

完整parent原bytes／公開出處、bank、source、課序在事前包；每輪fullstate、全部輸出、trace digest、成本與停止均保留。MAC只計矩陣結構，並非硬體總FLOPs；209980bytes陣列不是程序RAM峰值。正式開始前完成Git byte回讀和獨立0NN portable gate，coordinator負責使用者授權及版本核對；公開SHA本身不是授權，不自動合併。

範圍是同900組bank下補齊F2並保持舊三類。900不是全部30^4 payload，沒有heldout、E3/E4、Flip3或長度外推測試，也不識別通用copy／flip算法、內部router或課程因果優勢。
