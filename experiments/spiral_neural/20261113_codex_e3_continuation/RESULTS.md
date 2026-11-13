# E3 低學習率追加8輪結果

2026-11-13事前設計、11-14完成（台北）。正式與唯一獨立驗收均actualexit0/closed。沿PR47低η三完整state、同900payload/五類4500題/10499參數/原逐bit0.001數學，只增加教學量；全部21個原訓練/統計函數AST未改。

|Seed|起點E3|追加8輪後E3/900|舊題錯誤起點→終點/3600|首次E3全對（新輪次）|五類穩定完成|
|---|---:|---:|---|---|---|
|101|229|900|3→1|8|未達|
|202|54|879|2→0|未觀測|未達|
|303|182|897|8→1|未觀測|未達|

三個模型均第8輪cap停止，沒有任何五類全對輪次，也沒有連2個NEWepoch全對。Seed101只有F2差1題；202只有E3差21題；303 E3差3題、F2差1題。全4500題正確數分別4499、4479、4496。門檻未達不阻止完整公開，也不在看到結果後加輪。

Seed101是在原PR47的一輪加本輪8輪、合計第9個E3教學輪次，首次觀測三詞回音900全對：同900道E3各19個teacher-prefix targets重複教9遍，共8100題次、153900個E3target；不是8100道不同題，亦非從零初始化。當時全部五類合計40500題次/477900逐bit更新，未含更早四類預訓練。其餘seed本次仍未觀測E3滿分。

|Seed|追加各輪E3 whole/900|追加各輪舊題絕對錯數/3600|
|---|---|---|
|101|587, 775, 838, 785, 893, 806, 890, 900|4, 16, 1, 5, 6, 2, 4, 1|
|202|159, 128, 206, 581, 816, 898, 899, 879|0, 10, 0, 2, 4, 2, 0, 0|
|303|130, 376, 447, 662, 739, 826, 854, 897|18, 30, 12, 10, 11, 11, 12, 1|

曲線會回落，沒有挑最好checkpoint作終點。202最好曾899/900（新7），正式終點仍879（新8）。相對本輪baseline，原13個舊錯題全部恢復，但101/303各新增1個不同的F2錯題；所以絕對舊錯由13降到2，不能把淨改善11題說成只修復11題或零新遺忘。derived-readout.json與其固定程式只讀保存tokens，沒有新NN。

實際新工作24×53100=1274400updates、26833766400training dense MAC。物理baseline159524forward、每輪probe1276558、最終TF159300，合計1595382次非更新forward/16643025024MAC。正式命令1810.387372600002秒，約30分10秒，含baseline/訓練/生成/TF/I/O；繼承祖先counter另列，不重新計費。4項本輪mock tests actualPASS、0syntheticNN/up；mock增量265500不是optimizer。

獨立raw NumPy一次重算121500自由生成（3baseline+24epoch各4500）及159300最終TF，全部tokens/flags/scores/逐詞補0/STOP/首錯/QIDchurn/stop曲線strict一致，TF logits/probabilities/CE逐值exact。180science/63NPZ、30proof、來源輸入/receipt/log前後SHA通過。實際1595382F/16643025024MAC、0optimizer/0replay，內部74.1493175秒，含程序啟停74.42031029998907秒。自由生成rawlogits未保存；中間gradient/loss/權重軌跡未獨立重播，digest不是optimizer重播證明。

事前Git commit7e863b21c2a0cc2af0630625ba6d784bd569835e（PR49建立15:55:24Z），root執行意圖15:57:58.333Z，均早於本輪任何NN；原9事前檔逐byte快照保留。manifest3db5f30d1f32f47333674ee8eb456851087e62b4b49d8c331b318042fb7b8794；inputs23members/4452849B/SHAe2889728eccb95498df95cdcfdcf64e7eed5a9151b1e056f4d7c516ba3e1fde7。Parent47 result60ffaee62ab582f7ead926c064ba7e454e2f3018。

獨審post SHA f02b98d69870a91a4e5ccf911893f14ff45fd4bdb59c06d8798699f258f655d4，source e6508be9afe54b3cd2a770accdd22b77f9d27e04613b1f4a83713f857105c16c。正式7392/驗收49357均closed。完整state/答案/TF/課序/metadata集中在有成員SHA/CRC索引的ZIP，減少根目錄重複檔案。公開command/0僅機器個人路徑替<python>，有映射原/新SHA；local原件未改。

這是三個已接觸900payload的選定低η續教state，證明一個state能擬合本E3題庫，沒有證明新題泛化或所有seed都學會。沒有單獨比較其他η或容量，不能將殘差斷定為容量/位置限制。8輪後仍有非單調波動，下一問題可以另設計收斂階段步幅或錯題教學，但本輪不調參、不追加、不進E4，沒有自動merge。NVIDIA一次有限合成候選因schema不符拒絕，研究採納0；Gemini原工具隔離未解明列skip。
