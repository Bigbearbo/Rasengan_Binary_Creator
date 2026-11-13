# E3 一輪學習探測：有進步，但零舊題流失門檻未達

2026-11-13，Codex。先於Git封存設計與輸入，再單次執行CPU，最後做唯一獨立raw NumPy驗收；正式與驗收都已actualexit0並關閉。科學主要門檻為not_met，工程與數值驗收為PASS，兩者分開記錄。

起點三模型的舊E1/E2/F1/F2各900全對，新E3冷整串全為0/900。沿同900N4payload新增Echo參數3，舊3600Q/A原樣保留；兩臂從同一完整baseline state、同一53100target順序各教一輪，只改step的0.001／0.003，仍L80/H64、10499參數、原NumPy CPU。

|Seed|0.001 E3全對/900|0.001舊題流失/3600|0.003 E3全對/900|0.003舊題流失/3600|
|---|---:|---:|---:|---:|
|101|229|3|240|23|
|202|54|2|76|32|
|303|182|8|33|74|

事前主要判準要求0.001三個seed都舊題流失0且E3whole>cold。三個新題都進步，但三個都有舊題流失，因此主門檻false/not_met。0.003同公式也未達。冷分數均非900，沒有天花板不可識別個案。所有6臂恰一輪，沒有追加、換seed或選最佳checkpoint。

0.001在這三個起點均比0.003少流失舊題；新E3分數則101/202是0.003較高、303是0.001較高，不能用合計分數取代逐seed取捨，也不能說高η一定學得快或低η普遍最佳。三詞回音尚未達900全對，本輪一epoch不能證明它學不會，更不能單獨歸因模型容量或特定內部位置機制。

|Seed/臂|自由生成詞1/詞2/詞3完整正確（各900）|自由生成S位置正確/900|TF第三詞資訊bit正確/4500|TF S正確/900|
|---|---|---:|---:|---:|
|101/eta001|900/900/229|899|3620|900|
|101/eta003|900/890/240|820|3690|900|
|202/eta001|900/900/54|899|3116|900|
|202/eta003|900/850/76|890|3082|900|
|303/eta001|900/897/182|854|3647|900|
|303/eta003|893/839/34|883|2993|898|

冷E3在正確前綴下第三詞資訊bit皆0/4500；一輪後已升到表列水準，顯示逐bit已有可量化進步，但整串仍受第三詞及部分前詞／STOP錯誤影響。TF每一步提供正確先前答案，不能當作自由生成成功；自由生成只接自己的輸出，cap32/L80 guard，沒有按正解長度截斷或強迫S。每詞5資訊bit+0，沒有省略第三詞補0。

正式新工作6×53100=318600逐bit更新，training dense MAC6708441600。共用baseline只實際3份，188726forward；6臂生成318639forward；最終TF318600forward；合計825965次非更新forward／8616466880MAC，原有祖先counter不重新計費。正式命令459.7506418999983秒，約7分40秒，含baseline/訓練/生成/TF與I/O，不含事前封存或獨立驗收。工程另3次合成更新／3forward／63168trainMAC；210600是mock counter增量，非NN呼叫。

唯一獨立raw NumPy驗收重算40500完整自由生成（3×4500baseline＋6×4500endpoint）及369900個TF位置（3×17100cold＋6×53100final），825965forward／8616466880MAC、0optimizer／重播／外部呼叫。全部tokens/flags/scores與派生詞/bit/S/首錯/QID讀數一致；logits/probabilities/CE逐值exact專指保存的TF位置，free rawlogits未保存。90份science／33NPZ、27逐點proof與全部來源/ZIP/receipt/log前後SHA通過。驗收內部47.4331224秒，含程序啟停47.65823320002528秒。沒有重建中間逐target gradient/loss/權重軌跡，trace digest不是optimizer重播證明。

事前commit beca9c77e774318accf9a78ea971ae5aec620d4d，PR47建立15:00:10Z，執行意圖15:01:20.222Z，早於本輪任何正式NN。manifest SHA5e2b3e6eb90c20a27c12ff9d743c8f0ab65a759fff4d561c6d156b535497c8bc，inputs926204bytes/22members/SHAb658716bd3e4bba693ab33c26e429f406fc326fe220bfa1679cb5fb446ff4efc。原24檔完整快照在preregistration.zip；DESIGN.md保留事前原文。

獨立報告SHA1e10c3df8fd3039ea9abce5f9a9a15c69b3af492dbfaec4dbd8a9e5597f91292；auditor SHA cff693544debfa6bbd730af6df20fe3bed2be7c667b2c6e2714879a2b2c8bc30，vendored純NumPy來源443ad00cb9cebe94c6cc5e22602f139586c35c7310e48623e21d515b2e72aacc。正式session1057／audit48104均closed。

限制：三個既有已接觸900payload的選定state、一輪固定課序、沒有新盲測或長期穩定性結論。PR44–46是另一PyTorch cohort，本輪沒有混入。PR43原始滿分state及兩學習率全部新分支都保留，沒有自動挑一個新官方終點。E4、更長期教學或新泛化題庫都待另外設計，本輪不追加。NVIDIA一次候選錯誤總成本算式已拒，研究採納0；Gemini因既有工具隔離未解略過，未重送/重登入。公開命令副本僅把含個人目錄的Python executable欄位替<python>，以public-redactions.json記原/新SHA與pointer，本機原件未變且已audit。
