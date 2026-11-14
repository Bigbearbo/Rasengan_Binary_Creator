# 輸入詞回饋與容量拒答（2026-11-01）

使用者：「繼續」。承接前輪完整方向 `conversation_20261101_question_resource.md`；本輪回應摘要 `conversation_20261101_input_feedback.md`。

更動：`src/tree_error_trial.hpp` 的回饋 VM 程式增設 input+2 螺旋詞題目鍵、TREE_ADD_REG 路徑及樹空節點檢查；`src/tree_error_world.cpp` 改用輸入回饋和付費前容量閘門，可設定節點數；`tests/test_tree_error_trial.cpp` 增加跨題回饋隔離和滿樹預檢；`tests/test_tree_error_world.cpp` 加四節點對照；更新 `README.md`；新增本檔、`tree_error_input_feedback_run.log` 和 `conversation_20261101_input_feedback.md`。共八檔。

`make tree-error-trial-test tree-error-world-test tree-error-world`：ASan／UBSan 兩組 PASS，O2 世界原容量31第6輪 3/4 掌握升題，第10輪題二全員掌握、資源4000→3200。容量4時三輪各四次錯答後每隻樹的根加三個錯節點占滿；從第四至十六輪不再付費，資源停2800，未升題。詳細命令與輸出見 log。

[更新] 有限記憶保護資源但不保證學會。[取代] 樹滿時仍試答、記不住又重複耗費的流程。[原因] 付費前容量閘門令小容量世界停在第一題；原容量世界行為未變。[狀態] 高（這兩組固定環境實測）。

界線：容量閘門是宿主檢查樹節點，不是客體自主計費、擴容或壓縮；每輪題目仍由環境提供，教師判分和獎懲仍在宿主。這只是在樹滿時拒絕可能浪費的嘗試；沒有完成落後者補題、樹壓縮或可變資料語義。核心 ISA 未改、6000 隨機 VM 未重跑。
