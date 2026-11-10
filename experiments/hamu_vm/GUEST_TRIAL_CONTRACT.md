# Guest 試驗契約：第二輪明確停止原因

日期：2026-11-10，Asia/Taipei。
第一輪基準：45e50ada61ca89f7b78070001e05fa7059c99123。
第二輪基準：7196afcce8476a1546d01266ce6b4757f8f00e10。
本輪分支：codex/hamu-stop-reasons-20261110。

目的：區分「執行能否提交」與「答案是否正確」，讓後續學習實驗有一致邊界。
決策來源及替代方向見 DECISIONS.md 的 D-001～D-007。

## 結果與狀態

| 結果 | guest 狀態 | guest revision | HP 成本 |
|---|---|---|---|
| 核心以 OUT_AREA／SET_AREA(7)／WindowEnd 正常返回，答案尚未評分 | 提交 | 有 D-005 狀態差異則 +1；無差異不增版 | 按實際步數結算 |
| 教師判定答錯 | 不因此撤銷前一筆 guest 執行 | 評分與 guest 錯答回饋各自處理 | 教師獎懲不在本原型範圍 |
| 步數耗盡 | 回滾 | 不增版 | 已執行步數仍結算 |
| 工作 INSERT 或 TREE 容量不足 | 回滾 | 不增版 | 已執行步數仍結算 |
| C++ 例外 | 回滾，結果記錄錯誤 | 不增版 | 已執行步數仍結算 |
| 有變更但 revision 已為 UINT64_MAX | 拒絕提交並回滾 | 保持最大值 | 已執行步數仍結算 |
| 事前窗口範圍／對齊不合法 | 不執行、不修改 | 不增版 | 0 |
| 執行途中無效跳躍或採用無效窗口 | 回滾；Result 保留原因 | 不增版 | 已執行步數仍結算 |

第一輪「無效跳躍與正常停止都只有 stop=true」的缺口，在第二輪以 typed stop reason 區分，參考交易拒絕無效跳躍而恢復前綴。
核心對某些壞 token／未知條件仍採略過，這不屬於嚴格解碼，Completed 也不是答案正確的證明。
原始核心允許半 token 尾端，參考交易事前仍要求整窗口對齊；兩者刻意不同，見 D-007。
`Outcome::InvalidInput` 同時涵蓋事前拒絕和執行中窗口切換失敗：前者未執行、0 成本，後者的 `Result.stop_reason=InvalidWindow` 且須結算已執行步數，不能只看 Outcome 就一概免單。

## 程式位置

- prototypes/guest_trial_contract_ref.hpp：host-only 參考邊界，完整拷貝與回滾，成本另行結算。
- tests/test_guest_trial_contract.cpp：執行真實 simulate_spiral_program，並與舊 FullStateEnvelope 作反例對照。
- run_with_host_fault_for_test 只用於在真實 guest 指令後注入宿主刪除及例外，不是 guest 自己會刪除／丟 C++ 例外。
- src/hamu_vm_core.hpp 本輪只新增停止原因分類與重設；未攔截任意直接呼叫，也未接入強制交易。

## 驗證範圍

1. 舊版 ptr-only 不增版與預算耗盡可提交前綴的兩個反例。
2. TREE_ADD、工作寫入、游標變更、診斷式 no-op 的提交／增版。
3. 真實 guest 步數耗盡、樹容量與 INSERT 容量失敗，以及版本溢位的回滾。
4. 重試再次付費；失敗的讀取軌跡只保留於 Result，guest 狀態恢復。
5. 受控的一位元錯答先提交；教師供給候選 ID 後，guest TREE_ACTION 寫入錯答 mask。
6. 後續回饋中斷不污染先前錯答記憶；錯答 mask 可隨既有 new_his/copy_hamu 機制繼承。
7. 宿主注入例外恢復 generation、工作記憶與交易內 HP 變更，保留既有有效 handle。
8. 正常停止與窗口結束、無效跳躍／窗口切換、重複呼叫的原因重設與保留。
9. 既有窗口跳轉測試與 6,000 組 old/new 狀態快照對照（新增診斷欄位不納入舊 hash）。

本輪不測自主候選選擇、完整題庫學習效率、未提交 handle 封裝、持久化斷電安全或大型樹效能。

## 重現

Ubuntu / g++，由 experiments/hamu_vm 執行：

```sh
make guest-trial-contract-test
make vm-stop-reason-test
# 契約、停止原因與相關基準／相容性測試：
bash scripts/verify_guest_trial_contract.sh
```

腳本可接受外部輸出目錄作為第一個參數；每個測試保存 build.log 與 run.log。
採 C++17、O0、AddressSanitizer + UndefinedBehaviorSanitizer；ASAN_OPTIONS=detect_leaks=0。
腳本涵蓋十個相關測試程式，不等於完整歷史測試集。

## 下一輪

由 GPT 與作者審查 D-003、D-005、D-006、D-007。下一步再設計正式執行入口與成本結算責任，
避免舊的 use_hp 呼叫重複收費；差分優化與未提交引用封裝仍留在後續研究單位。
