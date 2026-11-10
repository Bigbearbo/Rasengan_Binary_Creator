# 倉鼠世界：寬編號樹可重建索引與成長成本驗證（2026-11-02）

## 來源與本輪重點

U：使用者先前要求「也不用太在意快，一時快可能變大之後反而慢了，好的成長型設計優先」，本次續以「繼續」授權接續。優先保持長期成長正確性和受控學習死記設計，不拿小型步數競賽當核心貢獻。前輪來源：`/倉鼠世界/程式版本/hamu_vm_tree_wide_growth_20261102.zip`；本輪改動集中在 `src/hamu_vm_core.hpp`、`tests/test_tree_wide_index.cpp`、`tests/test_tree_wide_vm_growth.cpp`、`Makefile`。

## 本輪實作（F）

1. 寬編號樹 `tree_id_bits>5` 可以選用 **VM 宿主內部的衍生索引**（`HamsterParams::tree_index_enabled=true`；設 false 保留原逐列掃描用於對照）。不修改客體 `TREE_ADD/TREE_FIND` opcode、節點位元布局、記憶持續形式、最小可用節點 ID 的語意。五位舊模式不使用索引。
2. 索引由既有樹行重建：key 是 `(parent_id, 3-bit token_key)`，value 是原節點 ID；同鍵多行時保留原線性掃描的最小 ID。採 32-bit packed open-addressed hash，隨**實際已索引節點**增量擴張，而非按所有預留節點配置一組 8-way 轉移表。最小空位以單一 next-free 指標追蹤，未針對每個空位配置集合。索引只可加速查找，不是權威記憶，不會寫入 `memory_his`。
3. 客體 VM 透過一般 WRITE 修改樹行結構時自動丟棄索引；原樹不受影響，下次查找重建。客體使用 `TREE_ADD` 插入合法節點時同步維護索引；`TREE_ACTION` 只寫動作欄位，不重建結構索引。宿主 `change_hamu`、隨機記憶初始化、`copy_hamu`、回合交易回滾均使索引失效。宿主 `grow_wide_tree_capacity` 扩大未使用的尾端時保留有效索引與 stable ID。宿主若在這些 API 之外**直接改 `Hamster::memory` 的樹行**，必須自行呼叫公開的 `invalidate_tree_index()`；本輪未全面封裝 raw memory 權限。
4. 度量分開：`tree_lookup_rows_examined`（包含索引建立、最小空位探查和未索引掃描）、`tree_index_probes`（雜湊槽探查及重雜湊）、`tree_index_slots.capacity()*4`（衍生索引的槽配置位元組；不含 vector 類別等固定開銷）。上述均是 VM **宿主原生成本**，不等於客體 `executed_steps`/HP。兩類成本日後要制定收費政策才能合併。

## 本輪獨立實測（T）

同種題目、增長策略與回饋下，將 `tree_index_enabled=true/false` 並排執行，對比 handle、整份 canonical memory/暫存器、容量、回滾與後代答案：

| 題目路徑 | 真正建成節點 | 擴容次數 | 無索引掃描列 | 開索引掃描列 | 雜湊探查（開索引） | 已配置索引槽 |
|---|---:|---:|---:|---:|---:|---:|
| 600 | 688 | 7 | 789,958 | 3,744 | 17,161 | 1,024 槽 / 4,096 B |
| 3,000 | 3,429 | 9 | 22,489,628 | 11,603 | 75,393 | 8,192 槽 / 32,768 B |

3,000 題在當前 12-bit ID、容量 4,095、17-bit 行的持續樹資料預留 77,805 bit（約 9.5 KiB），衍生索引槽占 32 KiB（不計 VM 其他資料）。索引節省大量逐行掃描，但不是零成本：有額外記憶與雜湊探查。**不能把掃描列數直接當成牆鐘時間或總計算成本**，不同工作單位不能直接相減。

`test_tree_wide_index.cpp` 600 題另覆蓋：重複題不新增 ID、`TREE_ACTION` 動作記憶、客體直接 `WRITE_0` 修改某節點存在位後重新索引、刪除後沿用同一最小可用 ID、後代重建索引/保留答案、滿額路徑原子回滾及擴容重試。3000 題比較開關索引後的所有 canonical 位元，保留多次擴容。`test_tree_wide_vm_growth.cpp --stress-3000` 也在開索引模式通過。

編譯測試記錄：`results/tree_wide_index_regression_20261102.log`。五項 (`test_tree_wide_index`, `test_tree_wide_vm_growth`, `test_vm`，包含 6000 隨機 guest，`test_tree_vm`，`test_tree_compact_optimized_cost`) 以 `g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined` 測試均 PASS；3000 路徑負載以 `g++ -std=c++17 -O2`、**不帶 Sanitizer** 比較 PASS。既有舊版其他測試本輪未全部重編。

## 新結論、限制及下一步

[更新] 寬編號客體樹指令具備可重建、可隨成長維護的衍生查找索引，且所測 600/3000 題與未索引版本記憶逐位一致。
[取代] 寬編號 VM 必須每次逐列掃描全部預留節點，否則難以維持原 ID / 重用 / 回滾語意。
[原因] 索引只重建/映射既有行，沒有讓索引成為新的可繼承真相；差分測試涵蓋修改、滿額、重試、繼承。
[狀態] 高（所測條件、單程式 VM）；不是任意程式與惡意直接改寫下的完整一致性證明。

仍未完成：真正頁式/分段存放與穩定跨寬度 handle；超過 4095 節點的 guest 格式；宿主擴容仍會複製搬動連續 VM 記憶（O(整段長度)）；可由倉鼠主動請求新容量與 HP 收費；八候選緊湊試錯附帶記憶整合；完整世界級繁衍與長期族群測試；直接宿主寫樹資料的封裝防護；更大真實題庫的總成本/牆鐘測量。不要將此視為自由生態或 Zero 無種子已實現。

下一輪建議：先探索頁式樹與固定邏輯 handle（舊 ID 不中斷）+ 持續樹行快照，盡量避免每次成長搬整段記憶；比較原生索引記憶、搬遷成本與 HP 資源。其後再把八候選錯誤旗標融入寬模式，不要先發明公式壓縮。
