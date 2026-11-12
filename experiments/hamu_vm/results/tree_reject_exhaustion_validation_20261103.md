# 八候選遮罩窮盡狀態／選擇策略獨立驗證（2026-11-03）

U：作者要求先死記錯答、下次選未試答案，題目作為資源；不把窮盡誤判成學會。
F：基於 `hamu_vm_tree_reject_mask_20261103.zip`，原 VM 不變。新增 `tests/test_tree_reject_exhaustion.cpp`，採用客體 `TREE_ACTION 2/3` 讀寫拒絕位元；宿主提供暫時的「最低編號未拒絕」策略。這不是客體自主選擇，也不是 8 候選端到端題庫。
T：`g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_reject_exhaustion.cpp -o test_exhaustion`；`ASAN_OPTIONS=detect_leaks=0 ./test_exhaustion`，PASS。逐一建構全部 256 種 8-bit 遮罩，以客體 VM 指令標記與讀回；每種遮罩都確認不選已拒絕候選、優先選最小未拒絕編號；全拒絕 0xff 回傳 `std::nullopt`，不將窮盡當作成功、不修改 canonical pages。此測試為 256 種靜態遮罩狀態，不等於 256 題完整學習。
A：[更新] 現有 VM 已足以供外部策略識別「八個答案全部失敗」而不誤選；需要將窮盡狀態明確納入客體決策協議。[取代] 不能因已有八候選遮罩就聲稱已完成八候選學習。[原因] 實際驗證所有遮罩狀態，但正解仍是 2-bit，宿主選擇策略尚未移入客體。[狀態] 256 狀態測試高；完整學習器未驗證。
下一步：擴展已確認答案到 3-bit，規劃新 ABI 與舊 snapshot 遷移；實作客體可用的候選選擇、窮盡異常輸出與受控題庫完整回合。保留原 ZIP 作可重播基準。
