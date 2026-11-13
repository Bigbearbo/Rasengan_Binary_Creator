# F2四類續訓事前交接

2026-11-13，Codex。尚未正式訓練。Parent PR28 head5ceec0c42507bb5646dc0d87089f4a86e0e6269c，三fullfinalstate父t297000/400500/441900全承接。參考Pro30 1e4812bd...NEXT_PHASE，這輪只加入op100/r2翻轉前兩詞，原E1/E2/F1全部Q/A不變；兩詞各反5info、各尾0不反，literal30/31答案不執行。

同900四詞bank，3600Q／36000targets每epoch，seed+555000預凍40輪。ALL3先baseline舊三類各900exact才更新，F2診斷不計streak、不選seed。四類各900/900含S兩連勝或cap40；L80H64／原Adam.003不改，保留p/m/v/birth/t/RNG，成本只計新delta。沒有正式全程訓練重播，三seed not_planned／所有replaycost0；只做有界合成工程與全部baseline/epoch/finalTF獨立數值驗算。

新增word1/word2 info／tail／whole、bit／STOP／首錯、逐QID lost/recovered，全部讀生成tokens無額外NN。baseline轉移null，epoch1對baseline。資料／state／課序及中途錯誤完整封存，不挑最好checkpoint。每學生cap1.44M新updates，三人cap4.32M；gradients／raw逐targetloss／optimizer中間state未存不冒稱再算。

下一步完成工程freeze及0NN portablegate，Root公開Git並actual byte回讀後，一次正式批次。只新增本目錄，不重跑舊NN／Pro29/30、不改他人主導航、不合併PR。E3/E4仍未凍結或執行；科學範圍固定900bank下新增F2與舊三類保持。
