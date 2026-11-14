# 2026-11-03 三位元答案 ABI 試驗

U：題目作資源，先樹狀死記錯答再探索壓縮；重視可成長與繼承。
F：以 Library `hamu_vm_tree_reject_exhaustion_20261103.zip` 為基準。
A：分頁樹 32-bit row 的 bit31 可用於已確認答案第三位，既有 row[1..3] 保持確認旗標與低兩位；row[23..30] 是八候選拒絕遮罩。新 opt-in `tree_confirm_three_bits_enabled`，TREE_ACTION(4) 讀、(5) 寫；舊 0/1 不變，舊 1 寫入時清除高位以避免新讀取不一致；跨 ABI 快照 copy 明確拒絕。這是擴充實驗，非正式遷移。
T：g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_confirm_three_bits.cpp -o test_confirm3 && ASAN_OPTIONS=detect_leaks=0 ./test_confirm3
PASS 8 three-bit answers: commit/read, mask isolation, inheritance, rollback, ABI gate
T：原有 test_tree_reject_exhaustion.cpp、test_tree_reject_mask.cpp 亦重新編譯 ASan/UBSan，分別 PASS 256 masks、PASS opt-in eight-candidate rejection。以上為本輪執行；未重跑全量世界測試。
已知限制：候選挑選仍由宿主測試策略；未做端到端八候選客體學習器、舊版資料遷移、世界 HP 成本；尚需測試刪除重用與舊 param1 混用情況。
