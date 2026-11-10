# 緊湊試錯四倉鼠世界驗證

2026-11-01。更動：新增 `src/tree_compact_world.cpp`、`tests/test_tree_compact_world.cpp`、`results/tree_compact_world_validation.md`、`results/tree_compact_world_run.log`、`results/conversation_20261101_compact_world.md`；修改 `Makefile`、`README.md`。原世界保持為獨立對照。

四個個體各自以客體 VM 從題目節點 ID 讀寫試答資料，客體自行選擇正解或第一個未試選項。環境仍供題與回饋，每次試答扣100，答對補200；至少三隻掌握首題才升題。首題答案6、次題3。容量31的結果為首題第7輪4/4、次題第11輪4/4、合計資源4000→1200。容量1在首題第7輪4/4後升題，第二題沒有新節點可用，16輪結束保持資源2000，避免每輪支付無法記住的試答。

四隻目前從相同狀態與固定試答順序出發，因此結果完全同步，未驗證落後者補題、變異、知識傳播或長期生態。滿容量時由宿主檢查既有題目節點並拒絕新題，尚不是倉鼠自主分配記憶。核心 ISA 未更動。

以 ASan／UBSan 編譯，`detect_leaks=0`，四項針對性測試 PASS：tree-compact-reference-test、tree-compact-world-test、tree-error-trial-test、tree-error-world-test；見 `tree_compact_world_run.log`。未重跑6000隨機 VM 客體。

[更新] 緊湊試錯可在四倉鼠受控世界中運作。[取代] 只在單倉鼠參考模型驗證。[原因] 升題、資源及容量拒答測試通過。[狀態] 高，限本受控配置；多樣化進度及自主容量管理未證實。
