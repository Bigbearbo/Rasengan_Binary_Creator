# F2 CPU 一輪穩定性實驗結果

2026-11-13，Codex。正式執行與唯一獨立驗收皆已實際 exit0 並關閉。

從 PR33 三個首次四類全對的完整 checkpoint，沿用原下一輪凍結課序，只把 Adam 學習率 0.003 改為 0.001。模型仍是 L80/H64、10499 參數，教材仍是 900 組 N4 payload、回音1詞／2詞與翻轉1詞／2詞共3600題。保留原 p/m/v/birth/t/RNG/events 與計數。

| Seed | 起點→下一輪 | 歷史0.003流失 | 新0.001流失 | 新E1/E2/F1/F2整題正確 |
|---|---|---:|---:|---|
|101|19→20|7|0|900/900/900/900|
|202|22→23|5|0|900/900/900/900|
|303|19→20|52|0|900/900/900/900|

事前主要假說「每個 seed 都嚴格少流失」通過，未使用合計分數替代逐seed判準。基準四類全對，因此新臂沒有任何新失誤；相對歷史臂只修復其7/5/52個錯誤QID，所有逐題交集都保存。三個新臂生成的10800道整題、16200個輸出詞、81000個資訊bit、16200個補零與10800個STOP全部正確；正確前綴下的108000個最終TF target也全對。生成時接回自己的輸出，沿用cap32和L80 guard，沒有按正解長度截斷或強迫STOP。

正式成本：單一命令／三條新primary／各36000逐bit更新，共108000更新，training dense MAC2274048000；三baseline、新臂生成、最終TF共324000次非更新forward／3379968000 MAC。完整optimizer重播0；歷史控制直接引用已公開結果，不算新訓練。原NumPy CPU完整命令197.79170689999592秒（約3分18秒，含baseline、新生成和TF；不含封存及獨立驗收）。合成工程測試另有3次更新／3forward，不混入正式成本。

解讀：在這三個已看過題庫、事後挑選的首次全對state，較小步幅能保住下一輪已會的答案，支持下一步採低步幅繼續設計混合教材。這不是未見題泛化或長期最佳學習率證據，也沒有測量新教材所需題數。原PR33官方終點不變，E3/E4與更長期穩定性仍未執行。

事前封存 commit dbebad71af32ea208dd85171347a4185e2e7e23d，PR43建立於12:32:44Z，root執行意圖12:33:48.751Z，均早於本輪任何正式forward。manifest SHA1079366438d667f7bce2ac8fce983792b6c7bf935f4a200fb9eda4e9612e328c，inputsZIP SHA46f14f6e233ed6f6304c9c0a01779c653647c2f40ae60c57ab4e5d7661f0dc79。

獨立驗收：一次 pure NumPy、零optimizer／新學生／外部呼叫，重算32400道baseline／新臂／歷史control自由生成與108000個新臂TF targets；共432038forward／4507020416denseMAC。101歷史control實際生成多38個token，已逐次計費，沒有補case。內部驗收計時24.542572799997288秒，含process啟停的實際命令24.825394800005597秒。48份science／18個NPZ、25欄完整state與所有來源／ZIP／receipt／logs前後hash均通過，15份numericproof保留。自由生成的全部tokens／flags／scores及詞／資訊位／尾零／STOP／首錯／QID配對讀數strict exact；logits／probabilities／CE逐值比對專指108000個TF位置，其prefix／target／metadata也exact。自由生成raw logits未保存。沒有獨立optimizer／gradient重播；中間逐target loss／gradient與權重軌跡未重建，digest不是重播證明。

獨立報告SHA671d7684c4b1196f792844b5753d941387a99323ff577473240c2049479b80f4；auditor來源SHA443ad00cb9cebe94c6cc5e22602f139586c35c7310e48623e21d515b2e72aacc。正式session68762／驗收session85755皆actualexit0且closed。

外部隊員：NVIDIA單次真呼叫的算術候選未通過，研究採納0項；Gemini因既有analysis-only工具隔離未解而明確略過，沒有重送或重登入。詳見EXTERNAL_REVIEW.json與external-method-checks.json。公開執行命令副本只將含個人目錄的Python executable路徑替為<python>，原檔仍由本機audit核hash；public-redactions.json列出原／公開副本SHA與唯一JSONpointer，不把這份副本宣稱為原檔逐byte相同。
