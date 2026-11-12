# 客體選項決策驗證

2026-11-01。接續 guest_write 版本。更動：`src/tree_compact_reference.hpp`、`tests/test_tree_compact_reference.cpp`、`README.md`、本報告、`results/tree_compact_guest_choice_run.log`、`results/conversation_20261101_guest_choice.md`。

VM 查題目節點，按 ID 讀取十二位附帶資料。成功旗標存在時輸出已知答案；否則依序跳過標記錯誤的選項，輸出第一個未試選項；全部錯誤時不寫輸出。宿主只讀取四位輸出（存在位及三位答案），不再決定下一選項。題號、評分回饋、參考模型的布局檢查仍由宿主提供。世界既有路徑尚未接入。

ASan／UBSan 三項 PASS：`tree-compact-reference-test`、`tree-error-trial-test`、`tree-error-world-test`。七題每題八個錯誤，已知答案重用、後代繼承，以及節點 ID31 的錯答及正解回讀；測試結果見 `tree_compact_guest_choice_run.log`。未重跑6000隨機 VM 客體。核心 ISA 未修改。

[更新] 緊湊參考路徑的下一選項由客體 VM 決定。[取代] 宿主讀旗標後選未試答案。[原因] 客體輸出經七題及 ID31 邊界案例驗證。[狀態] 高，限參考模型；世界接入與資源計費尚待驗證。
