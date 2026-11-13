# [視窗GPT] VM 交易發布閘門 × 發行器 epoch 組合回歸

日期：2026-11-13。研究執行者：視窗GPT（ChatGPT 對話視窗）。
Work ID：HAMU-VM-COMPOSITION-20261113。
狀態：受控 VM 的 host-only 動態反例及候選防護；正式 VM 未修補。

## 來源及責任

U：原作者要求樹記憶可成長、回滾、正確的成本及後代繼承；本次「跨原型組合回歸」屬視窗 GPT 的新增研究。
F：Library 全量基底 `hamu_vm_tree_guest_full_state_transaction_20261110.zip`，SHA256 `9a78c642655d88c556541b7b8f3b3b8e1491e1a3cfc66144fdf463841f08bb16`；前輪 [視窗GPT PR #17](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/17) 和 [PR #22](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/22)。本支系從 PR #22 commit `ba8aa1cd7e4fd0be0f8ebed7f84d8b95241401fa` 建立；其上游 Codex `codex/hamu-stop-reasons-20261110` 參考 SHA `44d23b934dbea141e436c24e52b60a500d09e162`。未覆寫 Codex 分支。
T：2026-11-13 在上述 Library ZIP 實際解壓、覆入先前兩個測試（僅替 session-epoch 測試的 main 加 `#ifndef HAMU_SESSION_EPOCH_NO_MAIN`），C++17 ASan/UBSan 重新編譯四個測試，均 exit 0。**沒有在完整 Git checkout 重建測試，僅核對公開提交測試檔的 Git blob SHA 與本地已測原始碼相同。**
A：應由單一、不能被跳過的 API 同時執行 guest transaction、commit 與 ticket issuance；這一方向未接正式 VM。

## 新反例

PR #17 的 `PublishedRefs` 禁止在交易中發票；PR #22 的 `SessionPublishedRefs` 用 `(issuer_epoch, serial)` 避免跨發行器重號，但新類別的 `publish()` **沒有檢查交易是否尚未提交**。

實測負面對照：真 guest `TREE_ADD` 建立節點 1，當次 host `FullStateEnvelope` 尚未 commit 時，`SessionPublishedRefs.publish(1)` 已接受並發票；交易 abort 後引用暫時失效；下個成功 `TREE_ADD` 重新使用同樣 ID/generation/lineage，舊票據重新有效（ABA）。這不需要發行器重啟，所以 issuer epoch 無法單獨解決。

候選防護 `TransactionAwareEpochRefs` 讓發票器只能在交易外 `publish()`；未提交拒絕、成功 commit 後發票、abort 刪除不傷及已提交票據、成功刪除／回收使舊票據失效、新 serial 不重複，均通過本輪測試。**宿主仍可直接接觸底層 Registry 或原先不受保護的 SessionPublishedRefs；此原型本身不是不可繞過的安全界面。**

## 測試與局限

本輪命令在已展開的 `hamu_run` 目錄執行：

```sh
for t in tree_guest_full_state_transaction guest_handle_publication_20261113 guest_handle_session_epoch_20261113 guest_handle_composition_20261113; do
  g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer \
    "tests/test_$t.cpp" -o "/tmp/test_$t"
  ASAN_OPTIONS=detect_leaks=0 "/tmp/test_$t"
done
```

實際結果：

```text
PASS: full-state host checkpoint rolls back work, generation, HP, exception and revision overflow
PASS raw aborted-handle ABA reproduced; publication-gated host token tests passed
PASS: baseline ticket reuse alias reproduced; issuer epoch, deletion, overflow guards pass (host-only)
PASS: epoch issuer lost transaction guard (ABA reproduced); composed host guard blocks provisional publication
```

第一次編譯失敗：嘗試用 `#define main` rename 內含 epoch 原型的測試，但內部 `#undef main` 造成 duplicate-main。改為在 session-epoch 測試 main 外加條件編譯 guard 後重新編譯成功；直接執行該舊測試的行為不變。既有 fixture `prior_generation_main()` 無 return 警告仍在。

[更新] 發票時間與發行器身分必須同時納入引用契約。
[取代] PR #17 發票閘門與 PR #22 epoch 高水位可自動安全組合的推論。
[原因] 重新實作 session publisher 時漏掉未提交交易限制。
[狀態] 局部反例高信心；正式執行路由、typed InvalidJump/InvalidWindow/BudgetExhausted、一次性 HP 付費、session epoch 磁碟恢復及客體自治仍未驗證。

本支僅改動三件：`tests/test_guest_handle_session_epoch_20261113.cpp`（guard 兩行）、`tests/test_guest_handle_composition_20261113.cpp`（新測試）、本報告。私人完整 logs、腳本與封存保留 Library `/倉鼠世界/程式版本/hamu_vm_guest_publication_composition_20261113.zip`，未把私人聊天或 Library 原稿直接上傳。

下一輪：在 Codex typed-stop 的真正 Git checkout 接上此組合閘門，對 InvalidJump、InvalidWindow、BudgetExhausted 交錯 commit／abort／HP 成本做獨立測試；若要定案正式 API，應防止直接取得不受限制的 registry/ref。
