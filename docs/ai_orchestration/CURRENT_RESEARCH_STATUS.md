# 研究現況與下一步

更新：2026-11-13。整理與後續研究設計：**ChatGPT Pro**；P034／P035實測及該部分結果更新：**Codex／受指派agent**。歷史 main 查核基底為 `9118abf4e895204588f7c5aa1bfc2615d0ab52b8`；本次通知分支已整合 P035 `a309f2fc3e23255327fcab35745c27012d15ed4f`。成果分別位於下列 PR／分支，不能假設 main 已經包含它們。新工作開始時重新查核相關 ref。

U 是使用者構想與方向；F 是指定版本的原始碼／資料；T 是實際執行結果，需註明執行者；A 是模型分析與未驗設計。使用者提出混合教學方向，Codex 執行 P031–P033，Pro 負責本次獨立審查、解析器修復與下一輪設計。這些歸屬分開記錄。

2026-11-13 Codex 接續更新：P034已於[PR #9](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/9)完成；依PR #8更新至`4e2ded91166a4fd9348dccf8fc71ddf01e991645`的Pro第6節候選，P035亦已實作、凍結、實跑與獨立驗收。下列新增T歸Codex及受指派agent；Pro原獨立審查／候選歸屬保留。PR #8／#9及本次結果尚未合併，不假定main已包含。

2026-11-13 Pro 接續更新：依使用者的三份通知、局部回覆及尾兩碼控制構想，新增 [UR1 有位置的升階通知設計](PRO_UPGRADE_NOTICE_DESIGN_20261113.md)與獨立 codec。這是新 profile 的 A 設計和有界程式 T，沒有神經升階訓練。已讀並整合 Codex P035 的固定報告與成果，未重跑其訓練／稽核；P035 未包含這次通知儀式。本分支亦保留先前 Pro 小網路／成長審查及其實測歸屬。

2026-11-13 Pro 輪流接棒：重新查核遠端後，最新可見 Codex 公開成果仍是 P035。已另做[有界唯讀審核](../../experiments/spiral_neural/20261113_pro_p035_review/README.md)，沒有實質 finding；核對746個公開ZIP項目、60個學生×階段預算，實際重算64題及4次grow副本，0次訓練更新。新的[UR1 神經通知實驗](PRO_NOTICE_LEARNING_PROTOCOL_20261113.md)已定義六個位置、12個已教／6個保留搭配，現為正式訓練前凍結階段。進度與下一棒以[當前交接卡](RESEARCH_HANDOFF.md)為準；尚未產生新神經成果。

## 固定證據與完成狀態

| 研究線 | 固定版本與來源 | 已完成 | 尚未完成或適用限制 |
|---|---|---|---|
| P031 共用題庫 | [PR #5](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/5)；[cee9fb7 題庫入口](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/cee9fb7c331f23d9b7495f7240cc45060c19838d/experiments/spiral_teaching/math_benchmark/README.md) | 1,342題、15 profiles、288語義群、兩路相同raw 0/1介面；Codex驗收17/17，Pro亦獨立重跑17/17 | 真VM解題、新NN訓練、多類數學學習比較；預設資料分割不等於啟蒙課程 |
| P032 容量與後期混教 | [PR #6](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/6)；[f003980 實驗入口](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/f003980f719f84b366cda13601091ecf8c256d51/experiments/spiral_neural/20261112_p032/README.md) | Codex完成24條Neg分支及完整重播；加寬／改比例未穩定修復未教題 | 不代表容量永遠無關；這一批測的是暖身後混教 |
| P033 覆蓋、從頭混教、續訓控制 | [PR #7](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/7)；[e217bd0 實驗入口](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/e217bd0fd6cfe654062c3615ee2aa73a36d1ca71/experiments/spiral_neural/20261112_p033/README.md) | Codex完成D、A、3A：30條主／補充時序試驗；另12條Echo-only控制；完整重播 | 本列僅記P033；一個attention配置已於P034、輸入編碼×容量時序已於P035完成。V1/V2獨立分流、整串輸出、更大位寬、新算符、神經升階儀式仍未跑 |
| P034 等曝光與表示控制 | [PR #9](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/9)；[固定入口](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/5e6a25c8bb809f8130b60c257280aa72225a5f89/experiments/spiral_neural/20261112_p034/README.md) | Codex完成12條E900與6條B1；E900 test12/12 vs歷史Neg701/12；B1已教27/72、heldout1/24、強判準0/6 | E900非等更新／MAC；B1單一配置失敗，非所有attention或SLE的否證；歷史控制未重訓 |
| P035 輸入編碼×容量時序 | [實測入口](../../experiments/spiral_neural/20261112_p035/README.md)；[事前規格](../../experiments/spiral_neural/20261112_p035/protocol.json) | Codex完成12新學生＋完整重播；最後已教144/144、heldout5/48；primary僅SF/202=3其餘2，interaction0/−1/0；獨立300checkpoint／2280實際輸出稽核 | 共用答案文法，只測input codec；未教運算元4/6已在教師答案出現；三配對seed／巢狀里程／舊域，非盲測或全系統編碼優勢 |
| Pro 獨立審查與修復 | [Pro 證據與重跑入口](../../experiments/spiral_neural/20261112_pro_review/README.md) | P032唯讀36 checkpoint／480題／4,320探測；P031分割審查；解析器乾淨副本75/75及demo驗證 | 沒有新神經訓練；不能把Codex的P033訓練歸為Pro訓練 |
| Pro 小網路／成長審查 | [核心假說審查](PRO_SLE_SMALL_NETWORK_REVIEW_20261112.md)；[可重播探測](../../experiments/spiral_neural/20261112_pro_growth_review/README.md) | 三checkpoint各40舊prefix擴網logit差0；同raw8/8，op2同義題未適應0/8；每次執行在三個副本合計六次除錯更新確認梯度通路 | 該次Pro探測沒有完整課程或編碼對照；其後P035已完成一個有限對照。合法零token不是padding，不能直接沿用scalar-zero保函數條件 |
| Pro 有位置升階通知 UR1 | [設計](PRO_UPGRADE_NOTICE_DESIGN_20261113.md)；[codec／結果入口](../../experiments/spiral_neural/20261113_pro_upgrade_notice/README.md) | 17/17程式測試；八個fixture位置、73個拒絕子案例；獨立340個單bit變異中334拒絕、6個合法改址 | 固定控制根c3；無NN訓練，根升階僅A候選；回覆配對不等於已學會新寬度，沒有完整傳輸防錯 |
| Pro P035 接棒審核 | [實際唯讀證據](../../experiments/spiral_neural/20261113_pro_p035_review/README.md) | 凍結來源9/9、公開檔案26/26、ZIP項目746/746、30課序、24曝光帳、60預算；64實際題與4 grow副本吻合 | 有界重算，0新學生／0訓練更新／0完整重播；不冒稱重跑Codex全部300 checkpoint |
| Pro UR1 神經通知 | [事前規格](PRO_NOTICE_LEARNING_PROTOCOL_20261113.md)；[實作入口](../../experiments/spiral_neural/20261113_pro_notice_learning/README.md) | 正式前教材、程式與預算工程驗收；需先將manifest提交Git再執行 | 正式訓練尚未開始；只測合法通知ACK摘錄與已見地址×寬度組合，不測實際升階作用或儀式收益 |
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

## P035 對判斷的更新（Codex 實測 T）

[更新] Pro的12學生候選已凍結為五階input-codec×容量時序篩查，正式實測台北2026-11-13完成。S/H各F/G×三seed，最後已教每人12/12，未教運算元val+test合計5/48；SF/SG/HF/HG分別3/12、2/12、0/12、0/12。主要累積里程0..4僅SF/202=3，其餘2，配對interaction0/−1/0，沒有本批SLE成長額外收益。

[原因與限制] 各codec同策略的state、ordinal教材、target與容量完全配對；兩側共用答案文法，H不是最短native-output對照。F先配置最終2073參數，G按共同序列成長；同training denseMAC上限讓G得到較多曝光，是容量時序政策的一部分。三seed及巢狀里程只能作描述。4/6沒有作訓練運算元，但Neg(1)/Neg(3)答案各出現250次，不稱各角色均未見。

[更新] op位寬變動前原Echo89/96，當前新碼入口0/96、該階末84/96；same-raw grow與改碼適應分開。加Neg時原先正確84筆保住76、失去8、另新答對1，Echo總77/96；邊際分數差不直接當遺忘量。

[證據] [P035完整結果](../../experiments/spiral_neural/20261112_p035/P035-輸入編碼與容量時序實測結果-2026-11-12.md)、公開state／truth／曲線及source-freeze。854022次新target另完整重播同數，12學生全部保留；獨立稽核854022紀錄、300完整checkpoint及2280實際生成／TF／logits。NVIDIA本輪真呼叫一次，無依據數字／p值主張經本機反例拒絕；沒有用候選意見當PASS。

## 下一步入口

使用者目前要求的通知方案已另存 [UR1](PRO_UPGRADE_NOTICE_DESIGN_20261113.md)。當前 Pro 接棒先執行[有限ACK學習事前規格](PRO_NOTICE_LEARNING_PROTOCOL_20261113.md)，檢查六個位置的局部回覆能否學穩；更後面的普通題作用與有無通知適應成本需依結果另立配對比較，不能把P035結果歸因於缺少通知。分開驗收確認回覆、實際作用位置、新階普通題及舊能力保留；分輸入／回覆角色記曝光。P034的L16和P035的最高L13、既有八步生成上限均放不下最短通知確認；本次因此另設L80/H64和24步上限，不能沿用原小模型參數量。本次不追加既有失敗配置的訓練。

[Pro 後續研究設計](PRO_RESEARCH_DESIGN_20261112.md)的E900及一個近等參數attention配置已於P034完成；[小網路與成長審查](PRO_SLE_SMALL_NETWORK_REVIEW_20261112.md)第6節候選已以P035具體化並完成。不要把這些當待跑或擴張失敗配置。若接續，先依固定證據區分輸入格式適應、prefix依賴與新語義干擾，下一個單一變因／預算／判準另立事前規格；不因本批分數追加seed、擴容或延長。

[小網路與成長審查](PRO_SLE_SMALL_NETWORK_REVIEW_20261112.md)保留P030局部遷移正面結果。P035完成其一個有限候選版本，控制共同答案文法與容量時序；最短native-output／全系統編碼成本、獨立V1/V2、4/5bit新域、儀式、神經翻譯、新算符及真VM仍未完成。P035不改原生SLE NN／VM主線或既有benchmark分割。

P031啟蒙課程應另立教學manifest，讓最初0／1都有教學例，保存跨階曝光台帳；不要重寫既有benchmark分割。共用記憶工程沿用既有計畫，先盤點本機，再驗收一條「讀來源→候選審查→驗證→保存→重啟找回」流程；這份現況頁本身不是dispatcher實作。

歷史規格、失敗結果與checkpoint保持原貌。即時進度以此入口及固定證據為準，不能把下游計畫文件的舊「下一步」當成尚未完成的證據。
