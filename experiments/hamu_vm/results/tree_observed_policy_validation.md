# 個體政策狀態，2026-10-31 Asia/Taipei

來源：hamu_vm_observed_transient_20261031.zip；工作入口 version 13。

## 全部更動

src/tree_observed_vm.hpp：新增 policy_set／policy_export／policy_react 三個客體程式產生器。work+158 是個體可寫政策，+159 是宿主發布的最近初選執行失敗感測位；政策 export 至 output+28，+29 為最後提交位。react 只有遇到失敗才開啟 +158，其他情況保留原值。set 明確設定 +158 並清除 +159。

src/tree_observed_learner.hpp：TreeObservedTurn 增加 initially_invalid，保存改選之前的真實執行有效性。新增 run_tree_observed_policy_turn，驗證客體輸出的新鮮政策與提交，再呼叫原學習入口；成功返回一輪結果後發布失敗感測位，由客體執行反應。沒有直接在宿主讀政策工作位作決策。原 bool 開關入口不變。

tests/test_tree_observed_policy.cpp：從前輪固定題序測試延伸，新增反應政策與成本分類，驗證失敗後下一題生效、後代繼承、子代以客體指令獨立關閉、部分政策 export 不得啟動學習及清空舊答案。96 次全資料親代／後代路由，三政策兩種失敗片段。

Makefile：新增 tree-observed-policy-test ASan/UBSan 目標。

README.md；results/tree_observed_policy_output.txt、tree_observed_policy_regression.txt 及本紀錄。其他原始碼沒有修改。

## 本輪證據

新政策測試首次通過；補入中斷政策 export 測例後再通過，沒有測試失敗後修正正式程式。make tree-observed-policy-test、make -j2 tree-observed-transient-test tree-observed-learner-test 均 ASan/UBSan PASS。沒有改核心或 ISA，也未重跑 6000 隨機 VM、舊四候選／寬度回歸及一般全觀察成本基準。

| 失敗片段 | 策略 | 確認題次 | 六題有效／正確 | 學習 VM 總步數 | 觀察次數 |
| --- | --- | --- | --- | --- | --- |
| ZERO | 固定關閉 | 5 | 4／2 | 13624 | 17 |
| ZERO | 固定開啟 | 4 | 6／4 | 15745 | 10 |
| ZERO | 遇失敗開啟 | 4 | 5／3 | 12960 | 13 |
| COPY | 固定關閉 | 3 | 4／4 | 6277 | 12 |
| COPY | 固定開啟 | 3 | 6／4 | 11824 | 9 |
| COPY | 遇失敗開啟 | 3 | 5／4 | 9207 | 11 |

總步數包括 guest/request/recovery/fragment/policy 五欄；反應政策 export/react 成本分別 182 與 143 步。初始政策 set 程式在計量前執行、不計入學習成本；這是比較從既定初始狀態出發的學習，不是完整生命週期成本。確認後路由與最後 96 次驗證不計學習成本，六題作答覆蓋包含確認後路由。CSV recovery 欄位 0=固定關閉、1=固定開啟、2=遇失敗開啟。

失敗以宿主於前兩題把相同片段預算設成零注入，片段表不變；兩故障皆恰好兩次。反應政策第一題仍無恢復，感知初選失敗後，第二題才啟用。本輪沒有測牆鐘、HP、長期演化或政策最優性。

## 界線

政策可寫與可繼承已驗證；反應規則與 set 程式由研究者寫定，測試指定初始狀態，不代表倉鼠已自行設計規則或找到最優選項。宿主仍發布執行有效性事實，客體按規則改政策；沒有用標準答案或詞義標籤決定該政策。無效候選仍保留未知，唯一確認規則不變。

export 若中斷，包裝入口返回 nullopt、清空答案，且尚未開始學習。react 是學習完成後的獨立程式，不與整輪學習形成原子交易；若其執行中斷，學習結果仍已完成，政策更新可能延後。本測例給 react 足夠預算，不宣稱測過所有中斷點。work+158/159 為新入口的保留區，舊自訂工作布局需避開。

下一步可讓客體依資源訊號選擇是否承擔恢復費用，或測世代變異政策如何隨失敗頻率與報酬而變；目前沒有收益／HP 計費模型。
