# 2026-11-10 第二輪：明確停止原因與無效跳躍回滾

基準提交：7196afcce8476a1546d01266ce6b4757f8f00e10。
本輪分支：codex/hamu-stop-reasons-20261110。
作者要求建立代理繼續倉鼠世界；主代理分派三個子代理並整合實作與驗證。

## 分工與審查

- stop_reason_impl：僅修改 VM 核心，新增 VmStopReason 與診斷欄位，不改舊 stop bool 語義或成本。
- stop_reason_tests：修改參考交易邊界與測試，將前輪無效跳躍 KNOWN_GAP 改成拒絕提交的正式斷言。
- independent_review：只讀審查，提供 deferred/immediate 窗口切換反例，指出 InvalidInput 的成本不能一概而論。
- 主代理：處理 D-006／D-007、建置目標、回歸腳本、文件、審查補測與本機整合驗證。

審查未提出未處理的阻擋問題。以上是 Codex 子代理協作，不表示原本 ChatGPT 對話的 GPT 已審查本輪。

## 行為改變

原始解釋器現在可以回報：

- WindowEnd、OutArea、SetAreaStop：明確正常結束。
- InvalidWindow、InvalidJumpTarget：窗口或跳躍失敗。
- BudgetExhausted、WorkCapacity、TreeCapacity：資源限制。
- None、AlreadyStopped：尚未產生結果／已停止而未再次執行。

Reference Trial 只允許三種明確正常原因提交，其餘拒絕或另回報失敗；Result 保留本次原因與成本。
無效跳躍／採用無效窗口時，前綴的 tree、output、register、cursor 和版本不再由參考交易提交。
交易外仍按實際步數扣 HP；重試再次付費。答錯仍與執行失敗分開，D-001～D-005 未改。

## 相容性決定

D-006 由第一輪標註缺口，推進為原因分類與參考回滾。
D-007 保留 legacy 壞 token 略過、原始半 token 窗口、SET_PTR2 延後生效的行為。
WindowEnd 保持 stop=false；同一個原始窗口可以重跑。OUT_AREA／SET_AREA(7) 保持 stop=true。
已停止的重入保留先前原因；None／WindowEnd 改為 AlreadyStopped，不誤稱有新的執行。
write_prob 清除原因與嘗試旗標；活躍原始呼叫重新記錄原因。

原始核心仍只分類，**沒有強制所有直接呼叫者經過交易**。繞開 Reference Trial 的直接呼叫仍可能留下前綴；這點不是本輪已完成的成果。

## 本機實測

環境：WSL Ubuntu-24.04，g++ 13.3.0；C++17、-O0 -g0、ASan/UBSan。
執行日期：2026-11-10（Asia/Taipei）。
命令：在 experiments/hamu_vm 執行 `bash scripts/verify_guest_trial_contract.sh`。
十個測試程式全部編譯與執行退出 0，各 build.log 為空，未產生編譯警告：

1. tree_guest_revision_bypass
2. tree_guest_transaction_envelope
3. tree_guest_full_state_transaction
4. guest_trial_contract
5. tree_reject_mask
6. work_insert_capacity
7. vm
8. vm_stop_reason
9. vm_unary_skip
10. vm_decode_snapshot

關鍵輸出：

```text
PASS invalid jump rolls back guest prefix; reason survives rollback and retry costs HP
PASS OUT_AREA, SET_AREA(7), window end commit with distinct normal reasons
PASS invalid deferred/immediate window switch rolls back prior output and cursors
PASS raw normal exits, legacy stop bool, stale reason reset and stopped reentry
PASS raw invalid initial/window switches and jump targets; deferred/partial-token compatibility
PASS budget, strict INSERT and TREE capacity reasons preserve existing flags
PASS: VM opcode loop skips unary lengths 110 and 1110 bit by bit
PASS 6000 old/new VM state snapshots: 88c085a021cbfdb7
```

主代理依審查建議補入 write_prob 重設與 WindowEnd 原始重跑斷言，另跑 `make vm-stop-reason-test` 編譯與執行均退出 0、無警告。
舊快照 hash 未包含新診斷欄位；新原因另由明確測試驗證。這不等於全部歷史測試或全生態長期實驗。

## 仍未完成與 GPT 審查重點

- 正式執行入口尚未強制交易；下一輪應先盤點 raw interpreter 呼叫點和 HP 結算點，再決定遷移範圍，避免重複扣費。
- InvalidInput 可能是事前拒絕（0 成本），或採用無效窗口時失敗（有成本）；須連同 Result.stop_reason／attempted_steps 解讀。
- 正常 WindowEnd 仍可能包含被略過的壞 token；未引入嚴格解碼或新 ABI。
- D-005 的 revision 不是整個生物狀態的並行鎖，交易外扣 HP 不增加 guest revision。
- 全拷貝成本、未提交 handle 外流、斷電持久化與自主學習效率均未處理。

請原 GPT 主要檢查 D-006／D-007 是否符合既有研究設定，尤其窗口延後生效、正常結束與執行失敗的界線。
