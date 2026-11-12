# ChatGPT Pro：獨立研究審查、證據與修復

日期：2026-11-12。本目錄作者／審查歸屬：**ChatGPT Pro**。使用者要求把Pro研究設計與改動更新到Git；Codex的既有P031／P032／P033實驗保持原始歸屬。本包沒有新神經訓練，也沒有合併其他研究分支。

目前判斷見[研究現況](../../../docs/ai_orchestration/CURRENT_RESEARCH_STATUS.md)，未執行的新研究見[Pro後續設計](../../../docs/ai_orchestration/PRO_RESEARCH_DESIGN_20261112.md)。`evidence.zip`內的`historical-review-before-p033.md`保存PR #7發布前的Pro審查；其中「P033尚待實跑」已由新現況取代，不是現行工作指令。

## 歸屬與固定來源

U：使用者研究方向（含混合教學）；F：指定版本公開材料；T：實際執行；A：Pro分析／提案。所有新訓練成績來自Codex，以下明列Pro真正做過哪些核對。

| 來源 | 固定commit | Pro實際工作 |
|---|---|---|
| [P031／PR #5](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/5) | `cee9fb7c331f23d9b7495f7240cc45060c19838d` | 前輪獨立重跑17項工程驗收；枚舉題庫分割。本次為審查程式補上來源hash守門與拒絕覆寫，再執行枚舉 |
| [P032／PR #6](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/6) | `f003980f719f84b366cda13601091ecf8c256d51` | 前輪載入36 checkpoint、480題、4,320探測，驗參數／Adam／RNG與檔案未改；本次發布原始程式與證據 |
| [P033／PR #7](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/7) | `e217bd0fd6cfe654062c3615ee2aa73a36d1ca71` | 本輪從30份最終真值表重新評分480筆已存生成字串；交叉核對12份Echo-only聚合結果。沒有載checkpoint推論或重跑訓練 |
| parser／main | `9118abf4e895204588f7c5aa1bfc2615d0ab52b8` | 修正乾淨checkout缺fixture問題；全新副本75/75及demo實跑 |

## 1. P033 已更新研究判斷

`audit_p033.py`先驗五份公開來源SHA，再獨立檢查原始truth table的Q／target構造與生成全對數，對照各學生結果、`summary-table.json`及報告表格。30份表480筆全部吻合。Echo-only封存未提供逐題生成字串，該部分只交叉核對12份`result.json`／聚合結果及暖身檔案hash，不稱重新推論。

| 時序 | 已教Echo（兩組教材合計） | 未教val＋test（兩算符合計） |
|---|---:|---:|
| T0分段 | 1/36 | 7/24 |
| T1從頭混合 | 36/36 | 0/24 |
| T0B後期混合 | 36/36 | 1/24 |

這些分母是模型×題目評估，不是相互獨立的新題。T0較高的部分holdout總分不代表兩種技能都保留。補pair覆蓋的C0 test 1/6、C1 0/6，沒有穩定修復。Echo-only 3,000題後保留原Echo test 12/12，Neg70只1/12，但Echo曝光是3,000對900。

[更新] 下一步改為等Echo曝光控制與近等參數表示比較。

[取代] 再把從頭混教、補pair覆蓋或普通續訓控制列為尚未首次執行的主要工作。

[原因] Codex P033已實跑；Pro從已存答案重新計分確認報告數字。

[狀態] 本批結果信心高；表示瓶頸及干擾機制仍待新實驗，不能先宣稱attention一定有效。

## 2. Pro 的 P032 獨立診斷

前輪對36個保存模型完成480題與4,320單位元翻轉；24個Neg後checkpoint的自由生成與正確前綴預測均與原表一致。test的48筆模型×算符評估中，首錯在bit0有8筆、bit1有38筆，整題全對2筆。中位自由生成正確10/48，餵正確答案前綴後僅2/48；val相同位置為48/48。

48組合法中位反事實比較只改輸入中位，前綴對兩題均正確。logit差48/48朝應有方向移動，僅2/48改變輸出決策。模型對輸入位仍有功能性反應，但不足以跨過決策邊界；不能說它完全忽略Q，也不能把首錯全歸前綴級聯。

一般矩陣中`input_bit < output_bit`會刻意固定不一致前綴，資料以`prefix_consistent`標記，不能當合法教學題。上述48組對照沒有此問題。這些是回溯診斷，不是新盲測或訓練干預。Codex P033-D也用了相同來源模型，其概率差與val/test合計96題報法與此處不同，不相加製造樣本數。

## 3. P031 教學分割審查

17/17工程測試通過：1,342題、15 profiles、288語義群、6,966教師前綴；兩路raw輸入SHA相同。這是傳輸及codec驗收，未跑真正VM學生或新NN訓練。

| 初期階段 | train值 | val值 | test值 |
|---|---|---|---|
| 1資訊位Echo | 0 | 1 | 無 |
| 2資訊位Echo | 0,3 | 1,2 | 無 |
| 3資訊位Echo | 0,3,7 | 1,2,4 | 5,6 |
| 3資訊位Neg | 0,1,2,3,4,5,6 | 無 | 7 |

原README已揭露小集合不保證分割比例，這不是隱藏的split演算法缺陷。問題是若拿它直接啟蒙，只有0→0無法由資料區分Echo與常數零。建議另立教學manifest，在第一階示教0／1，明說當階沒有盲測；往更大值域預留新組合，並保存跨階語義與(op,value)曝光。原benchmark封存保持原樣。P031沒有被用於P032，不能用這張表回溯解釋P032的失敗。

## 4. 解析器可重跑修復

原main的75測例在乾淨checkout有19個缺檔錯誤；測試／demo讀取未提交的`spiral_dialogue_v03_run`。本次新增由原`scenario()`確定性產生的公開教師fixture，讓v0.4／v0.5／v0.6測試與demo讀取已提交fixtures。既有學生fixture及parser／packet／teaching演算法未變。

在只含追蹤檔案及新fixture的全新副本執行75/75 PASS；demo從不同cwd執行exit0，trace與學生狀態吻合原封存fixture，highwater=32、version=3。輸入hash未改，生成物只在暫存副本。demo原有`run_v06`輸出行為保留。[修復說明](../../spiral_parser/README.md)載明來源與用法。

## 5. 重跑

Python標準庫可跑兩個audit；`review_probe.py`另需NumPy。先取得指定PR分支／commit，勿把main裡尚無的路徑當缺失實驗。從repo根目錄建立獨立worktree，例如：

```sh
git fetch origin
git worktree add --detach ../pro-source-p031 cee9fb7c331f23d9b7495f7240cc45060c19838d
git worktree add --detach ../pro-source-p032 f003980f719f84b366cda13601091ecf8c256d51
git worktree add --detach ../pro-source-p033 e217bd0fd6cfe654062c3615ee2aa73a36d1ca71
python -B experiments/spiral_neural/20261112_pro_review/audit_bank.py --bank-code ../pro-source-p031/experiments/spiral_teaching/math_benchmark --out ../pro-p031-audit.json
python -B experiments/spiral_neural/20261112_pro_review/review_probe.py --p032-dir ../pro-source-p032/experiments/spiral_neural/20261112_p032 --out ../pro-p032-probe
python -B experiments/spiral_neural/20261112_pro_review/audit_p033.py --p033-dir ../pro-source-p033/experiments/spiral_neural/20261112_p033 --out ../pro-p033-audit
```

輸出位置必須未存在；若前次已跑，換新名稱。audit核對固定公開檔案，來源變更會拒絕執行，應先審查新版本再更新來源身份。原先P031工程驗收命令為該分支的`python -B run_checks.py --out <新目錄>`。parser原75測例命令在其README，demo應在新副本執行以保存舊輸出。

## 檔案與範圍

`summary.json`是本包摘要；`manifest.json`列來源、程式及封存各成員SHA；`evidence.zip`包含P032六份原始診斷JSON、P031分割／17項測試紀錄、P033重新計分的逐學生結果／來源hash、parser驗證及前輪歷史報告。沒有再打包上游checkpoint或私人材料。檔案雜湊驗證屬工程驗收，不代表學習成功。

本輪沒有修改既有CMake workflow或補根目錄`CMakeLists.txt`，GitHub既有build限制與Python實跑結果分開看。沒有VM實跑、模型新訓練、E900或B1實作，也沒有dispatcher／SQLite MVP實作。

NVIDIA：`task_id=PRO-RESEARCH-REVIEW-20261112`，`status=skipped_unavailable`，`model_id=null`，呼叫0次；當前環境沒有可用OpenRouter／NVIDIA工具或相應憑證環境變數。另以三個研究子任務做獨立來源審查與本地驗證。不能把Codex P033中的真實NVIDIA呼叫計到Pro本輪。
