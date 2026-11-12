# 無效片段恢復驗證（2026-10-31 Asia/Taipei）

來源：hamu_vm_observed_cost_20261031.zip，工作入口 version 11。

## 本輪全部更動

src/tree_observed_vm.hpp：新增 tree_observed_recover_choice_program，核對當前待學上下文及觀測格式，將存活遮罩與本批觀察有效位求交集，由客體輸出第一個可試答索引。不修改存活遮罩。

src/tree_observed_learner.hpp：入口新增預設 false 的 recover_invalid 參數；原選中項無效時，可把本批有效實際輸出存入觀察記錄，再執行客體恢復選擇。宿主核對返回索引屬於請求且實際有效，再按該輸出評分。結果新增 recovered 欄位。沒有可用項時保留無效結果；恢復程式中斷返回 nullopt 並清空輸出。

tests/test_tree_observed_learner.cpp：保留預設策略原有測例，新增無效首項→XOR1 錯答→COPY 正答的兩輪恢復、未知項保留所以不可確認、已淘汰項不再觀察、全部無效不得提交、恢復選擇中斷不得留下輸出或更新遮罩。

README.md：加入新入口、預設值、證據及限制。

results/tree_observed_recovery_cost_regression.txt：本輪重新執行既有成本對照的原始輸出。

results/tree_observed_recovery_validation.md：本紀錄。

## 本輪實測

make tree-observed-learner-test：ASan/UBSan PASS。首次新增恢復測例通過；再新增中斷測例後通過，沒有因測試失敗修正正式程式。仍含原 64 次隔離觀察、40 次路由、舊批次拒絕及其他無效證據測例。

make tree-observed-cost-benchmark：O2 PASS，12 批相同題序，逐輪結果、遮罩、最終樹及 768 次親代／後代路由驗證一致。因預設恢復關閉，這是既有策略回歸，沒有量出恢復策略的成本優勢。每批全觀察／請求的總 VM 步數仍分別 37819／39083，觀察次數仍為 40／26；本次平均秒數 0.0114259／0.0102424。時間僅為本機小樣本，不推廣為一般效能。

本輪未改核心或 ISA，沒有重跑 6000 隨機 VM、舊四候選或寬度學習測試。先前 PASS 紀錄保留為歷史證據。

## 界線與下一步

恢復只是從現有觀察中選另一個有效試答，不會增加片段庫、改寫基因或把執行失敗解作詞義錯誤。所有可選片段均已實際執行，沒有宿主語義預測公式。固定優先順序仍存在，未知且永遠無效的候選仍會阻礙唯一確認；這是證據不足，而非已完成未知詞義判定。

下一步可測暫時性失敗後重新有效的候選能否恢復完整確認與綁樹，並比較恢復開關在同一失敗序列中的作答／觀察／客體成本。HP 計費尚未實作。
