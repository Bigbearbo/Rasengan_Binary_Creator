# VM 動態讀取題目附帶記憶（2026-11-01）

使用者：「繼續」。承接前輪每題節點／答案旗標設計；本輪 AI 簡略回應見 `conversation_20261101_guest_address.md`。

更動：`src/tree_compact_reference.hpp` 新增客體按五位節點 ID 移動讀取指標的程式，`next` 改用該程式；`tests/test_tree_compact_reference.cpp` 新增樹 ID31 的邊界案例；更新 `README.md`；新增本檔、`tree_compact_guest_address_run.log`、`conversation_20261101_guest_address.md`，共六檔。

`make tree-compact-reference-test tree-error-trial-test tree-error-world-test` ASan／UBSan 三項 PASS。原七題56錯／七題節點／84附帶位與後代繼承仍通過。另建30個節點後使新題位於 ID31，錯答0後回報下一個1，再標正解7並回用7；讀取地址由 VM 的節點 ID 位元判斷。詳細命令／輸出見 log。

邊界：客體現只完成附帶資料的動態讀取；寫入路徑仍由宿主算 ID 對應地址生成 VM WRITE，讀回後的選項判斷也在宿主。世界仍使用舊的每錯一節點實作，未聲稱其已遷移；固定題目鍵仍需宿主提供。核心 ISA 未改，6000 隨機 VM 未重跑。
