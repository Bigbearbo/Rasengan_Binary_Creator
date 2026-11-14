# 2026-11-08 同世代快照修訂版號試驗

U：作者要求分頁樹可持續成長、記憶正確、回滾不污染。F：Library 最新 `hamu_vm_tree_generation_clone_atomic_20261108.zip`；工作入口 Library v44 落後封存。T：本輪獨立 C++17 ASan/UBSan 執行。A：下一輪待驗證。

[更新] 新增宿主原型 `RevisionRegistry`，以 `HAMU-REV-2 revision` 包裝原 `HAMU-GEN-1` 快照；宿主每次寫入後必須呼叫 `commit()` 單調增加 revision。相同 lineage / generation 但答案位元已變更時，舊 revision 快照拒絕恢復；相同 revision、不同 payload 亦拒絕。先驗證再提交，失敗保持原狀。
[取代] 僅依 generation 防 ABA，無法發現同一節點答案位元回退。
[原因] generation 只在刪除重用時遞增，不涵蓋原地改答案。
[T] 指令：`g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_revision_guard.cpp -o /tmp/hamu_revision11 && ASAN_OPTIONS=detect_leaks=0 /tmp/hamu_revision11`。結果：`PASS revision guard same-generation stale restore, rollback, malformed header; restart limitation demonstrated`。先前測試曾誤用 VM 指令未寫入 row，改用宿主直接切換答案位元並增加明確 row 變更斷言，避免假陽性。繼承夾具仍有既存 no-return 警告。
[狀態] 宿主局部驗證中高；不是正式 VM 修改。重大限制：`commit()` 尚未自動綁定所有 VM/宿主寫入，漏呼叫會讓 revision 失真；重啟後若無獨立可信 high-water mark，舊快照仍能被新進程接受（本輪刻意測出）。未做磁碟原子提交、客體 handle、HP 成本。下一輪：將所有樹寫入路徑接到交易 revision，並設計持久化 high-water / crash consistency；不以這次測試宣稱磁碟防回滾。
