# 倉鼠世界｜分頁樹 VM 實驗與成長驗證（2026-11-02）

## 研究源頭、版本界線
U：使用者要求「也不用太在意快，一時快可能變大之後反而慢了，好的成長型設計優先。繼續」，之後再次「繼續」。核心目標是成長正確性、容量擴展以及不破壞記憶，不是只追求短題執行步數。
F：基底為 Library `/倉鼠世界/程式版本/hamu_vm_tree_index_growth_20261102.zip`。**本輪新增的是獨立、明確 opt-in 的分頁樹 VM ABI；舊五位模式與既有連續寬位元樹模式仍保留。**

## 本輪程式變動（F）

1. `src/hamu_vm_core.hpp` 新增 `HamsterParams::tree_segmented_enabled=false`。設 true 時樹由原生分頁儲存，節點 ID 位寬容許 6–16，保留零號根，標準客體 `TREE_FIND`、`TREE_ADD`、`TREE_FIND_REG`、`TREE_ADD_REG`、`TREE_ACTION` 路由到分頁樹；原五位與寬連續模式對應路徑不變。
2. 分頁樹每頁 31 節點。每節點 canonical row 是一個 `uint32_t`，其中 23 個有效位（最多 16 位父 ID、3 位 key、3 位 action 狀態、1 位 live）。採 `std::deque<std::array<uint32_t,31>>`，新添頁面不改變已有節點 row 的地址；全域 ID = `1 + 31*page + slot`。原 VM `memory` 的程式位元、`program_start` 等不需要搬移。原生節點資料不是客體一般 `READ/WRITE` 位元區，僅藉樹指令操作；兩種格式目前**不可直接互讀**，也無既存連續樹轉換器。
3. `grow_segmented_tree_capacity(n)` 由宿主在 VM 執行回合外呼叫；只新增需求頁數並調高邏輯容量，可選擇增加少於整頁的可用槽數。使用例外恢復，配置失敗時移除剛新增的空頁並維持原容量。至 16 位上限 65,535 節點；**沒有**跨位寬自動遷移，也沒有客體自行決定買容量及 HP 計費。
4. 客體多個 `TREE_ADD` 在同一執行回合中，若中途容量不足，只撤銷本回合新建節點及修改過的 `TREE_ACTION` 欄位，同時回滾原工作區寫入和寄存器；無須每回合先複製所有分頁。`tree_capacity_blocked=true` 明確回報；宿主增容後重試可繼續。舊 5-bit 與連續寬位元路徑不改。
5. 原生 `std::unordered_map` 索引是可重建的衍生資料：由 canonical 頁行建立，非遺傳知識；`tree_index_enabled=false` 可逐列線性掃描供差分對照。快照 `new_his()` 保存 canonical 頁，`copy_hamu()` 核對模式、編號位寬、容量與快照布局；未公布快照或容量不合則拒絕，後代重新建索引。
6. 新增 `tests/test_tree_segmented_vm.cpp`，可採一般測試或 `--stress-10000`，`Makefile` 提供 `segmented-vm-growth-test`（ASan/UBSan 600 題）與 `segmented-vm-growth-stress`（O2 10,000 題），舊 `make` targets 保留。差異詳 `results/tree_segmented_vm_core_20261102.diff`。

## 本輪實際執行（T）

| 測試 | 600 路徑（12-bit） | 10,000 路徑（16-bit） |
|---|---:|---:|
| 真正建立節點 | 689 | 11,431 |
| 最終邏輯容量 | 1,024 | 16,384 |
| 擴容次數 | 7 | 11 |
| 實際頁數 | 34 | 529 |
| canonical row payload | 4,216 B | 65,596 B |
| `program_start` | 固定 350 | 固定 350 |
| 有索引模式的重建掃描行 | 1,015 | 16,375 |
| 有索引模式的查找次數 | 3,732 | 60,462 |
| 無索引逐列掃描行 | 664,616 | 262,960,871 |

兩組都以同一題序同時執行開／關索引版並比較結果；抽查 canonical 頁內容完全相同。測試涵蓋舊節點位址不移、已學答案、後代複製（索引不遺傳）、容量不足回合回滾、動作寫入回滾、擴容重試、重複分支的 REG 版本指令、布局不相容拒絕，以及增容後舊快照失效／重新公布。原生 row payload **不等於**總記憶成本：未包含 `std::deque` 容器管理、雜湊索引桶、元素或 VM 其他位元區。寬連續位元列可更緊湊，因此分頁方案並非記憶體最省。無索引掃描量不是執行時間。

`results/tree_segmented_vm_regression_20261102.log`：`g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined` 重新編譯運行 7 種測試，**全部 PASS**：
`test_tree_segmented_vm`、`test_tree_wide_index`、`test_tree_wide_vm_growth`、`test_tree_vm`、`test_vm`（含 6,000 個隨機 VM guest）、`test_tree_compact_optimized_cost`、`test_segmented_tree_growth_ref`。最後修正「增容後需重新發表快照」測試並再次單獨以 ASan/UBSan PASS。`--stress-10000` **只以** `g++ -std=c++17 -O2` 無 Sanitizer 運行 PASS，不可升格為 sanitizer 已測。

## 結論與未完成（A）

[更新] 可以在同一 VM 實作中選擇新的分頁樹 ABI，讓客體以既有樹指令跨頁存取、維持全域節點編號，擴容時不搬舊樹或 VM 程式區；10,000 題／11,431 節點已跑通。
[取代] 「只有宿主分段參考模型，真 VM 必須使用可搬移的連續樹」。
[原因] 本輪新增原生 VM 分頁儲存、樹指令路由、快照繼承與交易回滾，並完成開關索引差分測試。
[狀態] 高（上述條件），但不包括生態演化或跨格式資料遷移。

仍未完成：

- 分頁樹是**原生 VM 管理的特殊區**，不是普通 work bits，也不是螺旋語自行定義的全自描述內存；一般 `READ/WRITE` 不可直接改頁內位元。沒有舊連續樹轉換成新頁格式的正式、受控遷移實作。`std::deque`/index 不等於總 HP 成本已計價。
- 16 位全域節點編號仍有限，未做到 65,535 以上的跨階 handle；目前 3-bit key 表示路徑局部詞鍵，需研究可變鍵寬、句型成長。
- `TREE_ACTION` 仍是 2 位答案值（0–3）和 1 位確認，不是八候選完整失敗旗標。之前 8 候選的緊湊死記與這套分頁儲存尚未整合。
- 索引為宿主衍生雜湊資料，未計 `unordered_map` 真正總配額，亦未向倉鼠 HP 收費；需比較分頁配置、索引、客體計算與宿主成本的總代價。
- 只有受控 VM 單體、快照後代測試，沒有自由生態、Zero、世界級繁殖與長期死亡／重生，不能把固定宿主詞表稱為自主語言或自主學習。

建議下一步先設計並驗證：有明確版本和無損檢查的 **舊連續樹 → 分頁樹遷移交易**，包括已有行動答案、空洞節點／重用順序、回滾及後代。其次讓分頁樹葉片儲存八候選錯誤旗標，仍以試錯死記為核心。不要因索引跑得快就跳過資料格式互通與成本計帳。
