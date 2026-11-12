# VM 原始樹引用在失敗交易後的 ABA 重用反例

研究執行者：視窗GPT（ChatGPT 對話視窗）  
日期：2026-11-13  
工作範圍：受控倉鼠 VM 的宿主交易／記憶引用安全，不是 NN Echo/Neg、自由生態或 Zero。

## 來源與版本

U：作者要求樹狀記憶可成長、失敗交易回滾、後代繼承安全，並區分 guest 自行行動與 host 實驗。

F：2026-11-10 全量 VM 原始封存 `hamu_vm_tree_guest_full_state_transaction_20261110.zip`，SHA-256 `9a78c642655d88c556541b7b8f3b3b8e1491e1a3cfc66144fdf463841f08bb16`。本 Git 分支基於 `codex/hamu-stop-reasons-20261110` 固定 commit `44d23b934dbea141e436c24e52b60a500d09e162`；該分支的 `DECISIONS.md` D-005 **已經預告**未提交引用外洩風險。本輪的貢獻是可重現的動態反例及隔離原型，不冒稱前人未注意。

T（本輪真正執行）：在解壓後的全量 Library 基底，用 C++17 `-O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer` 編譯測試。對照 `test_tree_guest_full_state_transaction.cpp`：PASS；新 `test_guest_handle_publication_20261113.cpp`：PASS。

## 反例與防護

原始 `FullStateEnvelope` 失敗交易執行真實 `TREE_ADD` 時，外部宿主取得 `DurableRegistry::Ref(id,generation,lineage)`，再 abort，原 raw ref 立即無效；下一筆交易成功重用相同 id/generation/lineage，原 raw ref **重新有效**（ABA）。因為記憶與 generation 都回滾，無法讓已洩漏的引用一起回收。

新增 host-only `PublishedRefs` 能力票據原型：未 commit 不能對外 mint ticket；成功後才發放；失敗刪除回滾維持既有票據；成功刪除／重用則舊票據失效。這並非正式 guest 能呼叫的指令，也沒有封閉 raw `DurableRegistry` 對宿主的直接存取。

可重現命令（在 `experiments/hamu_vm/`）：

```sh
g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer \
  tests/test_guest_handle_publication_20261113.cpp -o /tmp/hamu_guest_handle_pub
ASAN_OPTIONS=detect_leaks=0 /tmp/hamu_guest_handle_pub
```

本輪 Library 基底的實際輸出（exit 0）：

```text
PASS raw aborted-handle ABA reproduced; publication-gated host token tests passed
```

已保留失敗：測試夾具最初用 `#define main` include 上游 `.cpp`，遭內層 macro undef 造成重複 main 編譯錯誤；改為包含 `tree_generation_registry_fixture.hpp` 及複用 envelope 定義後 PASS。既有 fixture 的 `prior_generation_main()` 無 return 警告未消除。

## 結論與限制

[更新] FullState 回滾不能自動撤銷已交付給外部的數字引用；發布時點必須成為 transaction contract 的一部分。

[取代] 「狀態回滾即不可能有失敗交易的跨交易引用污染」之過度推論。

[原因] ABA 取決於 ID+generation+lineage 再次被使用，並不取決於快照 bytes 已恢復。

[狀態] Library 基底動態反例 PASS，宿主發票閘門原型 PASS；**本輪尚未在 Git 的 `44d23b9` checkout 實際編譯此新檔**。這次只增添測試與報告，不改正式 VM、guest ISA、HP 收費入口。票據表沒有持久化、並行鎖、容量清理或 crash recovery；直接取 raw ref 的宿主仍可繞過。此原型不能宣稱 VM 對外引用安全。

A／下輪：在 Git 分支重跑回歸；把 typed InvalidJump／InvalidWindow／StepBudget 回滾與票據發布連成同一個正式入口。需明確定義中途失敗不得發票、舊已提交票據在 abort 後仍有效、宿主不得繞過 guard；再評估持久化 issuance high-water、跨代 lineage 與差分日誌。NVIDIA：未呼叫，本輪單點 VM 測試。

備註：本回合沒有訓練 NN、沒有生命週期／HP 長跑，沒有證明倉鼠自行選擇或分享記憶。
