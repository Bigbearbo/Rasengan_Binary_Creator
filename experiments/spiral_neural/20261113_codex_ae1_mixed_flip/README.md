# 三種題混合續訓

2026-11-13，Codex，事前版本，正式訓練尚未開始。直接接續[PR26](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/26)結果commit `7213cce112a8411b13dc128c49f9e88acfc9d65f` 的三份完整finalstate，不另開新學生。原P030 Model AST、Adam0.003、L80/H64／10499參數不變，保留p/m/v/birth/t/RNG及所有舊計數器。

選定格式為 `SLE-AEM1-n5-v1`：`01 + 三bit題型 + 四bit組數參數 + 四個六bit資料詞 + END111100`，Q39位。題目普通資料ID0..29，每詞五資訊位加尾零；沿用原900組bank，前兩詞全30×30組合、後兩詞固定seed331000。同一payload配三個題型，各900題，共2700 Q。

|類別|題型碼|組數參數|答案|
|---|---|---|---|
|E1 新回音1|010|0010|第一個完整六bit詞，然後S|
|E2 新回音2|010|0100|前兩個完整六bit詞，然後S|
|F1 翻轉第一組|100|0010|第一詞的五資訊位反碼，加尾零，然後S|

舊E1/E2的Q與A逐bit不變，沒有位移或換題。Flip100只在本輪明確選定profile生效，不混用舊numeric Zero100／Neg010語義。翻轉ID0答`111110S`，ID1答`111100S`；答案位串是字面內容，不執行UP或END。只有外部S停止，沒有控制碼過濾、正解長度截斷、強制STOP或給學生解碼特徵。固定cap32、L80 guard，最長待預測prefix70；正解STOP prefix E1/F1=45、E2=51。

正式批次先做三個parent的全部2700題baseline。全部三模型的E1/E2都各900/900，才開始任何新optimizer更新；否則integration abort，0新更新、不修權重或替換parent。baseline F1是新題冷啟動診斷，成績不影響課程或streak；baseline只增推論計數，學習state保持精確不變。

每輪所有target集合全域洗牌：每pair依E1、E2、F1及其答案位置建立canonical pool，用各seed+444000 RNG預先凍結40份實際(QID,pos)排列。每輪24300更新，類別6300:11700:6300；題數相同但更新權重不平權。訓練給正確前綴CE，輪末自由生成只接模型自己的輸出。三類均900/900含S、連續兩輪才提前停；任何miss清零，最多40輪，無追加或最好checkpoint選擇。

每seed最多972000個新更新／20466432000 training dense MAC。舊global t151200／181800／223200及其舊MAC保留但不重算新成本；新訓練、baseline／probe／最後TF推論用parent差額報告。每新target21056 MAC、每非更新forward10432 MAC。三primary後只seed101完整重播baseline與全部實際epoch；202/303 not_planned。最後三模型各2700題／24300個TF targets，重用最後free輸出，不探測Flip2、r3/r4。

完整parent checkpoint原bytes／公開archive/blob/member出處、bank、Model source、protocol、三份完整40輪課序事前凍結。每輪完整state、全部輸出、streak／stop、loss/prediction digest全保留。未存逐target原始loss／中間gradient或獨立replay state副本，不宣稱獨立重算那些。engineer、baseline、primary、replay、TF與audit成本分列；MAC是矩陣結構計數。

科學範圍是900組固定題庫下新增F1並保持E1/E2，非盲測、一般copy／內部router證明或單一因果機制識別。900不是全部30^4四詞payload。Git事前byte回讀與獨立0NN portable gate後才啟動唯一正式批次；公開SHA本身不是授權，coordinator負責當前使用者授權與版本核對，不自動合併PR。
