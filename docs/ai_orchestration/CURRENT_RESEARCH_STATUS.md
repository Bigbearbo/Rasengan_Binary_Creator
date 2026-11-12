# 研究現況與下一步

更新：2026-11-13（Asia/Taipei）。本輪 **ChatGPT Pro／受指派本機agent** 已完成AE1正式神經訓練、指定重播與獨立驗收。基底為Pro PR16 `685c6f92d9e5a335a2f2a7193d9b501918d90b00`；事前公開凍結`beb6dd7d4ce78d4f79e61164f838aaa881eafcd5`，分支`pro/advanced-echo-learning-20261113`。開工查核main仍`a28d6fa582bf60bd051c78897f7aa900d863c6e7`；不假定串接PR已合併。歷史Codex／Pro成果維持各自歸屬。新工作開始時重新查核相關ref。

## 最新：AE1停止控制強、內容複製未學穩

[完整結果](PRO_ADVANCED_ECHO_RESULTS_20261113.md)、[公開證據／重現入口](../../experiments/spiral_neural/20261113_pro_ae1_learning/README.md)。三seed各201,840更新，最後已教294/750、242/750、279/750；N4測試整串68/240、62/240、67/240，STOP位置239/240、235/240、236/240。四r全對僅0/60、1/60、0/60；強判準0/3。三seed合計197/720整串、710/720停止，不能把停止高分當完整回音成功。

這次固定課時漸增不是達標後進階：首階一詞11/30、9/30、30/30；seed303已全對仍後來退化。phase4→5完整回音test115/540→56/540，逐題舊正確失去86、新得27；count與繼續更新的影響未單獨分離。固定五階碼、L80/H64／10,499參數、cap32，無擴網或通知轉移測試。

三primary和唯一指定seed101重播均完成；五phase端點與epoch統計完全重現。全部18checkpoint／19,980題離線評分，另468題獨立raw-array推論PASS；本輪共807,360optimizer、599,760另列推論forward、23,256,468,480denseMAC。四ZIP的66成員全部驗證，沒有只公開hash。

下一候選A（信心中）：另凍結只改學習率0.003→0.001的配對診斷，保留原初態、資料、target次序、phase與更新預算，舊臂直接沿用本批。達標才前進保留為教學政策比較，不能先宣判是解方；不要把本批加長、換seed或擴網後覆蓋原結果。已看過test再用屬診斷，新盲測另立payload。依使用者要求記錄先設計再實驗的耗時及返工；本輪凍結後科學規格變更0／正式訓練丟棄0，沒有對照所以不宣稱已證明更快。

## 既有研究沿革

U 是使用者構想與方向；F 是指定版本的原始碼／資料；T 是實際執行結果，需註明執行者；A 是模型分析與未驗設計。使用者提出混合教學方向，Codex 執行 P031–P033，Pro 負責本次獨立審查、解析器修復與下一輪設計。這些歸屬分開記錄。

