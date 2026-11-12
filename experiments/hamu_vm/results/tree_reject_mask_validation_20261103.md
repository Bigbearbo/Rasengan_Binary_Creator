# 倉鼠世界｜分頁樹八候選錯答遮罩（2026-11-03）

## 來源與範圍

U：作者既有研究主線是「題目作為資源，先用樹死記錯誤答案、逐次試未試過的答案，之後再研究壓縮與歸納」；優先可成長的正確設計。
F：基底為 Library `/倉鼠世界/程式版本/hamu_vm_tree_wide_segment_migration_20261102.zip`，不是較早的 `tree_segmented_growth`。原始 ZIP SHA256 見本封存 `results/tree_reject_mask_base_sha256_20261103.txt`。
A：本輪選擇把 8 候選的「曾答錯」位元直接放入分頁樹 canonical row，先驗證儲存、客體操作、回滾與遺傳，不宣稱已接上完整題庫選擇策略。

## 程式變更（F，本輪新增）

1. `src/hamu_vm_core.hpp` 新增 opt-in `tree_reject_mask_enabled=false`；預設不改既有 ABI。僅在 `tree_segmented_enabled=true` 下開啟功能。舊 `TREE_ACTION` 參數 0/1 的 2-bit 已確認答案功能完全保留。
2. opt-in 時 `TREE_ACTION param=2` 讀取、`param=3` 記錄一個錯答；候選編號 0–7 由 `val_reg[tree_id_bits+1..tree_id_bits+3]` 三位指定。節點 ID 仍在 `val_reg[0..tree_id_bits-1]`。回傳 `val_reg[tree_id_bits]` 表示該候選已被拒絕，`val_reg[tree_id_bits+4]` 表示節點存在。要求 register 至少 `tree_id_bits+5` 位，避免把不存在的節點當作未試過。
3. 分頁 row 原有 bit 0 live、bit 1–3 action、bit 4–6 key、bit 7–22 parent（16 位）。新遮罩使用 bit 23–30，保留 bit31。canonical row 仍是 32-bit `uint32_t`，不增加每節點 row bytes；但開啟時 16-bit handle 的暫存器至少需要 21 位，不能聲稱 VM 總記憶零增量。
4. 重複標記同一錯答不改資料；同回合因 TREE_ADD 容量不足回滾時，已標記的錯答一併回滾。子代繼承 canonical mask，衍生索引照舊重建；不同 mask-ABI 的 snapshot 拒絕互拷。新節點 row 初始化不帶舊洞 mask。
5. `tests/test_tree_reject_mask.cpp` 新增獨立測試；`Makefile` 新增 `segmented-reject-mask-test`。未修改其他來源程式、題庫或既有測試內容。

## 實測（T，本輪重新編譯／執行）

使用 `g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer` 跑新測試、寬→分頁遷移、分頁樹 600 paths、寬樹索引、基礎樹 VM；寬樹增長測試為 `-O1 -g` sanitizer；`tests/test_vm.cpp` 使用既有 Makefile `-O1 -g` sanitizer，含 6000 隨機客體。全部 PASS，原始編譯與輸出在 `results/tree_reject_mask_regression_20261103.log`。

新測試覆蓋 8 候選初始清零、錯答 0/3/7 記錄與獨立查詢、重複標記、既有 `TREE_ACTION` 不覆蓋 mask、容量失敗後回滾、子代繼承與親代隔離、mask ABI 不相容拒絕、功能未開時保持舊行為、不存在節點的明確狀態。原始基底的 10,000 路徑 O2 壓力測試沒有在本輪重新執行；不可當成本輪 PASS。

## 結論、限制與下一步

[更新] 分頁樹已具備 opt-in、客體可用的八候選「錯答遮罩」原語，與 2-bit 確認答案並存，保留回滾與遺傳。
[取代] 「分頁樹葉片尚無八候選錯答位元存取」；但沒有取代「完整八候選題庫策略尚未整合」。
[原因] 利用原 32-bit row 的 8 個未用位，避開獨立位元表擴容時的同步問題；在同一 VM 回合交易日誌中記錄變更。
[狀態] 高（列出之程式與測試）；世界級學習、跨格式狀態遷移、資源成本仍未驗證。

重要界線：目前 `TREE_ACTION` 已確認答案仍只有 2 位（0–3），不能記錄 4–7 的「正確答案」，所以這是**八候選錯答記憶原語**，不是完整 8 候選學習器。下一輪應先擴充／版本化已確認答案到 3 位並加入「選未拒絕候選→答錯標記→答對確認」的端到端題庫測試；必須測試所有 8 個候選都被拒絕時的異常處理，不應直接當作成功學會。更大範圍：HP/索引/分頁配置總成本、跨 16 位 handle、自由生態／Zero 尚未實測。
