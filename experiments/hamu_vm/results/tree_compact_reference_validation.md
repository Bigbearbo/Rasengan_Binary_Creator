# 題目節點與試答狀態分離（2026-11-01）

使用者原話：「不對啊，節點只要能吃下題目長度就夠了，試答案可以用排序或者子樹？繼續」。

[更新] 每次錯答使用一個新節點是第一版儲存格式，並非節點編號的必要限制。[取代] 上一輪將31節點解讀成死背容量硬上限的回答。[原因] 題目可由樹節點／路徑定位，選項試錯可用每題八位旗標及正解標記獨立儲存，或設答案子樹；物理記憶體仍有限。[狀態] 高（佈局原型實測），對客體可執行性尚未驗證。

新增 `src/tree_compact_reference.hpp`（宿主對照實作）、`tests/test_tree_compact_reference.cpp`，更新 `Makefile`、`README.md`，新增本檔、`tree_compact_reference_run.log`、`conversation_20261101_compact_direction.md`；共七檔。`make tree-compact-reference-test tree-error-trial-test tree-error-world-test` ASan／UBSan 通過。七道題×八次錯答=56次，消耗七個題目節點，另用84位持續記憶；答對回用與後代繼承通過。舊試錯世界與客體遍歷測試亦通過。記錄見 log。

限制：參考佈局用宿主按 VM 找到的節點 ID 計算附帶位址，讀寫工作區位元；客體 VM 尚無直接的動態位址遍歷實作，現行四倉鼠世界仍走每錯一節點路徑。固定三位題目鍵只有1–7七種；較長題目需多段樹路徑及相應節點，不可說每個任意長題目只要一個節點。31是當前樹 ID 數量，與答案位元容量不同；核心ISA未變，未重跑6000隨機VM。
