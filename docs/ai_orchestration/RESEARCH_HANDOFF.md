# Pro／Codex 當前研究交接

更新：2026-11-13（Asia/Taipei）。使用者指定兩邊輪流研究。本頁只保留一張當前工作卡；完整研究完成狀態仍在 [CURRENT_RESEARCH_STATUS.md](CURRENT_RESEARCH_STATUS.md)。這是手動接棒，不代表任何桌面程序已被自動啟動。

## 當前工作卡

| 欄位 | 本輪內容 |
|---|---|
| 任務 | UR1 第一批神經通知：已見地址×寬度的保留組合 |
| Owner | ChatGPT Pro |
| 下一棒 | Codex |
| 狀態 | 正式訓練前的規格／工程驗收；正式執行需先凍結提交 |
| 基底 | `a6f4a0943d63a6cba1763f5de095d40aba893bfa`，Pro UR1；含 Codex P035 `a309f2fc3e23255327fcab35745c27012d15ed4f` |
| 工作分支 | `pro/notice-learning-20261113` |
| 唯一神經問題 | 純01 MLP 能否學穩通知片段摘錄，並回答六個保留地址×寬度搭配？ |
| 規格 | [Pro 事前規格](PRO_NOTICE_LEARNING_PROTOCOL_20261113.md)，機器manifest與實驗目錄相互核對 |
| 寫入範圍 | `experiments/spiral_neural/20261113_pro_notice_learning/`、本輪 P035 唯讀審核新目錄、Pro 規格／報告與本交接卡 |
| 導航整合 | Pro 更新現況與索引；歷史實驗、來源凍結和checkpoint保持 |
| 固定預算 | L80/H64；三seed；每seed128epochs／27,136更新；完整重播另列 |
| 不在本輪 | 普通數學題適應、有無通知效果、根升階、k2/k3、位寬外推、物理擴網 |

## 已完成來源與最新可見範圍

本輪已重新查核 GitHub PR、全部遠端分支並 fetch。當時最新可見的 Codex 公開成果仍是 [P035／PR #10](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/10)，最新 Pro 成果是 [UR1／PR #11](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/11)。沒有據此推定使用者本機尚未提交的工作不存在；若新來源出現，先核對增量再接入，不能把未讀的本機工作冒稱已審查。

P035 的正式12學生已完成；本輪另做來源／公開包／預算／曝光與部分checkpoint的有界唯讀核對，沒有重跑完整訓練。UR1 原codec 17項測試是上一輪成果，不計為本次新神經學生。

## 回交規則

正式前的固定提交保存規格、來源與manifest；正式完成後另提交結果、完整失敗例、checkpoint、重播判定、實際成本與限制。回交時記下已存在的固定提交／manifest SHA，不預填尚未生成的本頁自身 commit。下一位先讀固定結果，再決定唯一下一變因；不得因保留題低分擅自續訓、改分割或追加seed。

接棒者領取後在新分支記 owner、起始 head、寫入範圍與事前規格，再開始正式新實驗。遇到新提交先核對是否已有人執行同一工作；一般 Codex 寫新實驗證據，Pro 接回後統一整合總覽，減少互相覆寫。
