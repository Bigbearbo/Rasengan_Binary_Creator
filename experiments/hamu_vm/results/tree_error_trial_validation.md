# 試錯樹與分階題目（2026-11-01）

作者方向：題目是可重複利用的學習資源，環境應在多數個體掌握後才提高難度。先記住每題錯誤選項、避免重複試錯，答對後記住正解；日後才測壓縮。原話及本輪 AI 回應見 `results/conversation_20261101_question_resource.md`。

全部更動：新增 `src/tree_error_trial.hpp`，用 VM TREE_ADD 建題目／選項節點、TREE_ACTION 標正確，遞回查詢優先已知正解、其次未試選項；新增 `src/tree_error_world.cpp`，四個個體的十輪多數升題小環境、每實際嘗試費100／正答回200；新增 `tests/test_tree_error_trial.cpp`，兩題分離、錯答去重、正答回用、後代記憶；新增 `tests/test_tree_error_world.cpp`，多數升題和少數落後；`Makefile` 新增兩項 sanitizer 和 O2 執行入口；`README.md` 記錄結果；新增 `results/tree_error_world_output.txt`、`results/tree_error_trial_test_output.txt`、`results/tree_error_world_test_output.txt`、本檔與對話紀錄。共11個檔案。

測試：`make tree-error-trial-test tree-error-world-test` ASan/UBSan PASS；O2 世界第1題在第4／5／6輪分別有1／2／3隻掌握，第6輪達3/4門檻，升題時1隻落後；第2題第7至10輪逐隻掌握，第10輪4/4。每次作答費100，正答獎勵200，四隻初始資源合計4000，最後餘額3200。沒有在測試外推長期學習或產生新片段。

實作筆記：編譯初版漏 include core 已修；第一次記錯答案時，TREE_ACTION 讀回的 committed 位自然為0，不能用它判定 TREE_ADD 失敗，改核對非零節點 ID；原遞回若遇前方未試選項會過早返回，改為遍歷後優先找已知正解，再取第一未試項。這些修正均經 sanitizer 重跑。

界線：題目鍵與候選範圍仍由宿主給定，客體 VM 只實際保存與查詢樹，遞回選項遍歷是宿主受控演算法，不能稱為倉鼠自主遞回。世界題庫只兩題、每題一個固定答案，沒有隨資料值變動的詞義，也沒有語義歸納、錯誤樹壓縮或長期族群演化。多數升題可能遺下尚未掌握上一題的少數個體，這是本測試可見的取捨。此實驗使用獨立31節點樹配置，不直接改前版容量8的學習個體；核心ISA、legacy HP、嚴格 Zero 均未改。