2026-11-13 Codex 接續更新：P034已於[PR #9](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/9)完成；依PR #8更新至`4e2ded91166a4fd9348dccf8fc71ddf01e991645`的Pro第6節候選，P035亦已實作、凍結、實跑與獨立驗收。下列新增T歸Codex及受指派agent；Pro原獨立審查／候選歸屬保留。PR #8／#9及本次結果尚未合併，不假定main已包含。

2026-11-13 Pro 接續更新：依使用者的三份通知、局部回覆及尾兩碼控制構想，新增 [UR1 有位置的升階通知設計](PRO_UPGRADE_NOTICE_DESIGN_20261113.md)與獨立 codec。這是新 profile 的 A 設計和有界程式 T，沒有神經升階訓練。已讀並整合 Codex P035 的固定報告與成果，未重跑其訓練／稽核；P035 未包含這次通知儀式。本分支亦保留先前 Pro 小網路／成長審查及其實測歸屬。

2026-11-13 歷史接棒（Pro PR #12）：[P035有界唯讀審核](../../experiments/spiral_neural/20261113_pro_p035_review/README.md)沒有實質 finding；當時最新可見Codex成果是P035。[UR1神經通知原序實測](PRO_NOTICE_LEARNING_RESULTS_20261113.md)已先提交事前規格，再跑三個學生及全部重播。最後已教7/12、5/12、5/12，保留各0/6，原強判準0/3；37個失敗中35個首錯在地址。這是Pro神經T，不能只說未教組合泛化失敗；當時提出的target次序候選現已由下一段PR #13完成。

2026-11-13 上輪接棒：[Codex PR #13](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/13)已完成同資料／初態／模型／更新預算的target次序對照，最後已教11/12、12/12、11/12，合計34/36；保留整串與地址仍各0/18。新strong fit僅1/3，不能稱全seed穩定學會。[Pro本輪有界審核](../../experiments/spiral_neural/20261113_pro_echo_review/README.md)重算三個final共54題，結果吻合，scope內無finding；0訓練、0完整replay。

同輪[回音／八位元／UR1釐清](PRO_ECHO_AND_UR1_REVIEW_20261113.md)核對P027有限回音成功、P029固定1171參數逐步增加資料位寬，以及舊介面的`|`。UR1回覆是從Q固定offset8起的一段連續摘錄，不能寫成任意位置搜尋重組。[一次人工權重構造](../../experiments/spiral_neural/20261113_pro_echo_construction/README.md)以同類原生01 MLP固定八位元回音256/256全對，只證明表達能力，非學習或UR1成功。本輪兩項模型工作合計4221次forward、0optimizer；下一棒與未驗教材候選見[交接卡](RESEARCH_HANDOFF.md)。

2026-11-13 最新接棒：Codex [PR #15](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/15)完成P030六份舊checkpoint的[Echo行為與曝光診斷](../../experiments/spiral_neural/20261113_echo_copy_audit/RESULTS.md)：混教前各8/8、混教後7/8、6/8、7/8；有有限位元跟隨行為，不支持只重播受教完整答案，也未證明通用copy演算法。Pro已讀完整結果／交接，沒有重跑其960次主／獨審forward。

前輪使用者提出多詞回音後，Pro完成[AE1格式設計](PRO_ADVANCED_ECHO_DESIGN_20261113.md)及[codec檢查](../../experiments/spiral_neural/20261113_pro_advanced_echo/README.md)；當時0神經訓練的敘述屬該輪歷史。本輪正式學習已完成，見上方最新結果；原UR1地址多樣性候選仍保留，未執行。

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
| Pro UR1 神經通知 | [結果](PRO_NOTICE_LEARNING_RESULTS_20261113.md)；[事前規格](PRO_NOTICE_LEARNING_PROTOCOL_20261113.md)；[完整證據入口](../../experiments/spiral_neural/20261113_pro_notice_learning/README.md) | 三學生各128epochs／27,136更新＋完整重播；最後已教17/36、保留0/18；獨立18checkpoint／324完整回覆重算一致 | 固定10,499參數，只測合法k1通知ACK；已教未學穩，37錯中35地址先錯。無實際語義升階、物理擴網或三份相對一份收益證據 |
| Codex UR1 target次序 | [PR #13結果](../../experiments/spiral_neural/20261113_codex_target_order/RESULTS.md)；[固定來源／封存](../../experiments/spiral_neural/20261113_codex_target_order/README.md) | 同212target多重集合、三初態、模型及27136更新／seed；3新學生＋3完整replay；已教34/36、保留0/18；新strong fit1/3 | 已查看搭配診斷；最後2個cap耗盡、0overflow。已教改善不是搭配泛化或通知效益；Windows原序重現只作旁證／成本，不加為新條件 |
| Pro PR13接棒審核 | [有界實際核對](../../experiments/spiral_neural/20261113_pro_echo_review/README.md) | 10公開檔、5ZIP／118成員、三完整初態、384epoch；3final×18題＝54實際回覆與TF吻合；scope內無finding | 1917forward／19998144MAC，0訓練／0完整replay；未重做324題或未公開的大trace |
| Pro固定回音人工構造 | [程式／人工state／完整truth](../../experiments/spiral_neural/20261113_pro_echo_construction/README.md) | 原P030純01 L80/H64，9個active hidden；固定手工權重一次窮舉256題，全Q+STOP正確 | 2304forward／24035328MAC、0optimizer；非訓練成果、非UR1、非長度外推，不修改既有學生 |
| Codex Echo行為／曝光診斷 | [PR #15固定結果](../../experiments/spiral_neural/20261113_echo_copy_audit/RESULTS.md) | 六份P030舊state；主程序與獨審合計960forward／1920960MAC，0optimizer；混教前各8/8 | 已曝光固定三位元域；有限照抄行為不識別無界演算法，混教後退化機制未唯一確定；Pro本輪只讀未重跑 |
| Pro多詞回音AE1格式 | [新題型設計](PRO_ADVANCED_ECHO_DESIGN_20261113.md)；[codec／fixture](../../experiments/spiral_neural/20261113_pro_advanced_echo/README.md) | 使用者U已轉為具體格式與程式檢查；n5、1≤r≤N≤4，四詞prefix63 | 此列只記前輪格式T；正式神經T見新增結果列。010為獨立profile，未混舊Neg |
| Pro AE1正式學習 | [結果](PRO_ADVANCED_ECHO_RESULTS_20261113.md)；[事前規格／完整證據](../../experiments/spiral_neural/20261113_pro_ae1_learning/README.md) | 三學生＋seed101完整重播；已教815/2250，N4測試整串197/720、STOP710/720，強判準0/3；468題獨立重算PASS | 單課程、固定n5／模型；固定課時非達標進階；無SLE編碼對照、無通知效益或物理擴網證據 |
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

UR1原序、target次序及有界審核均已完成，最新UR1已教34/36、保留0/18。前輪[AE1設計](PRO_ADVANCED_ECHO_DESIGN_20261113.md)的正式課程亦已由本輪完成，不能再當pending。下一棒讀[AE1實測](PRO_ADVANCED_ECHO_RESULTS_20261113.md)及[交接卡](RESEARCH_HANDOFF.md)，再為單一變因的新對照凍結規格；既有失敗不續訓改寫。

普通題作用與有無通知適應成本需另立配對比較，不能把P035結果歸因於缺少通知。分開驗收確認回覆、實際作用位置、新階普通題及舊能力保留；分輸入／回覆角色記曝光。P034的L16和P035的最高L13、既有八步生成上限均放不下最短通知確認；UR1因此另設L80/H64和24步上限，不能沿用原小模型參數量。本次不追加既有失敗配置的訓練，也不把人工copy權重當成訓練學生。

[Pro 後續研究設計](PRO_RESEARCH_DESIGN_20261112.md)的E900及一個近等參數attention配置已於P034完成；[小網路與成長審查](PRO_SLE_SMALL_NETWORK_REVIEW_20261112.md)第6節候選已以P035具體化並完成。不要把這些當待跑或擴張失敗配置。若接續，先依固定證據區分輸入格式適應、prefix依賴與新語義干擾，下一個單一變因／預算／判準另立事前規格；不因本批分數追加seed、擴容或延長。

[小網路與成長審查](PRO_SLE_SMALL_NETWORK_REVIEW_20261112.md)保留P030局部遷移正面結果。P035完成其一個有限候選版本，控制共同答案文法與容量時序；最短native-output／全系統編碼成本、獨立V1/V2、4/5bit新域、儀式的實際語義作用、神經翻譯、新算符及真VM仍未完成；有限ACK實測已完成，結果如上。P035不改原生SLE NN／VM主線或既有benchmark分割。

P031啟蒙課程應另立教學manifest，讓最初0／1都有教學例，保存跨階曝光台帳；不要重寫既有benchmark分割。共用記憶工程沿用既有計畫，先盤點本機，再驗收一條「讀來源→候選審查→驗證→保存→重啟找回」流程；這份現況頁本身不是dispatcher實作。

歷史規格、失敗結果與checkpoint保持原貌。即時進度以此入口及固定證據為準，不能把下游計畫文件的舊「下一步」當成尚未完成的證據。
