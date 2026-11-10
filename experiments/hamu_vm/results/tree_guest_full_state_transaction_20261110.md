# 2026-11-10 Full-state host transaction experiment
U: 作者要求可成長的受控題庫、錯答樹、VM 內外一致性及安全回滾。
F: Library `hamu_vm_tree_guest_transaction_envelope_20261110.zip`，包含 host-only `GuestTreeEnvelope`；原始正式 VM 核心不改。
T: 新增 `tests/test_tree_guest_full_state_transaction.cpp`，C++17 `-O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer` 實際編譯執行 PASS（ASAN_OPTIONS=detect_leaks=0）。
[更新] 新的 host-only `FullStateEnvelope` 在交易開始時複製 Hamster 狀態及 generation/lineage/revision；成功時依 canonical tree、memory、hp、register 差異更新 revision；回傳 false、exception 或 revision 溢位則恢復所有已備份狀態。測試覆蓋 TREE_ADD、work-only 寫入、刪除後 generation 回滾、HP 例外回滾、溢位回滾。
[取代] 前一版僅能回滾 canonical tree，現在此獨立宿主原型可恢復較完整的 VM 記憶與世代資料，但仍非正式 VM 強制入口。
[原因] DurableRegistry::restore 禁止 generation 倒退，因此不能直接拿它來撤銷同一交易內的 erase；改用完整宿主記憶體檢查點做原型。注意 vector<bool> 的 auto proxy 會跟隨底層位元變化，測試已改用 bool 值拷貝。
[狀態] 局部實測高；O(total Hamster state) 每次交易完整複製不適合作為最終大型樹實作。若有外部已洩露的暫時 handle，單純 generation rollback 仍可能導致語義問題，需限制未提交引用外流。還未涵蓋所有 Hamster 欄位的成功變更偵測（例如單獨 ptr、log、stop），未做檔案 crash-atomicity、VM execute 強制路由、HP 成本、自由生態、Zero 或純01教學。
A: 下一輪先測 guest 指令在完整交易邊界內的可觀測成功/失敗語義，再改成差分日誌或 copy-on-write，避免每題複製整個樹。
重現：`cd hamu_run && g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_guest_full_state_transaction.cpp -o /tmp/hamu_full_state && ASAN_OPTIONS=detect_leaks=0 /tmp/hamu_full_state`
輸出：`PASS: full-state host checkpoint rolls back work, generation, HP, exception and revision overflow`
已知繼承警告：`prior_generation_main()` no return；本輪最初 include main 重複、後來 vector<bool> proxy 測試失敗均已修正。
