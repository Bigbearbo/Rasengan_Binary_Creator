# 2026-11-08 Transactional revision host trial
U: 作者要求成長型記憶樹、正確回滾與可重現實測。F: `hamu_vm_tree_revision_guard_20261108.zip`，其 `RevisionRegistry` 必須手動 commit。T: 本輪新增 `tests/test_tree_revision_transaction.cpp`。A: 尚未實作全 VM 寫入攔截。
[更新] 宿主 TransactionalRevision::apply(fn) 在成功且 canonical 快照確實改變時自動遞增 revision；失敗、例外或無變更不遞增。以底層 inner.restore 作交易內回滾，避免對外 restore 同版不同 payload 守衛阻止合法回滾。
[取代] 宿主試驗寫入必須手動 commit 的單一路徑；但裸露的 VM/宿主直接寫入仍可繞過 wrapper。
[原因] 同版衝突防護與交易內回滾有不同信任邊界，不能共用對外 restore。
[T] g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_revision_transaction.cpp -o /tmp/hamu_tx && ASAN_OPTIONS=detect_leaks=0 /tmp/hamu_tx
PASS transactional revision success/failure/noop/exception; external bypass demonstrated
初次編譯失敗：舊 fixture 改寫 main 巨集造成重複 main；改為直接重用 RevisionRegistry 定義。第二次測試失敗：對外 restore 拒絕同版不同內容（正確安全行為），改為交易內底層 restore 後 PASS。保留原有 no-return 警告。
[狀態] 宿主局部 PASS，不是正式 VM；沒有磁碟 crash consistency、高水位持久化、全寫入路徑保證、HP 成本。下一輪應將 VM 客體樹指令寫入導向單一受控交易入口，並做繞過路徑審計。
