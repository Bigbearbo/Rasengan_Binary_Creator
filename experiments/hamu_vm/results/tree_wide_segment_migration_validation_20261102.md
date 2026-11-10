# 倉鼠世界｜寬位元連續樹轉分頁樹：語義遷移與空洞節點重用（2026-11-02）

## 來源與範圍

U：作者優先要求可成長、正確的設計；初期允許死記題目與錯誤答案，先擴大樹記憶，再研究壓縮。
F：本輪基於 Library `/倉鼠世界/程式版本/hamu_vm_tree_segmented_growth_20261102.zip`，新增 `src/tree_wide_segment_migration.hpp`、`tests/test_tree_wide_segment_migration.cpp`，修改 `src/hamu_vm_core.hpp` 與 `Makefile`。原版與本輪的 diff 見 `results/tree_wide_segment_migration_core_20261102.diff`。

## 新增設計

1. 提供宿主明確呼叫 `import_wide_tree_rows_into_segmented(target, source)`：把 6–12 位連續寬樹的**目前有效樹節點**轉為 31 槽一頁的分頁樹，目標可使用更寬（至 16 位）的節點 ID。保留原節點 ID、父子關係、3 位 key、3 位動作狀態（確認位 + 2 位答案）；不會複製 VM 程式、工作區、HP、寄存器或其他生命週期狀態，故為「樹語義遷移」，**不是**完整倉鼠遷移。
2. 來源資料驗證包括：連續樹布局、容量與位寬、父節點存在、無重複 (parent,key)、無循環。目標必須是容量足夠且空白的分頁樹。所有驗證、配置先在臨時物件完成，成功後才發表到目標；失敗時目標不變，來源永不修改。
3. 舊樹中的空洞節點不再使分頁樹浪費原 ID。`segment_used` 改明確表示最高已配置 ID，`segment_first_free_id` 表示最小空槽；新增節點優先重用最小空槽，滿額判定改為檢查最小空槽是否超過容量。遷移時建構游標；後代快照複製時由 canonical 頁重建，不把衍生索引／游標當遺傳資料。
4. VM 單回合的多次 `TREE_ADD` 若遇到容量不足，現在會撤銷**所有**新插入的節點，包括重用的舊空洞，並恢復最高 ID、最小空槽游標、動作狀態、可寫工作區及寄存器；舊版只撤銷高水位以上的新節點，不足以處理重用空洞。正常無空洞的分頁樹增長仍為攤銷 O(1) 游標更新，不必每次掃描全樹。
5. 仍是 opt-in 的宿主遷移。未增加客體遷移指令；舊 5 位樹格式未納入；原始空洞列中的垃圾位元不保留，因為其不是有效節點語義。宿主可寫 canonical 頁；若另行直接修改有效位，須重新建構衍生游標與索引。

## 本輪實際測試 T

使用 `g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer`：

`make -B wide-segment-migration-test`：PASS。測到保留節點 ID 1/3/4、洞 2 優先重用、3 位 action 原值保留、一次回合重用洞 2 及新增 ID5 後容量失敗的**完全回滾**、擴容後重試、後代快照、索引開關一致、拒絕重複邊／循環／死父節點／容量不足／非空目標；另測 12→16 位的跨頁稀疏 ID 1/32/65 及繼承後繼續重用洞 3。

`make -B segmented-vm-growth-test`：PASS，600 條題目，689 節點，容量 1024，7 次擴容；索引開關 canonical 結果一致。

`make -B wide-tree-index-test`：PASS，600 條路徑的連續樹索引與線性對照。

`make -B wide-tree-growth-test`：PASS，600 條路徑的原連續寬樹擴容與繼承。

`tests/test_tree_vm.cpp` 以 ASan/UBSan 直接重編並執行：PASS。

`make segmented-vm-growth-stress`：PASS，`-O2` **未開 Sanitizer**，10,000 條路徑、11,431 節點、11 次擴容、16,384 容量、529 頁；與前版的規模結果一致。

`tests/test_vm.cpp` 的重編嘗試因執行指令超時，**沒有**得到本輪 PASS；不能把舊版 6,000 隨機 VM 客體 PASS 當本輪新測。指令與輸出見 `results/tree_wide_segment_migration_regression_20261102.log`；該 log 末尾在 `test_tree_vm` PASS 後結束，無 `test_vm` 結果。

## 判斷與下一步 A

[更新] 目前有一條可測、明確 opt-in 的寬連續樹 → 分頁樹**語義遷移**路徑，保留節點 ID 與已確認的 2 位答案；空洞重用、回滾及後代繼承在本輪指定情況通過。
[取代] 「分頁樹完全沒有舊寬樹轉換路徑」。
[原因] 實作了受驗證的宿主遷移交易，並補齊重用空洞的分頁 VM 原子回滾。
[狀態] 高（列出的具體測試），對完整 VM 狀態遷移與世界級生態適用性仍低。

未完成：整個倉鼠的程式與工作記憶搬遷、來源 snapshot／版本序列化、跨 16 位 ID、分頁樹客體任意位元存取、8 候選錯答旗標、宿主索引與頁配置的 HP 計費、自由生態與 Zero。下一輪建議先實驗「分頁樹葉片的 8 候選錯誤遮罩」或「完整 VM 狀態與樹同步遷移」，並把分頁配置及索引成本計入可觀測資源。這些都尚未完成。
