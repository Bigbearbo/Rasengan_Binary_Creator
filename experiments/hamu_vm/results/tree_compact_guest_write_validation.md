# 題目節點附帶位元：VM 動態寫入驗證

2026-11-01。接續 guest_address 版本。

更動檔案：`src/tree_compact_reference.hpp`、`tests/test_tree_compact_reference.cpp`、`README.md`、本報告、`results/tree_compact_guest_write_run.log`、`results/conversation_20261101_guest_write.md`。

客體 VM 先清除五位父節點 ID，再以 TREE_ADD 尋找題目節點，逐位判斷 ID、移動工作區指標，寫入八位錯答旗標或三位正解與成功旗標。五位清除用 payload 前方保留的工作區，配置時檢查不與樹列重疊。宿主提供題號、答案及回饋，也驗證寫入成功；下一選項仍由宿主選擇。原版四倉鼠世界尚未接上這個參考路徑。

第一次測試暴露連續寫正解位元時 TREE_ADD 把上次 ID 當父節點，造成第二次查詢走進子樹；修正為每次查詢前由客體清除五位 ID。沒有修改核心 ISA。

ASan／UBSan (`-O1 -g -fsanitize=address,undefined`, `detect_leaks=0`) 三項 PASS：`tree-compact-reference-test`、`tree-error-trial-test`、`tree-error-world-test`。涵蓋七題、每題八個錯答、七個題目節點及84位附帶資料、正解重用、子代繼承，另有節點 ID31 的錯答及正解回讀。詳見 `tree_compact_guest_write_run.log`。未重跑6000隨機 VM 客體。

[更新] VM 依題目節點 ID 動態定位讀與寫。[取代] 寫入時由宿主計算地址。[原因] 連續查詢清除父 ID 後，ASan／UBSan 邊界案例通過。[狀態] 高，限參考模型；客體選項決策及世界接入尚待實作。
