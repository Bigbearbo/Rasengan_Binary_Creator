# 複習介入與等待對照（2026-11-01）

目標：在不替客體改寫待學槽或 VM 指令的前提下，檢驗「二階待學佔滿」能否透過再次給題完成確認並釋放，讓三階題進入試答。兩組沿用同四片段、同資源費率與出生規則；前八輪皆為種子3，第9至12輪一組只付維持費，另一組給既有二階詞，第13至16輪給相同四道三階題。

全部10個更動檔案：修改 `src/tree_resource_population.cpp` 增加 CleanDelay／CleanReview、十六輪選擇及等待回合；新增 `src/tree_question_review.cpp` 的16組 CSV 入口；新增 `tests/test_tree_question_review.cpp` 驗前八輪一致、等待不出題、守恆及正答；新增 `tests/summarize_tree_question_review.py` 核對256筆與介入前歷史；修改 `Makefile` 增加 O2／ASan 目標；修改 `README.md` 記錄數據；新增 `results/tree_question_review_output.txt` 原始逐輪資料、`results/tree_question_review_test_output.txt` sanitizer輸出、`results/tree_question_review_comparison.md` 整理表及本檔。

實測：O2十六組×十六輪共256盤點與整理腳本 PASS；ASan/UBSan八組×十六輪共128盤點 PASS。所有比較的前八輪人口、餘額與正答相同，等待組第9至12輪沒有執行題目。獎勵12000且不繁殖：等待4存活／4正答／0路由／餘額40900，複習4存活／36正答／16路由／餘額356076。獎勵12000且繁殖：等待4存活／0出生／4正答／餘額40900；複習8存活／4出生／64正答／32路由／餘額596745。獎勵0時兩組最終均0存活；等待4正答，複習12正答，未把暫時多答直接稱生存成功。反轉創始政策順序的最終數值相同。重編原40組 O2 題序結果，480筆與上一版逐字相同。

此介入增加了四道複習題及其可得獎勵，不能把64對4正答全算成「單純修好待學槽」的效益。兩組有相同的總輪數及維持費，但介入組題目數較多；有效的是補完後能在後續三階題繼續試答與路由。仍沒有客體自主選擇複習／暫停／替換，也未接 legacy HP；核心／ISA沒改，6000隨機VM未重跑。
