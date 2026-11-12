# 試答附帶位元的客體 VM 讀寫（2026-11-01）

使用者：「繼續」。沿用上一輪題目節點／答案位元分離方向，原話見 `conversation_20261101_compact_direction.md`；本輪回應摘要見 `conversation_20261101_compact_vm_io.md`。

更動：`src/tree_compact_reference.hpp` 將宿主直接操作附帶位元改為 VM READ／WRITE 指令，正解先寫值再寫存在旗標；`tests/test_tree_compact_reference.cpp` 更新輸出辨識；`README.md` 更新；新增本檔、`tree_compact_vm_io_run.log`、`conversation_20261101_compact_vm_io.md`，共六檔。

`make tree-compact-reference-test tree-error-trial-test tree-error-world-test` 以 ASan／UBSan 全通過。七題×八錯=56錯、七節點及84附帶位；已知正解回用與後代繼承通過。原四倉鼠世界測試亦通過，仍使用舊的每錯一節點路徑；命令和 stdout 見 log。

界線：宿主仍根據 VM 回傳的節點 ID 計算實體位址並生成針對該地址的 VM 程式，亦由宿主讀取暫存器決定下一選項。只把持續位元的物理讀寫交給 VM，不是倉鼠自主動態定位／完整選擇策略。未接入四倉鼠世界，未驗證長題路徑或容量競爭；核心 ISA 未改，6000 隨機客體未重跑。
