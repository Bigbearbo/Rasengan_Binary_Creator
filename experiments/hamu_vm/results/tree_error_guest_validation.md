# 客體 VM 遍歷錯答樹（2026-11-01）

使用者接續指示：「好，繼續」。沿用上輪「題目是資源、錯答死記與多數掌握升題」方向。

修改檔案：`src/tree_error_trial.hpp`、`tests/test_tree_error_trial.cpp`、`README.md`；新增本檔、`results/tree_error_guest_run.log`、`results/conversation_20261101_guest_search.md`。共六個檔案。核心 ISA 與世界參數沒有改動。

宿主產生固定八選項的 VM 指令序列，客體先逐一以 TREE_FIND／TREE_ACTION 找答對節點，再逐一查缺席節點；由 VM 條件跳轉選擇，將有效位及三位選項寫入輸出。每項重置樹根 ID，讀取預先清零的五位輸出；命中才停機。`tree_error_next_host` 是既有遞回對照，世界改用一趟客體 VM 選擇。

ASan／UBSan：`make tree-error-trial-test tree-error-world-test` 通過。十六種錯答記錄分布 × 九個起點與宿主遞回結果一致，涵蓋已知正解優先、無未試選項回傳 -1、跨題分離及後代繼承。O2：`make tree-error-world` 通過，升題仍在第六輪 3/4 掌握，第十輪第二題 4/4；總資源 4000→3200。完整命令及 stdout 見 `tree_error_guest_run.log`，並非後續長期生態測試。

修正過程：初版以 VM 的局部跳轉計算錯位（VM 一個 opcode/參數占兩個詞），改用寬距跳轉及配對位移；初版在同一程式內只移動暫存器游標，未清空樹根 ID，導致題目錯誤巢狀，改用輸出區清零的五位重置 ID。修正後重跑全部上述測試。

界線：指令展開由宿主生成，不是客體自行遞回或改寫搜尋程式；宿主仍供題目鍵、起點、答題成本、正解回饋和升題門檻。八個候選、兩道固定答案及獨立31節點樹未改。沒有容量枯竭、崩潰交易、語義歸納或壓縮實驗；不能宣稱嚴格 Zero 或無先驗自主學習。舊6000隨機 VM 未重跑。
