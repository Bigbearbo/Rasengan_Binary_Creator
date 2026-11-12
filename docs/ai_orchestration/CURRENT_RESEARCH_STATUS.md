# 研究現況與下一步

更新：2026-11-13。整理與後續研究設計：**ChatGPT Pro**。歷史 main 查核基底為 `9118abf4e895204588f7c5aa1bfc2615d0ab52b8`；2026-11-13 通知設計接在 Codex P034 `5e6a25c8bb809f8130b60c257280aa72225a5f89` 後。成果分別位於下列 PR／分支，不能假設 main 已經包含它們。新工作開始時重新查核相關 ref。

U 是使用者構想與方向；F 是指定版本的原始碼／資料；T 是實際執行結果，需註明執行者；A 是模型分析與未驗設計。使用者提出混合教學方向，Codex 執行 P031–P033，Pro 負責本次獨立審查、解析器修復與下一輪設計。這些歸屬分開記錄。

2026-11-12 Codex 接續更新：依 PR #8 head `adca797c1afa98ed754ff616f73b691ab2925002` 的 Pro 事前設計完成 P034。下列新增 T 為 Codex／受指派 agent 的實作、訓練與獨立驗收；保留 Pro 原始設計及先前審查歸屬。P034 是接在 PR #8 後的獨立結果變更，不能假定 main 已包含。

2026-11-13 Pro 接續更新：依使用者的三份通知、局部回覆及尾兩碼控制構想，新增 [UR1 有位置的升階通知設計](PRO_UPGRADE_NOTICE_DESIGN_20261113.md)與獨立 codec。這是新 profile 的 A 設計和有界程式 T，不是神經升階訓練；P034 完成狀態保留。PR #8 較後的 [Pro 小網路／成長審查](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/4e2ded91166a4fd9348dccf8fc71ddf01e991645/docs/ai_orchestration/PRO_SLE_SMALL_NETWORK_REVIEW_20261112.md)另有固定入口，不能因本分支接在 P034 後就視為不存在。

## 固定證據與完成狀態

