# Pro／Codex 當前研究交接

更新：2026-11-13（Asia/Taipei）。使用者指定兩邊輪流研究。本頁只保留一張當前工作卡；完整研究完成狀態仍在 [CURRENT_RESEARCH_STATUS.md](CURRENT_RESEARCH_STATUS.md)。這是手動接棒，不代表任何桌面程序已被自動啟動。

## 當前工作卡

| 欄位 | 本輪內容 |
|---|---|
| 本輪已完成 | UR1 第一批神經通知：已見地址×寬度的保留組合 |
| 本輪 Owner | ChatGPT Pro，已完成審核、正式實驗與獨立驗收 |
| 下一棒 | Codex，待接棒；沒有自動啟動任何本機程序 |
| 狀態 | 先審核本輪負結果，再另凍結一項target更新次序診斷 |
| 原來源基底 | `a6f4a0943d63a6cba1763f5de095d40aba893bfa`，Pro UR1；含 Codex P035 `a309f2fc3e23255327fcab35745c27012d15ed4f` |
| 正式前固定提交 | `0b6de1d24481c2886833e412d173645fca98609c` |
| Manifest SHA256 | `d74dedb0627d79a8c41057a1625a3e83ab3c5b2edfbb675fccd902e94929a7b0` |
| 本輪成果分支 | `pro/notice-learning-20261113`，見[PR #12](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/12)；接棒先refresh此PR head，不假設main已包含 |
| 固定實測 | 三seed各128epochs／27,136更新＋完整重播；已教7/12、5/12、5/12；保留皆0/6 |
| 主要診斷 | 37個最後失敗有35個首錯在地址；已教未學穩，不能只歸為未教搭配泛化失敗 |
| 結果入口 | [Pro 結果與判斷](PRO_NOTICE_LEARNING_RESULTS_20261113.md)、[完整可攜證據](../../experiments/spiral_neural/20261113_pro_notice_learning/README.md) |
| 下一個唯一變因 | 每題答案targets連續更新，對比每epoch同一批212個target-prefix配對全部洗牌 |
| 下一輪寫入範圍 | Codex另開分支及新實驗目錄，保留Pro固定來源／原結果；領取時記起始head與新事前規格 |
| 導航整合 | 本輪由Pro整合現況與索引；Codex新增證據後回交，避免同時覆寫總覽 |
| 暫不追加 | 原配置epochs／seed／容量；普通數學題、有無通知效果、根升階、k2/k3、物理擴網 |

## 已完成來源與最新可見範圍

本輪已重新查核 GitHub PR、全部遠端分支並 fetch。當時最新可見的 Codex 公開成果仍是 [P035／PR #10](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/10)，最新 Pro 成果是 [UR1／PR #11](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/11)。沒有據此推定使用者本機尚未提交的工作不存在；若新來源出現，先核對增量再接入，不能把未讀的本機工作冒稱已審查。

P035 的正式12學生已完成；本輪另做來源／公開包／預算／曝光與部分checkpoint的有界唯讀核對，沒有重跑完整訓練。UR1 原codec 17項測試是上一輪成果，不計為本次新神經學生。Pro本輪新增3個神經學生與3條完整重播；獨立驗收18個checkpoint的324個完整回覆一致，0額外訓練更新。

## Codex 接棒的具體範圍

先讀本輪報告、完整失敗例與固定六點曲線；seed303在epoch32曾有1/6保留正確，最後回到0，不能挑中途checkpoint當成功。本輪原序對照已執行，後續只重用其固定證據，不稱為新的重訓。

建議候選保持相同12題、每epoch相同212個`(Q + 真答案前綴, target)`多重集合、每寬度68/68/76 targets及12個STOP，僅洗牌這212個target的出現次序。這些真答案前綴原本即在教師強制輸入，不是新增教師資訊；保留6題不得混入。從各seed原始`initial-state.npz`的完整初始狀態起跑，不能接final繼續訓練；模型、Adam、L80/H64、128epochs、27,136更新與training dense MAC都不變。

新target-stream、RNG、來源與三seed課序要先凍結提交，再正式執行。主要診斷是最後已教整串／地址擬合和固定checkpoint的穩定性，保留題仍完整報告；這六題已被查看，稱為診斷對照而非全新盲測。推論與牆鐘成本另計，不能把同training MAC說成所有成本相等。先把具體新判準寫清楚，保留全部seed及完整重播；不看分數補訓。

此候選是Pro的A、中低信心：相關targets集中更新可能影響擬合，但35/37地址首錯並未證明病因是更新順序。若Codex審核找到更直接的程式問題，先給可重現反例；若需換研究變因，明記原因並另凍結，不能把舊課程悄悄改成新實驗。

## 回交規則

正式前的固定提交保存規格、來源與manifest；正式完成後另提交結果、完整失敗例、checkpoint、重播判定、實際成本與限制。回交時記下已存在的固定提交／manifest SHA，不預填尚未生成的本頁自身 commit。下一位先讀固定結果，再決定唯一下一變因；不得因保留題低分擅自續訓、改分割或追加seed。

接棒者領取後在新分支記 owner、起始 head、寫入範圍與事前規格，再開始正式新實驗。遇到新提交先核對是否已有人執行同一工作；一般 Codex 寫新實驗證據，Pro 接回後統一整合總覽，減少互相覆寫。
