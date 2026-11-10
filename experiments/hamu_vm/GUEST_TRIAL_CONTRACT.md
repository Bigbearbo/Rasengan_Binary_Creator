# Guest 試驗契約：第一輪可執行規格

日期：2026-11-10，Asia/Taipei。
基準：45e50ada61ca89f7b78070001e05fa7059c99123。
本輪分支：codex/hamu-guest-contract-20261110。

目的：區分「執行能否提交」與「答案是否正確」，讓後續學習實驗有一致邊界。
決策來源及替代方向見 DECISIONS.md 的 D-001～D-006。

## 結果與狀態

| 結果 | guest 狀態 | guest revision | HP 成本 |
|---|---|---|---|
| 核心正常返回，答案尚未評分 | 提交 | 有 D-005 狀態差異則 +1；無差異不增版 | 按實際步數結算 |
| 教師判定答錯 | 不因此撤銷前一筆 guest 執行 | 評分與 guest 錯答回饋各自處理 | 教師獎懲不在本原型範圍 |
| 步數耗盡 | 回滾 | 不增版 | 已執行步數仍結算 |
| 工作 INSERT 或 TREE 容量不足 | 回滾 | 不增版 | 已執行步數仍結算 |
| C++ 例外 | 回滾，結果記錄錯誤 | 不增版 | 已執行步數仍結算 |
| 有變更但 revision 已為 UINT64_MAX | 拒絕提交並回滾 | 保持最大值 | 已執行步數仍結算 |
| 事前窗口範圍／對齊不合法 | 不執行、不修改 | 不增版 | 0 |

「正常返回」沿用 legacy 解釋器的語義：Completed **不是合法停止已被證明**。
核心會把無效跳躍目標與明確 OUT_AREA 都表示成 stop=true；本原型無法區分。
測試以 KNOWN_GAP 明確重現無效跳躍仍提交前綴，這項缺口尚未修復。
核心對某些壞 token／未知條件採略過，正式錯誤分類仍須另訂。

## 程式位置

- prototypes/guest_trial_contract_ref.hpp：host-only 參考邊界，完整拷貝與回滾，成本另行結算。
- tests/test_guest_trial_contract.cpp：執行真實 simulate_spiral_program，並與舊 FullStateEnvelope 作反例對照。
- run_with_host_fault_for_test 只用於在真實 guest 指令後注入宿主刪除及例外，不是 guest 自己會刪除／丟 C++ 例外。
- 原正式 src/hamu_vm_core.hpp 未修改，沒有攔截任意直接呼叫。

## 驗證範圍

1. 舊版 ptr-only 不增版與預算耗盡可提交前綴的兩個反例。
2. TREE_ADD、工作寫入、游標變更、診斷式 no-op 的提交／增版。
3. 真實 guest 步數耗盡、樹容量與 INSERT 容量失敗，以及版本溢位的回滾。
4. 重試再次付費；失敗的讀取軌跡只保留於 Result，guest 狀態恢復。
5. 受控的一位元錯答先提交；教師供給候選 ID 後，guest TREE_ACTION 寫入錯答 mask。
6. 後續回饋中斷不污染先前錯答記憶；錯答 mask 可隨既有 new_his/copy_hamu 機制繼承。
7. 宿主注入例外恢復 generation、工作記憶與交易內 HP 變更，保留既有有效 handle。

本輪不測自主候選選擇、完整題庫學習效率、未提交 handle 封裝、持久化斷電安全或大型樹效能。

## 重現

Ubuntu / g++，由 experiments/hamu_vm 執行：

```sh
make guest-trial-contract-test
# 新契約與六個相關基準／回歸測試：
bash scripts/verify_guest_trial_contract.sh
```

腳本可接受外部輸出目錄作為第一個參數；每個測試保存 build.log 與 run.log。
採 C++17、O0、AddressSanitizer + UndefinedBehaviorSanitizer；ASAN_OPTIONS=detect_leaks=0。
這是相關的七個測試程式，不等於完整歷史測試集。

## 下一輪

先由 GPT 與作者審查 D-003、D-005、D-006。接著為核心增加可區分的停止原因，
讓無效跳躍測試從「已知缺口」改為「拒絕提交」，再談正式執行入口與差分優化。