| 研究線 | 固定版本與來源 | 已完成 | 尚未完成或適用限制 |
|---|---|---|---|
| P031 共用題庫 | [PR #5](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/5)；[cee9fb7 題庫入口](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/cee9fb7c331f23d9b7495f7240cc45060c19838d/experiments/spiral_teaching/math_benchmark/README.md) | 1,342題、15 profiles、288語義群、兩路相同raw 0/1介面；Codex驗收17/17，Pro亦獨立重跑17/17 | 真VM解題、新NN訓練、多類數學學習比較；預設資料分割不等於啟蒙課程 |
| P032 容量與後期混教 | [PR #6](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/6)；[f003980 實驗入口](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/f003980f719f84b366cda13601091ecf8c256d51/experiments/spiral_neural/20261112_p032/README.md) | Codex完成24條Neg分支及完整重播；加寬／改比例未穩定修復未教題 | 不代表容量永遠無關；這一批測的是暖身後混教 |
| P033 覆蓋、從頭混教、續訓控制 | [PR #7](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/7)；[e217bd0 實驗入口](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/e217bd0fd6cfe654062c3615ee2aa73a36d1ca71/experiments/spiral_neural/20261112_p033/README.md) | Codex完成D、A、3A：30條主／補充時序試驗；另12條Echo-only控制；完整重播 | 本列僅記P033；表示／attention的一個配置已於P034完成，V1/V2、整串輸出、更大位寬、新算符、神經升階儀式仍未跑 |
| P034 等曝光與表示控制 | [實驗入口](../../experiments/spiral_neural/20261112_p034/README.md)；[凍結規格](../../experiments/spiral_neural/20261112_p034/protocol.json) | Codex完成12條E900及6條B1，完整重播與獨立驗收；E900 test 12/12，B1已教27/72、val+test 1/24，強判準0/6 | B0／Neg70／E3000為核對後引用歷史控制；不是等MAC、新盲測或所有attention的否證 |
| Pro 獨立審查與修復 | [Pro 證據與重跑入口](../../experiments/spiral_neural/20261112_pro_review/README.md) | P032唯讀36 checkpoint／480題／4,320探測；P031分割審查；解析器乾淨副本75/75及demo驗證 | 沒有新神經訓練；不能把Codex的P033訓練歸為Pro訓練 |
| Pro 有位置升階通知 UR1 | [設計](PRO_UPGRADE_NOTICE_DESIGN_20261113.md)；[codec／結果入口](../../experiments/spiral_neural/20261113_pro_upgrade_notice/README.md) | 新 profile 的局部確認、三份一次提交、重播與錯誤拒絕之有界程式驗證；實際命令與結果見入口 | 固定控制根 c3，八個 fixture 位置；無 NN 訓練、根擴張或任意版本同步，不能把 ACK 成功當成語義升階 |
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

## P034 對判斷的更新（Codex 實測 T）

[更新] 等900次Echo曝光、原始值流及暖身完整狀態下，新E900保留原Echo test 12/12，配對歷史Neg70為1/12；歷史E3000為12/12。E900每學生4500次target更新，Neg70為15000次；原Neg空槽完全不更新Adam、不消耗RNG。

[原因與限制] 更直接支持插入Neg更新的總效果；不把Neg語義、共享參數競爭及optimizer年齡單獨判為原因。E900不是等更新數或等MAC對照。暖身已錯的6筆val未修復，不能稱為本輪遺忘。

[更新] 2596參數B1 causal attention依事前配置跑完G0/G1各三seed、每學生3000題。已教27/72、val0/12、test1/12；六學生強判準0/6。歷史2595參數B0已教72/72、val+test0/24，來源／課程及96筆輸出已唯讀重算核對，沒有冒稱B0重訓。

[原因與限制] B1連已教題亦未學穩，此配置未通過；其矩陣MAC約B0的15.333倍，近等參數不等於等計算。STOP全對只證明固定長度停止。不能外推所有attention或SLE不可學；原三位元域已曝光，不稱新盲測。

[證據] [P034完整結果與限制](../../experiments/spiral_neural/20261112_p034/P034-等曝光與近等參數表示實測結果-2026-11-12.md)、入口中的兩份公開證據封存及可攜重現流程。新訓練與完整重播逐target狀態一致；獨立agent另核對來源、課程、工程梯度／因果性、checkpoint及實際生成。NVIDIA實際一次候選審查因截斷及錯誤主張未通過，不以模型意見代替本機驗收。

## 下一步入口

使用者目前要求的通知方案已另存 [UR1](PRO_UPGRADE_NOTICE_DESIGN_20261113.md)。若要進入學習實驗，先凍結新 profile／課程與足夠 context、生成上限及成本預算，再分開驗收通知配對、實際作用位置、升階後普通題與舊能力保留。既有 L16／部分 runner 的八步生成上限放不下最短通知確認；本次不擴訓已失敗的 P034 B1。

[Pro 後續研究設計](PRO_RESEARCH_DESIGN_20261112.md) 的E900及一個近等參數attention配置已完成，見P034；不再把它們列為尚未執行，也不重跑P033當新發現。依事前停止條件，不直接擴大失敗的B1或追加seed／訓練。若繼續，先以既有證據分析已教題擬合、優化穩定性與prefix行為；下一個單一變因、預算與判準須另立事前規格。V1/V2、4/5bit新holdout、等MAC對照、新算符、神經翻譯及真VM仍未執行。

P031啟蒙課程應另立教學manifest，讓最初0／1都有教學例，保存跨階曝光台帳；不要重寫既有benchmark分割。共用記憶工程沿用既有計畫，先盤點本機，再驗收一條「讀來源→候選審查→驗證→保存→重啟找回」流程；這份現況頁本身不是dispatcher實作。

歷史規格、失敗結果與checkpoint保持原貌。即時進度以此入口及固定證據為準，不能把下游計畫文件的舊「下一步」當成尚未完成的證據。

