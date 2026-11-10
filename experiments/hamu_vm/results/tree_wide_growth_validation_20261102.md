# 倉鼠 VM 寬編號、實際動態擴容驗證（2026-11-02）

## 來源及決策
U：使用者在本視窗要求「繼續」，此前明確要求「也不用太在意快，一時快可能變大之後反而慢了，好的成長型設計優先。繼續」。
F：基於 Library `/倉鼠世界/程式版本/hamu_vm_tree_growth_audit_20261102.zip` 延伸，不覆寫原檔。A：把上輪宿主限定的 31 節點以上分段樹研究，往真 VM 客體樹指令推進；不把本輪方案宣稱為最終分段索引。

## 本輪實作（F）
1. `src/hamu_vm_core.hpp`：新增 `HamsterParams::tree_id_bits`，預設 5；允許 5–12。預設 5 位保留原有 9-bit tree row、容量上限 31、既有 `TREE_ACTION` 3-bit 動作資料布局。寬模式中 `TREE_FIND/TREE_ADD/TREE_FIND_REG/TREE_ADD_REG/TREE_ACTION` 使用可變長的父節點編號。客體能在自己的 VM 指令串內沿題目詞序自行串起樹路徑。
2. 寬模式（`tree_id_bits > 5`）節點採 `[存在1][父節點ID bits][詞鍵3][動作狀態3]`，答案欄位與節點同行，節點位址不依賴總容量；傳統 5 位模式不變。現有寬模式 `TREE_ACTION` 仍只持有是否確認及兩位動作值（0–3），**不是**舊緊湊八候選錯誤旗標方案的完整升級；二者需後續整合。
3. 新增 host-only `Hamster::grow_wide_tree_capacity(new_capacity)`：在相鄰樹尾和程式區之間插入零位，把程式／快照底層位元與執行窗口搬到新位置，原有樹節點與動作欄位保持原位，擴增容量並防止超過位元上限或 1Mi-bit VM 限制。**只允許客體執行回合外由宿主呼叫，尚無客體申請容量／HP 計費政策**。布局不符拒絕執行，必須重新公布 `new_his()` 才可當作寬模式繼承快照。
4. 寬模式中，若一條路徑中途因節點滿額而無法完成，本次 VM 執行回合的可寫記憶與寫入痕跡回滾，`tree_capacity_blocked=true`，停機；宿主擴容後可重新由頭嘗試路徑。這個全回合 rollback 可能取消同一執行回合的其他可寫動作，是刻意的交易邊界。傳統五位模式維持既有語意。
5. 新測試 `tests/test_tree_wide_vm_growth.cpp`，主路線從 8 個節點容量開始、重試經過 31/255 等界線，以 VM 實際 `TREE_ADD` 建立題目路徑、`TREE_FIND` 查找，測原 handle、動作記憶、後代快照、拒絕布局不符及 3→8 增容時失敗回滾／重試；提供 `--stress-3000` 選項。Makefile 新增 `wide-tree-growth-test`。

## 本輪結果（T）
- `g++ -std=c++17 -O1 -g -fsanitize=address,undefined`：`test_vm`（含6,000個隨機guest）、`test_tree_vm`、`test_stable_work`、`test_tree_error_trial`、`test_tree_compact_world` 均 PASS。
- `g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined`：`test_tree_compact_reference`、`test_tree_compact_optimized_cost`、`test_tree_compact_growth`、`test_segmented_tree_growth_ref`、`test_tree_wide_vm_growth` 均 PASS。切換 O0 是因原一口氣 O1 編譯回歸批次碰到執行時限，不是 O1 測試失敗。合計 10 種測試項目均有 sanitizer 成功紀錄。
- `g++ -std=c++17 -O2`（**無 Sanitizer**）：600 條題目、688 節點、最終容量 1023、7 次擴容、787827 掃描列、預留 17391 位 PASS；3,000 條題目、3,429 節點、最終容量 4,095、9 次擴容、22,586,952 掃描列、預留 77,805 位 PASS。3,000 條的 Sanitizer 額外重測未完成：超出執行時間；不可當作 sanitizer PASS。
- `test_tree_compact_optimized_cost` 舊對照重播在本輪重新 PASS：既有緊湊安全版本 1,982 VM steps，舊方案 2,326 VM steps。本輪寬模式不能直接拿這些小型 VM 步數當自己效能資料。
- 測試原始輸出存 `results/tree_wide_growth_regression_20261102.log`；未修改標準題庫、自由生態、Zero 世界，未 GitHub 寫入。

## 新發現及限制
[更新] 真 VM 樹操作已跨 31，並可在回合外由宿主增量擴容、維持已配置 handle 與既有動作記憶。[取代] 上一輪只有宿主 C++ 分段參照模型跨 31。[原因] 新增可變 ID VM ABI、行內動作資料、動態樹尾擴張與客體執行測試。[狀態] 高（上述範圍內；3k stress 僅一般 O2）。

[更新] 不能把可擴容理解成已解決長期時間複雜度；3000 路徑共掃描 22,586,952 列，較 600 路徑掃描 787,827 列增加約 28.7 倍，而題目只增加5倍。主因仍是每次 `TREE_ADD/TREE_FIND` 在所有已預留列中逐列掃描，且宿主成長會複製／搬移整段 VM 記憶。[取代] 以 31→4095 容量擴大就宣稱成長架構完成。[原因] 操作內部成本直接計數。[狀態] 高（計數）；與其他資料結構效率比較尚未測。

[限制] 目前 3-bit 詞鍵可藉多層路徑組合大量題目，並不表示每個鍵只有8道題；但每節點的 2-bit 動作不能直接表達8候選死記試錯。擴容仍需預先選好 `tree_id_bits`，12-bit 上限4095節點，跨 ID 寬度改版必須另做顯式交易式搬遷／版本轉換。現行布局是連續工作區不是分段頁式，也沒有可維護索引、客體主動申請擴容、完整世界級繁殖及大題庫生命周期測試。`TREE_ACTION` 使用舊 opcode 的改變由 `tree_id_bits` 參數選擇版本，日後跨版本互通不能假定自動相容。

## 下次優先任務
1. 避免再把短題庫步數當首要 KPI。規劃 **真分段樹 + 可稽核索引** 的雙重成本：索引/頁資料位元、查找列數、更新寫入、搬遷成本；先決定段別與全域 handle 的可解碼格式，避免動態改變 `tree_id_bits` 造成大搬遷。
2. 新增真正的八候選（或更寬）錯誤排除葉片，不能把2-bit `TREE_ACTION` 當成已支援的8候選死記。
3. 做客體可見的「容量不足」回報與宿主資源／HP 計費，再接世界級繁殖及長期演化；不要把 host 的 `grow_wide_tree_capacity` 叫做倉鼠自主長記憶。
