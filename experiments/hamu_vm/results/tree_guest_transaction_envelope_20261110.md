# 2026-11-10 Guest canonical-tree transaction envelope trial
U: 題目為資源，樹記錯答；要求成長、回滾、可重現性。
F: hamu_vm_tree_guest_revision_bypass_20261110.zip；test_tree_guest_revision_bypass.cpp 與 tree_generation_registry_fixture.hpp。
T: 新增 tests/test_tree_guest_transaction_envelope.cpp；C++17 -O0 -g0 ASan/UBSan，執行 PASS。
[更新] Host-only GuestTreeEnvelope 包住實際 guest TREE_ADD 後，canonical tree 變更使 revision 0→1。空操作不增加版本；回傳失敗、丟例外、revision UINT64_MAX 溢位均回滾 canonical tree。
[取代] 上輪 guest TREE_ADD 無版本追蹤之反例：本輪證明透過指定入口可追蹤，但尚未堵住繞過入口的執行路徑。
[原因] TransactionalRevision::apply 比對 DurableRegistry canonical snapshot，成功後 commit，失敗 restore。
[狀態] 宿主局部驗證高。尚未修改正式 VM execute 或強制所有呼叫者走入口；非整個 Hamster 狀態交易，work/status/output/HP、宿主外部副作用不保證回滾；generation 變更後的 restore 防倒退限制亦未整合交易；無 crash-atomicity。fixture 既有 no-return 警告。
A: 下一輪應實作可強制執行的 guest API 邊界，並針對 TREE_ACTION、work 寫入、容量失敗、generation 刪除等建立完整狀態回滾測試；避免將此測試誤認為正式 VM 已修復。
重現：cd hamu_run && g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_guest_transaction_envelope.cpp -o /tmp/hamu_guest_envelope && ASAN_OPTIONS=detect_leaks=0 /tmp/hamu_guest_envelope
輸出：PASS: guest TREE_ADD revision, noop, failure/exception rollback, overflow guard (canonical tree only)
