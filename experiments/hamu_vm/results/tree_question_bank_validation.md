# 變動題庫及新片段表驗證（2026-11-01）

本批從資源繁殖 ZIP 接續。使用者要求先推進題型與題目。宿主教師明列標準答案，客體仍要根據真實片段輸出、教師回饋、遮罩交集與樹記憶確認；出題函數不替客體選片段或寫答案。

## 全部修改

1. 新增 `src/tree_question_bank.hpp`：題目結構、六種三位函數、教師答案、螺旋詞題目寫入與十二輪交錯／升階課程。
2. 新增 `src/tree_question_experiment.hpp`：兩個可用的片段表組件、任意一位翻轉程式、統一測試配置、十二題資源學習及不同時期兩名後代全資料路由。
3. 修改 `src/tree_resource_population.cpp`：可選變動題庫和有效片段表，舊入口參數預設維持原單題／超時片段；每輪依題目教師算出三位答案。
4. 新增 `src/tree_question_population.cpp`：八組變動題庫的獨立 CSV 執行入口。
5. 新增 `tests/test_tree_question_bank.cpp`：576 個題目格式／答案組合、四詞義課程與 32 個後代路由、換表中位翻轉確認與 8 個後代路由、非法欄位拒絕及資源守恆。
6. 新增 `tests/test_tree_question_population.cpp`：六組族群控制、72 次盤點、實際正答獎勵、出生及關閉繁殖對照。
7. 修改 `tests/summarize_tree_population.py`：加固定或變動題庫模式的敘述，兩模式都核對 96 次盤點與每輪人口／政策／資源／獎勵關係。
8. 修改 `Makefile`：新增兩項 sanitizer 測試和變動族群 O2 執行目標。
9. 修改 `README.md`：記錄新題庫、實測結果及不可歸因界線。
10. 新增 `results/tree_question_bank_test_output.txt`：sanitizer 課程實測輸出。
11. 新增 `results/tree_question_population_test_output.txt`：sanitizer 族群控制輸出。
12. 新增 `results/tree_question_population_output.txt`：八組 O2 的 96 筆逐輪原始 CSV。
13. 新增 `results/tree_question_population_comparison.md`：逐輪驗證後的結果表。
14. 新增 `results/tree_resource_population_recheck.txt`：重新執行舊單題的原始輸出。
15. 新增 `results/tree_resource_population_recheck.md`：同一整理程式核對的舊模式表。
16. 新增本檔 `results/tree_question_bank_validation.md`：修改清單與證據。

## 實際驗證

`make tree-question-bank-test` ASan/UBSan PASS：兩個詞長、所有合法算符碼、八個資料值、六個教師函數共 576 題編碼檢查。十二題中的 10 次有效試答、6 次正答，確認四個詞義；費用 40095，原帳戶仍有餘額。二階三條葉由升階前後代驗 24 答，三階一條葉由升階後後代驗 8 答。替換第四片段為中間位翻轉後，在第三次學習嘗試確認，後代八值路由全對，兩個帳戶守恆。首位翻轉只做教師產題編碼檢查，尚未作片段學習測試。

`make tree-question-population-test` ASan/UBSan PASS：六組十二輪，72 次逐輪核對。`make tree-resource-population-test` ASan/UBSan PASS：原六組控制不變。

O2 `build/tree_question_population` 八組十二輪 96 次盤點均通過；整理腳本再核對每組順序、人口、資源、政策數及 reward×實際正答。獎勵 12000：禁止繁殖最終 4 存活／0 出生／24 正答／260376 餘額，允許繁殖 8 存活／4 出生／40 正答／292699 餘額。獎勵 0：禁止繁殖最終 0 存活／0 出生／4 退場，允許繁殖 0 存活／4 出生／8 退場。創始政策順序反轉時，此次最終數值相同。

O2 原單題 `build/tree_resource_population` 重新執行，移除舊紀錄前兩行 make 命令後，與先前 96 筆資料及 PASS 尾行逐字相同；整理腳本同樣通過。第一次新測試編譯曾有測試輔助函式名稱筆誤，已修正；新中位翻轉測試起初錯誤預期兩次可確認，實際依固定候選選取順序在第三次確認，已調整題序並驗全部後代路由。正式程式無需因上述測試失敗修正。

## 界線

變動族群的片段表全有效，原單題族群有永久超時片段；這兩組同時改了題目和片段可靠性，不能把結果差異單獨歸因題序、題型或政策。不同政策在全有效片段條件下沒有強烈差異，不等於政策普遍等效。課程、算符對應、教師答案、片段表及出生規則都由宿主設定，沒有自動出題、任意寬度擴張、跨階降回二階、客體自行產生片段、嚴格 Zero 或長期演化。本批未改 VM 核心／ISA，也未重跑 6000 隨機 VM 及其餘無關測試。
