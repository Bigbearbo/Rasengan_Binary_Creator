# [視窗GPT] VM 跨發行器票據重用反例與 issuer epoch（2026-11-13）

研究執行者：視窗GPT（ChatGPT 對話視窗）
Work ID: HAMU-VM-REF-EPOCH-20261113
研究範圍：受控 VM 的宿主公開引用原型，**不是正式 VM 修補、客體自治或 Zero 世界實驗**。

## 來源與證據

U（作者）：倉鼠世界採用「題目是資源、以樹記下錯答、逐步找到新答案」的程式型小 AI 路線；重視樹擴容、回滾、記憶權限與後代傳承。

F：基於 Library 完整 VM 封存 `hamu_vm_tree_guest_full_state_transaction_20261110.zip`（SHA256 `9a78c642655d88c556541b7b8f3b3b8e1491e1a3cfc66144fdf463841f08bb16`）及上一輪 [PR #17](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/17) 的 `PublishedRefs` 測試。現有 `codex/hamu-stop-reasons-20261110` 已處理 typed stop reason 與參考 HP 結算，這一輪沒有改動其核心或冒稱重跑該分支所有測試。既有 D-005 早已指出 raw uncommitted references 風險；上輪 #17 處理的是交易內發票，這輪處理**發行器重建**。

T（視窗GPT 2026-11-13 本輪實際編譯）：

以 C++17 `-O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer`，在上述 **Library ZIP** 展開目錄，加上本分支兩個測試檔，實際執行以下三個程式，均 exit 0：

```sh
cd hamu_run
for t in tree_guest_full_state_transaction guest_handle_publication_20261113 guest_handle_session_epoch_20261113; do
  g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer "tests/test_${t}.cpp" -o "/tmp/test_${t}"
  ASAN_OPTIONS=detect_leaks=0 "/tmp/test_${t}"
done
```

結果：

```text
PASS: full-state host checkpoint rolls back work, generation, HP, exception and revision overflow
PASS raw aborted-handle ABA reproduced; publication-gated host token tests passed
PASS: baseline ticket reuse alias reproduced; issuer epoch, deletion, overflow guards pass (host-only)
```

繼承 `prior_generation_main()` 缺 return 的原有編譯警告；ASan/UBSan 沒有在這三個執行檔檢出錯誤。**這是 Library 全量基底重測，不是獨立重建當前 Git stop-reasons checkout。** Git 新增測試內容與本地實測原始碼的 blob SHA 已逐一核對；Git branch 尚需乾淨 checkout 重編驗收。

## 實驗觀察

原 `PublishedRefs` 只有 `uint64_t ticket`，每個新物件從序號 1 發行。測試先透過真實 guest `TREE_ADD` 建立不同節點。舊發行器為節點 1 發行票據 1 後銷毀，新發行器為節點 2 再發行票據 1；舊票據被新發行器當作節點 2 的有效票據，即使原節點 1 已刪除。

新增的宿主端 `SessionPublishedRefs` 用 `(issuer_epoch, serial)` 區分票據，由 `IssuerHighwater` 提供 epoch；跨發行器但高水位未回退時，舊票據拒收，新票據有效，已刪節點的票據失效，epoch 溢位拒絕。

**負面對照**：若從過時 checkpoint 還原發號 high-water，新發行器仍可取得相同 epoch 和 serial，使舊票據重新被接受。這只在記憶體中模擬 checkpoint，沒有做磁碟原子性或斷電恢復驗證。首次反例夾具誤以為刪掉 ID 1 後下一新增節點會拿到 ID 3，實際使用最低空位 ID 1；修正的是測試預期，非正式核心。

[更新] host-only 發票閘門必須同時處理 **交易提交** 與 **跨發行器編號生命週期**。
[取代] 以成功 commit 後 mint 即可防止所有 token ABA 的過度解讀。
[原因] 票據 ID 是可重用的局部計數器，不附發行器唯一性。
[狀態] 上述局部動態反例高；正式 crash-safe persistence、跨程序、並行、客體 VM capability API、安全防偽均未驗證。

A：先決定 token 是 session-local（重啟全失效）還是 persistent（須持久保存發號與引用紀錄），再選可恢復的 issuer/serial 發號機制。此原型用可猜測整數，**不是不可偽造的安全授權票據**。下一輪在當前 Git checkout 實測 D-006 的 `InvalidJump`／`InvalidWindow`／`StepBudget` 加上公開票據閘門及交易外一次性 HP 成本；大型樹再比較差分日誌與全狀態複製。

## 本 PR 改動

`tests/test_guest_handle_publication_20261113.cpp`：只替現有 main 增加 opt-out guard，以便其他獨立測試 include 原型；舊 main 流程不改。
`tests/test_guest_handle_session_epoch_20261113.cpp`：新增跨發行器 token ABA、發號高水位回退、刪除失效及溢位回歸。
`results/guest_handle_session_epoch_20261113.md`：本次來源、命令、結果、失敗、限制與下一步。

本 PR 基於視窗GPT 的 PR #17，與 Codex 核心變更隔離。不得自動合併或把局部宿主實驗當作 VM 全部入口安全。
