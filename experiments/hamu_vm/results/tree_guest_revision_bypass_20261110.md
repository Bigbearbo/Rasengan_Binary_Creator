# 2026-11-10 Guest TREE_ADD revision bypass reproduction
U: 作者要求 VM 樹狀記憶成長正確、回滾與客體權限；題目作資源、先死記錯答。
F: Library 最新 hamu_vm_tree_revision_transaction_20261108.zip，tests/test_tree_revision_transaction.cpp 的 TransactionalRevision wrapper，以及 src/hamu_vm_core.hpp 的 TREE_ADD/TREE_ACTION 路徑。
T: 新增 tests/test_tree_guest_revision_bypass.cpp；C++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer 編譯，ASAN_OPTIONS=detect_leaks=0 執行 PASS。
[更新] 實際 guest TREE_ADD 可改變 canonical snapshot 而 RevisionRegistry::revision 仍維持 0；對照由 TransactionalRevision::apply 包裝的宿主寫入則增加 revision。已重現客體路徑繞過版本交易，不再只是靜態推測。
[原因] VM execute 的 put/segment_row_ref 直接寫入 Hamster memory，宿主 TransactionalRevision 並非全域寫入攔截器。
[狀態] 宿主局部反例信心高；正式 VM 核心未改。下一輪設計 VM 執行外層 transaction envelope：捕捉前後 canonical bytes、失敗回滾、成功變更 revision+1，並驗證 TREE_ADD、TREE_ACTION、一般 work 寫入與容量失敗；同時確保 revision 溢位時拒絕提交。不可將此原型當成持久化 crash-safe 或 Zero/自由生態成果。
命令：cd hamu_run && g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_guest_revision_bypass.cpp -o /tmp/hamu_guest_bypass && ASAN_OPTIONS=detect_leaks=0 /tmp/hamu_guest_bypass
輸出：PASS: guest TREE_ADD bypass reproduced; wrapped mutation increments revision
已知警告：fixture prior_generation_main() 缺 return（繼承問題）。
