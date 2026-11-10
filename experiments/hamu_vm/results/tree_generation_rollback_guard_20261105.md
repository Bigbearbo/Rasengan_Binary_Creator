# 2026-11-05｜同 lineage 快照回退防護
U：使用者要求可擴展、可回滾但不能錯認舊節點。F：hamu_vm_tree_generation_linear_host_trial_20261104.zip。T：本輪重新編譯執行。A：後續 epoch / 跨進程持久化設計。

[更新] 在宿主 DurableRegistry::restore 中，若快照 lineage 與當前相同，拒絕任何節點 generation 小於現有值的快照；新增刪除後恢復舊快照的反例測試，確認失敗不變更狀態、舊引用不復活；獨立新 registry 仍可載入合法快照。
[取代] 上版允許同 lineage 恢復舊快照，使刪除後的舊 handle 重新有效的漏洞。
[原因] 先前只有快照內結構完整性，缺少跨時間的世代單調性檢查。舊快照本身可能合法，卻不代表可安全覆蓋現有狀態。
[狀態] 宿主局部 PASS；尚未解決相同 generation 下不同 row 的身分替換、重啟後回復較舊快照、跨進程防回滾、持久 epoch / 磁碟原子提交。這個 guard 不等於完整快照安全性，也不是客體 VM 功能。

重現：
`g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_generation_persistence.cpp -o gen_test && ASAN_OPTIONS=detect_leaks=0 ./gen_test`
輸出：`PASS durable host registry reload, stale refs, corrupt rollback, offspring isolation`。
仍有既存測試夾具 `test_tree_reject_mask.cpp:78` 缺少 return 的編譯警告。
