# 緊湊試錯：落後者補題驗證

2026-11-01。更動：`src/tree_compact_reference.hpp`、`src/tree_compact_world.cpp`、`tests/test_tree_compact_world.cpp`、`README.md`，新增本報告、`results/tree_compact_laggard_run.log`、`results/conversation_20261101_laggard.md`。

VM 選答以個體 ID 作循環起點，已知正解仍優先。當全世界升第二題，個體若尚未掌握第一題，先補第一題。首題第6輪3/4升題，第7輪落後者補完，次題第11輪4/4。已掌握者每輪仍答題，按現有環境規則扣100、答對補200，所以總資源4000→3600；初估2400忽略重複答對的獎勵，已修正測試。容量1情況，首題第7輪全掌握，第二題無節點可配，後續資源保持2900。

ASan／UBSan 三項 PASS：tree-compact-world-test、tree-compact-reference-test、tree-error-world-test。原四倉鼠世界未更動。沒有測知識分享、繁殖、長期資源均衡；不同起點由宿主傳入，非個體自主產生。既有答對獎勵可讓已掌握個體逐輪增加資源，後續研究應單獨衡量。

[更新] 過半升題後落後者可補前題。[取代] 四隻同序同步進度。[原因] 不同起點的客體掃描與世界補題測試通過。[狀態] 高，限兩題受控世界；起點仍由宿主指定。
