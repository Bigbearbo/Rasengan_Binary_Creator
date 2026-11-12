# 研究現況與下一步

更新：2026-11-12。整理與後續研究設計：**ChatGPT Pro**。本次查核基底為 main `9118abf4e895204588f7c5aa1bfc2615d0ab52b8`；成果分別位於下列 PR，不能假設 main 已經包含它們。新工作開始時重新查核相關 ref。

U 是使用者構想與方向；F 是指定版本的原始碼／資料；T 是實際執行結果，需註明執行者；A 是模型分析與未驗設計。使用者提出混合教學方向，Codex 執行 P031–P033，Pro 負責本次獨立審查、解析器修復與下一輪設計。這些歸屬分開記錄。

## 固定證據與完成狀態

| 研究線 | 固定版本與來源 | 已完成 | 尚未完成或適用限制 |
|---|---|---|---|
| P031 共用題庫 | [PR #5](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/5)；[cee9fb7 題庫入口](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/cee9fb7c331f23d9b7495f7240cc45060c19838d/experiments/spiral_teaching/math_benchmark/README.md) | 1,342題、15 profiles、288語義群、兩路相同raw 0/1介面；Codex驗收17/17，Pro亦獨立重跑17/17 | 真VM解題、新NN訓練、多類數學學習比較；預設資料分割不等於啟蒙課程 |
| P032 容量與後期混教 | [PR #6](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/6)；[f003980 實驗入口](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/f003980f719f84b366cda13601091ecf8c256d51/experiments/spiral_neural/20261112_p032/README.md) | Codex完成24條Neg分支及完整重播；加寬／改比例未穩定修復未教題 | 不代表容量永遠無關；這一批測的是暖身後混教 |
| P033 覆蓋、從頭混教、續訓控制 | [PR #7](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/7)；[e217bd0 實驗入口](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/e217bd0fd6cfe654062c3615ee2aa73a36d1ca71/experiments/spiral_neural/20261112_p033/README.md) | Codex完成D、A、3A：30條主／補充時序試驗；另12條Echo-only控制；完整重播 | V1/V2算符—資料搭配、表示／attention、整串輸出、更大位寬、新算符、升階儀式均未跑 |
| Pro 獨立審查與修復 | [Pro 證據與重跑入口](../../experiments/spiral_neural/20261112_pro_review/README.md) | P032唯讀36 checkpoint／480題／4,320探測；P031分割審查；解析器乾淨副本75/75及demo驗證 | 沒有新神經訓練；不能把Codex的P033訓練歸為Pro訓練 |
| 共用記憶與調度 | [原有MVP計畫](CODEX_MULTI_AGENT_MEMORY_PLAN_20261112.md) | 規格已公開；P032/P033各有Codex實際NVIDIA審查紀錄 | 本次已fetch的origin分支未見dispatcher／記憶MVP程式；不能推定使用者Windows本機未實作 |

P031題庫沒有用於P032訓練。NVIDIA單次呼叫成功不等於共用記憶系統完成。既有VM線應以[停止原因分支44d23b9](https://github.com/Bigbearbo/Rasengan_Binary_Creator/tree/44d23b934dbea141e436c24e52b60a500d09e162/experiments/hamu_vm)為本次已讀參考，不能只看較舊PR #2；Pro本輪沒有重跑VM測試。

## P033 對判斷的更新

[更新] 混教已實測能保留已教Echo；T1從頭混教與T0B後期混教均36/36，分段T0僅1/36；T1未教val+test為0/24。

[取代] 「從第一課混教尚未實跑，應先做這項」的舊工作狀態。

[原因] PR #7固定模型、精確樣本多重集合與各算符值流，只改時序，已完成對照。

[狀態] 本批結果信心高；沒有支持「必須第一堂混教」的獨特優勢，也沒有通用copy/flip成功證據。

[更新] 補齊二位元pair覆蓋未穩定修復泛化，C0 test為1/6、C1為0/6。

[取代] 把補pair覆蓋列為首要未測解法。

[原因] P033-A已實跑；資料缺口存在不等於它是唯一失敗原因。

[狀態] 對本批觀測信心高；內部機制仍是待驗假說。

[更新] 相同暖身後，Echo-only再教3,000題保留原test 12/12，Neg70只保留1/12。

[取代] 「普通續訓是否同樣退步」完全未測的狀態。

[原因] Codex另做12條控制；總題次相同，但Echo曝光為3,000對900。

[狀態] 支持本批多任務課程有額外干擾；不能排除曝光量、optimizer歷史及資源分配的差異。

## 下一步入口

[Pro 後續研究設計](PRO_RESEARCH_DESIGN_20261112.md)：先用E900補等Echo曝光控制，再做近等參數MLP／小型可學位置attention比較。這是A，尚未執行。保存來源、凍結預算與判準後，才交由Codex實作／驗證；不重做已完成的P033當作新發現。

P031啟蒙課程應另立教學manifest，讓最初0／1都有教學例，保存跨階曝光台帳；不要重寫既有benchmark分割。共用記憶工程沿用既有計畫，先盤點本機，再驗收一條「讀來源→候選審查→驗證→保存→重啟找回」流程；這份現況頁本身不是dispatcher實作。

歷史規格、失敗結果與checkpoint保持原貌。即時進度以此入口及固定證據為準，不能把下游計畫文件的舊「下一步」當成尚未完成的證據。
