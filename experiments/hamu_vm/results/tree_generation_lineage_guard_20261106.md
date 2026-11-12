# 2026-11-06｜跨 lineage 快照恢復權限守衛

U：作者要求可成長的分頁樹、後代隔離及可回滾；F：Library 最新 hamu_vm_tree_generation_rollback_guard_20261105.zip；T：本輪修改與重新編譯；A：尚未完成的威脅模型。

[更新] 宿主 DurableRegistry::restore(snapshot, allow_lineage_change=false) 預設拒絕不同 lineage 的快照；僅明確指定 true 才允許匯入（例如後代繼承），匯入後必須指定後代獨立 lineage 才可對外暴露引用。新增已持有有效樹節點的 registry 遭 foreign lineage 快照覆蓋的拒絕／狀態不變測試，以及後代先拒絕預設匯入、再顯式匯入的測試。
[取代] 舊 restore 可無條件接受不同 lineage，僅靠呼叫者事後重設 lineage。
[原因] 不同個體的引用域不可在普通 restore 中被無意替換。
[T] g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_generation_persistence.cpp -o gen_test && ASAN_OPTIONS=detect_leaks=0 ./gen_test
輸出 PASS durable host registry reload, stale refs, corrupt rollback, offspring isolation。既存 test_tree_reject_mask.cpp:78 no-return warning 未修。
[狀態] 宿主原型局部 PASS，非 VM 客體可操作功能。顯式匯入後改 lineage 仍是呼叫者責任，應後續改成原子 clone_into_new_lineage API。重啟後舊快照回滾、同 generation 的 row 身分替換、磁碟原子提交、HP 成本仍未解決。
