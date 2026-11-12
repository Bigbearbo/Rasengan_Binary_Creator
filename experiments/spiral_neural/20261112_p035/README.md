# P035：輸入編碼 × 容量時序

這是Pro在PR #8提出的12學生小型篩查，由Codex與受指派agent實作、執行及獨立驗收。來源設計固定於`4e2ded91166a4fd9348dccf8fc71ddf01e991645`；歷史P030–P034結果保留原貌。

SLE-Original與緊湊階層一元binary各搭配固定最終容量F／共同階段成長G，seed101/202/303。兩側共用SLE答案詞，這輪隔離的是**輸入codec × 容量時序**；沒有比較H的最短native輸出或完整系統壓縮優勢。原生SLE NN／VM共用題庫主線不變。

正式實測於台北2026-11-13完成：12名新學生最後已教144/144、未教運算元val+test5/48；主要0..4分數僅S-F/202為3，其餘2，配對interaction0/−1/0。完整重播與獨立checkpoint稽核通過。本批未見SLE特有的成長收益；4/6雖未作訓練運算元，已在Neg教師答案出現，不能稱各角色皆未見。

- [事前規格](P035-事前規格-2026-11-12.md)及[機器規格](protocol.json)
- [實測結果與限制](P035-輸入編碼與容量時序實測結果-2026-11-12.md)
- [開跑前來源凍結](source-freeze.json)
- [獨立工程／NVIDIA審查](review_notes.json)與[執行結果稽核](integration_review.json)

## 課程、預算與判準

五階為Echo data1→data2→data3→只增加op位寬→同形狀增加Neg。每階按外定預算前進，不因答錯卡住教材；全12名學生與失敗均保留。升階後用當前格式測舊語義。data1/data2全教，data3 train0/1/2/3/5/7、val4、test6；這是已曝光研究域，不是新盲測。

F從起點即有L13/H69、2073參數；G沿8/64→10/66→12/68→13/69成長，兩codec同容量序列。原P030權重／Adam／birth與t在擴張當下逐元素保留，後續全網可訓練。每學生training dense MAC上限277,794,000；G在整題邊界實花277,772,868，餘額不carry。MAC不等於硬體總FLOPs；推論、工程、重播與編解碼成本另記。

主要分數0..4為最後當階格式下連續通過的累積里程：Echo0/1、Echo0..3、Echo0..7、Echo與Neg各0..7整串全對。它們是巢狀條件。每seed列`(S-G−S-F)−(H-G−H-F)`，不只挑最好的一格，也不把三seed當精確廣泛估計。

## 重現

使用Python3.12.14與NumPy2.3.5，無需歷史checkpoint或API憑證。原始碼、protocol與reference需保持原bytes；Windows下載／checkout時請關閉自動換行轉換（例如clone使用`git -c core.autocrlf=false`）。驗收會核對SHA，不會默默接受改過的來源。

在本目錄執行，輸出目錄必須全新：

```text
python -X utf8 -B run_p035.py --out <全新工程檢查目錄>
python -X utf8 -B run_p035.py --out <全新實測目錄> --execute
```

預設只做合成工程preflight，含少量可丟棄副本的更新／重播檢查，不做12學生正式擬合；`--execute`才執行凍結的12名學生及完整逐target重播。每次使用全新目錄，程式拒絕覆寫。教師oracle只產標籤／批改，不進學生自由推論；模型僅接raw01與自己的已生成prefix。

完整重播的一致性在同次執行環境驗收；跨平台或不同數值運算環境不承諾checkpoint檔案位元相同。每輪保存實際Python／NumPy版本與來源SHA。

## 證據與來源

公開封存的白名單、逐檔SHA及排除項見PUBLICATION_RECORD與package manifest。保存每階完整起終state、曲線、自由生成／teacher-forcing真值、漂移、成本、曝光帳及重播判定；龐大逐target壓縮trace留本機並列完整SHA，可由上述固定程式重新產生。獨立稽核重算checkpoint輸出，不冒充新學生。

逐學生推論counter含複製template的初始化計數，不是全系統唯一實體operation總數。資料較大的完整彙總／報告索引收在證據ZIP的analysis/，頂層compact提供結果入口。

reference中的P030 Model與main原始Model AST一致；其檔案只保留較早本機路徑整合差異，版本來源見lineage.json。P031的student_io／teacher／reference_codec逐byte固定。H僅是本輪明示的一元階層子集，不宣稱已實作任意遞迴文法。

NVIDIA實派一次公開唯讀候選審查；無依據數字／統計主張經本機反例拒絕，通用公平性提醒另外驗證。公開副本移除機器私密API記錄路徑並列原SHA；原API帳號、quota、憑證及私人對話不發布。

本輪固定預算完成後即停止。下一變因須另立事前規格，不因分數追加seed、改codec、擴容或延長訓練。
