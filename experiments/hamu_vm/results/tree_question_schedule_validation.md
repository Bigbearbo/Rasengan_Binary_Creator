# 同片段表與同題集合重排驗證（2026-11-01）

本批接續 `hamu_vm_question_bank_20261101.zip`，目標是排除前版比較同時更換題序及永久超時片段的混雜，並觀察相同題目重排是否改變有限資源下的學習與繁殖。

## 全部更動

1. `src/tree_question_bank.hpp`：新增五種確定性同題集合重排，二階前八題與三階後四題分別置換，保持單向升階；拒絕無效種子或輪數。
2. `src/tree_resource_population.cpp`：明確列出 LegacySingle、CleanSingle、CleanVaried、CleanPermuted 四種排程；有效片段表組在學習前先嘗試已確認樹路由並計入正答獎勵；逐輪增加確認及路由正答計數。舊三參數和四參數 bool 入口保留，原單題路徑不變。
3. 新增 `src/tree_question_schedule_comparison.cpp`：同四有效片段下固定題／變動題的16組 O2 CSV。
4. 新增 `src/tree_question_order_experiment.cpp`：同十二題五種順序的40組 O2 CSV。
5. 新增 `tests/test_tree_question_schedule.cpp`：八組 sanitizer 條件、96次逐輪帳本、確認後路由、出生開關與正答回饋。
6. 新增 `tests/test_tree_question_order.cpp`：四個新種子的十二題多重集合相同、詞長順序、拒絕非法種子，以及八組 sanitizer 族群、96次盤點；驗本設定下順序改變出生。
7. 新增 `tests/summarize_tree_question_schedules.py`：16組192次逐輪重新核算與對照表。
8. 新增 `tests/summarize_tree_question_orders.py`：40組480次重新核算，並對照種子0的96筆與前一個同片段比較完全一致。
9. `Makefile`：新增上述兩項 O2 實驗及兩項 ASan/UBSan 測試入口。
10. `README.md`：更新可重跑入口、數據、原因與界線。
11. 新增 `results/tree_question_schedule_output.txt`：同片段16組原始逐輪資料。
12. 新增 `results/tree_question_schedule_comparison.md`：16組結果及限制。
13. 新增 `results/tree_question_schedule_test_output.txt`：sanitizer 測試輸出。
14. 新增 `results/tree_question_order_output.txt`：40組原始逐輪資料。
15. 新增 `results/tree_question_order_comparison.md`：五順序結果及限制。
16. 新增 `results/tree_question_order_test_output.txt`：sanitizer 測試輸出。
17. 新增 `results/tree_question_population_routed_output.txt`：舊變動題庫獨立入口按新路由規則重跑的96筆。
18. 新增 `results/tree_question_population_routed_comparison.md`：上述96筆重新核算。
19. 新增 `results/tree_question_population_routed_test_output.txt`：原變動族群六組 sanitizer 回歸輸出。
20. 新增 `results/tree_resource_population_control_recheck.txt`：原單題六組 sanitizer 回歸輸出。
21. 新增本檔 `results/tree_question_schedule_validation.md`：本批全項清單、測試、數字與限制。

## 測試與修正

`make tree-question-schedules-test`：ASan/UBSan 八組、96次盤點 PASS。`make tree-question-orders-test`：ASan/UBSan 四個新順序的逐題集合驗證、八組族群、96次盤點 PASS。原 `make tree-question-population-test`（六組72次）與 `make tree-resource-population-test`（六組72次）重編重跑均 PASS。兩項 O2 實驗各16組192筆與40組480筆，兩個新整理腳本核對人口、政策、獎勵、資源及單調累積均 PASS，種子0與同片段變動題的96筆逐欄一致。原單題 O2 重新執行，與前版 `tree_resource_population_recheck.txt` 逐字相同。原題庫編碼單元測試和6000隨機VM本批未重跑；核心與ISA沒改。

順序測試最初把「每個種子都應出生」作為假設，種子3實測為0出生而失敗；取消該錯誤前提，改驗確實存在順序差異並保留兩個0出生條件。最終 sanitizer 測試與 O2 都通過。正式程式沒有因這個失敗改動。

## 實測對照

同四片段表的固定題在獎勵0且禁止繁殖時，十二輪4存活、48正答、其中44次樹路由、餘額113247；變動題0存活、20正答、0次樹路由、餘額0。固定題開繁殖時即使獎勵0仍有8存活、4出生、88正答、84次路由；此結果是反覆命中已學同一題的低成本路由，不能稱為廣泛學習或「永生」。獎勵12000、開繁殖時，固定題8存活／4出生／88正答／餘額1109207，變動題8存活／4出生／56正答／餘額476603。

在五種完全相同十二題的順序下，獎勵12000且開繁殖時：種子0、1、2依序為56、48、40正答，均4出生／8存活；種子3、4均4正答、0出生／4存活。後兩組確認計數各4、路由正答0，不能把存活4隻當成較好的學習。無繁殖的五種順序高獎勵正答數為32、28、24、4、4；零獎勵下部分順序也未耗盡，反映題序和未答題成本的交互作用。這證明同題集合在這個固定時間窗／成本與待學槽規則下有順序敏感性；未確定各順序的一般好壞。

[更新] 變動題庫高獎勵開繁殖的正答由前版40變56、餘額由292699變476603；[取代] 前版在已綁樹後仍只跑學習回合，沒有計入路由答案；[原因] 新版本先執行客體樹路由並對真實正答給獎勵；[狀態] 高，96筆新舊資料分別保留並核對。舊文件 `tree_question_bank_validation.md` 的40正答屬舊執行規則的歷史數值，不能當成新版本結果。

## 邊界

固定與變動題序的對照共用候選表、費率、出生規則，但固定題只練一種語義且反覆命中，變動題同時有四個語義。真正只動順序的五組比較保留所有十二題與前後階段，但仍只是一套人工課程、一組常數費率、十二輪與兩個待學槽；後代繼承既有記憶與片段表，沒有自主產題或發現片段。評分為宿主教師，資源帳戶未接 legacy HP，題目無外部隨機性。路由失敗後再學習可能多付嘗試費；兩組同表比較均按此相同規則。沒有證明長期演化、一般最優課程或跨階降回二階。
