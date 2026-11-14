# 2026-11-08 宿主後代 lineage 原子匯入試驗

U：作者要求分頁樹長期成長、後代記憶繼承與隔離。F：Library 最新 `hamu_vm_tree_generation_lineage_guard_20261106.zip`。T：本輪程式修改與重編測試。A：後續未驗證設計。

[更新] 在 `tests/test_tree_generation_persistence.cpp` 的宿主 `DurableRegistry` 原型新增 `clone_into_new_lineage(data, child_domain)`：先驗證非零、非來源 lineage，再使用現有 restore 的全量驗證，成功後一次綁定子代 lineage，避免呼叫者忘記手動重設 lineage。保留原 restore 供既有測試相容。
[取代] 上版後代顯式匯入後，仍由呼叫者手動改 lineage 的危險示範；新增安全 API，舊示範仍保留於回歸測試。
[原因] 後代不可接受父代舊 handle；匯入失敗也不能改變子代樹狀態。
[T] 以 C++17 `-O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer` 重編並執行 `tests/test_tree_generation_persistence.cpp` 與 `tests/test_tree_reject_mask.cpp`，兩者 PASS。新增拒絕零 lineage、與來源相同 lineage、損毀尾碼；檢查失敗不變、成功匯入後父 handle 無效而子 handle 有效。修正繼承測試夾具 `test_tree_reject_mask.cpp` 缺 `return 0` 警告。測試仍為宿主局部原型，正式 VM 核心未改。
[狀態] 宿主後代匯入局部高信心。仍未解決磁碟原子提交、重啟後回滾防護、同 generation row 更新與快照版本、客體 handle/HP 資源成本。下輪優先同世代快照回退風險：引入單調 revision，區分合法答案更新與舊快照回滾。

重現：`g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_generation_persistence.cpp -o gen_test && ASAN_OPTIONS=detect_leaks=0 ./gen_test`；同樣編譯 `tests/test_tree_reject_mask.cpp` 執行。測試輸出分別 `PASS durable host registry reload, stale refs, corrupt rollback, offspring isolation` 和 `PASS opt-in eight-candidate rejection, legacy action, rollback, inheritance, isolation, ABI gating`。
