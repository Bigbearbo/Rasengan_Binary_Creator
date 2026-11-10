# 研究決策紀錄

日期：2026-11-10，Asia/Taipei。狀態均為**暫定**，作者可依編號重議。
作者已允許 Codex 在有分岔時先選方向，並留下標記。以下不是對歷史設計的追溯改寫。

| 編號 | 本輪選擇 | 替代方案 | 理由及重議條件 |
|---|---|---|---|
| D-001 | 一次已準備好的 guest 執行為一筆交易；評分／回饋另一步 | 每條指令提交，或整題連評分一起提交 | 避免留下執行前綴，也不把教師評分和 guest 混為一談；若需要中途保存，重議交易粒度 |
| D-002 | 答錯不是執行失敗；正常輸出先提交，之後 guest 可寫錯答記憶 | 答錯撤銷全部狀態 | 保留學習所需的經驗；若錯答會造成不可接受副作用，改討論具體狀態，而非全盤撤銷 |
| D-003 | 嘗試的實際步數在交易外結算一次 HP，失敗不免單 | 回滾 HP 成本，或只收固定費用 | 沿用 executed_steps / unit_cost_per 的成本尺度；不含原有 status_ref 的基本費、答題獎懲與樹原生查找成本；需生態對照實驗再決定最終成本模型 |
| D-004 | 保留全狀態拷貝作為參考，行為站穩後再比較差分實作 | 直接寫差分日誌 | 簡化正確性對照；大型狀態效能需求出現時重議，不能宣稱本版已高效 |
| D-005 | guest revision 追蹤 memory、val_reg、HP 的交易內改變、各游標、程式窗口、canonical tree、generation、lineage；診斷／衍生快取不單獨增版 | 任一欄位都增版，或僅樹變更增版 | ptr-only 已證明是舊版遺漏；stop、written、read_seen、steps、查找計數視為診斷。交易外 HP 扣款不增 guest revision，因此此版本號不能當整個生物狀態的並行更新鎖 |
| D-006 | 第二輪新增 typed stop reason，參考交易只接受明確正常結束；無效跳躍／採用無效窗口回滾 | 用 stop=true 一律判失敗，或繼續接受任何核心返回 | 第一輪僅標 KNOWN_GAP；第二輪據此修正判斷。正常 OUT_AREA、SET_AREA(7)、WindowEnd 保留提交資格，不改 legacy stop bool 行為 |
| D-007 | 保留 legacy 的壞 token 略過、半 token 尾端與延後採用窗口語義 | 在核心全面採嚴格解碼／對齊或立即驗證所有窗口改變 | 本輪只增加原因分類，避免意外改 ABI；Reference 仍可事前嚴格驗證。若要嚴格解碼，應另立規格並建立相容性對照 |

## D-005 的範圍細節

- memory 包含執行前已裝載的程式與題目，準備工作在交易之前，不計入本次 guest 差異。
- revision 比較 ptr、secondary_ptr、output_ptr、val_ptr、pro_1、pro_2。
- segment_pages / segment_used 與 registry 的 generation / lineage 是 canonical 狀態；查找索引和 first-free cursor 是可重建衍生資料。
- 拒絕執行時恢復整份 Host 備份（含診斷），但 Result 另保留本次步數與讀取軌跡；不是把失敗嘗試假裝成沒發生。
- Host 履歷、題目計分、出生、參數變更、對外 I/O 不由此 guest API 執行，也沒有宣稱其成功變更偵測已涵蓋。
- 未提交引用不得對外發布；本原型沒有封住呼叫者直接讀 registry 的能力。generation 回滾造成暫時 handle 別名的問題仍待正式 API 處理。

## 結算責任

參考 Trial 自己結算一次成本。呼叫後不能再對同次嘗試呼叫 use_hp()，否則重複收費。
目前未接正式生態迴圈；正式整合時須移除相同路徑上既有的重複結算，並維持活體檢查與死亡規則。
測試中的 HOST 例外注入可撤銷交易內直接扣 HP；其後仍扣本次已實際執行的成本。這與舊版「所有 HP 都回滾」的原型有意不同。

## D-006／D-007 的第二輪解釋

- 正常窗口結束維持 `stop=false`，但記錄 `WindowEnd`；明確停止仍維持 `stop=true`。
- 停止原因是本次核心實際採用窗口的執行結果。SET_PTR2 修改的是待採用窗口，尚未採用時不把它當成當前窗口失敗；pending／immediate 切換真正採用無效窗口時記錄 `InvalidWindow`。
- `write_prob` 清空原因；活躍執行重新記錄原因。已停止的短路呼叫不抹除既有終止證據，若只留下 None／WindowEnd，則記為 AlreadyStopped。
- 原始核心的停止原因分類不等於強制交易。直接呼叫 simulate_spiral_program 仍可能留下前綴；本輪以參考邊界將錯誤原因轉為回滾。
- 壞 token 的略過仍可導致正常 WindowEnd；Completed 不代表通過嚴格解碼，亦不代表答案正確。
