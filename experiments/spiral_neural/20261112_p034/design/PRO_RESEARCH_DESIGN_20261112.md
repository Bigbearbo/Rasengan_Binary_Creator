# Pro：P033 後續研究設計

作者／審查歸屬：**ChatGPT Pro**。日期：2026-11-12。狀態：**A，事前候選設計，尚未實作或訓練**；可作下一輪P034的工作規格，編號以執行者凍結manifest為準。這是Pro建議，不倒填為使用者原始構想。

先讀[現況](CURRENT_RESEARCH_STATUS.md)、[Pro獨立證據](../../experiments/spiral_neural/20261112_pro_review/README.md)，以及Codex [PR #7固定報告](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/e217bd0fd6cfe654062c3615ee2aa73a36d1ca71/experiments/spiral_neural/20261112_p033/P033-覆蓋與從頭混教實測結果-2026-11-12.md)。P033已跑出結果；本設計建立在結果上。

## 1. 要回答的問題

混教已保住已教Echo，未教組合仍失敗；全pair覆蓋也未穩定修復。下一輪要分辨「插入Neg更新的總效果」與「目前表示方式能否支撐可泛化的copy/flip」，而不是同時更換教材、容量、語法與算符。

H1：在相同Echo曝光下，插入Neg訓練仍會使原本能答的未教Echo退步。信心中；P033的Echo-only控制支持這個方向，但其Echo曝光量不同。

H2：在相近參數量、相同原生01輸入與教學資料下，可學位置／attention架構比目前MLP更容易保留未教組合。信心中低；這是可驗證候選，沒有實跑證據。若成功，首先只支持整個架構組合，不能直接把因果歸給attention單一元件。

既有三位元域已多次查看，下一輪在此域只能稱機制對照，不能稱新盲測。Pro先前P032診斷與Codex P033-D使用同一批模型，分母及指標不同，不合併當成更多獨立樣本。

## 2. E900：等 Echo 曝光控制

使用PR #7中S0/C0/S1/C1 × seed101/202/303的12份`warm-3` checkpoint。完整載入權重、Adam一二階動量、birth／step及RNG。先核對來源SHA，不在原封存內產生輸出。

| 組別 | 暖身後課程 | 題次／target更新 | 本輪角色 |
|---|---|---:|---|
| E900 | 只執行配對Neg70課程中那900次Echo，順序和值完全相同 | 900／4,500 | 新增12條短控制 |
| E900+N2100 | 原Neg70課程，900 Echo＋2,100 Neg | 3,000／15,000 | 沿用固定封存；只有來源／runner驗證不符才另立重現 |
| E3000 | P033後加的Echo-only 3,000題 | 3,000／15,000 | 已完成的等總題次參照 |

E900從原課程直接篩出Echo值流；不要重新抽樣900題。若沿用3,000個外部時槽，Neg槽完全不呼叫更新器、不增加step、不衰減moment、不消耗RNG。**Adam的零梯度step不等於沒有更新。** 空槽只記錄外部題次；計算量也不能把它算成已執行一題。

先驗收E900 trace與原Neg70的Echo子序列逐項相等、初始完整狀態相等、每個train值150次、剛好4,500個target更新。從訓練值與已封存oracle取得教師標籤；評估不更新模型。每100次Echo與最後一次記錄訓練／val／test，另保存起點、終點及完整重播核對。

主要結果是12個配對Echo test的保留／失去，逐split、seed回報；val要先標明暖身時已錯的題，不能把原本不會的算成遺忘。同時報全題、每位、首錯位、正確前綴下的logits及STOP。

若E900保留、Neg70失去，可更有力支持「插入Neg更新」的總干擾效果；仍不能單獨拆成Neg語義、共享參數競爭或optimizer年齡。若E900也失去，先檢查同Echo曝光的暫態曲線與來源，不將差異全歸Neg。**這是等Echo曝光對照，並非等更新數／等MAC對照。** 不必為補齊計算量而發明中性算符或偷偷加入新資料。

## 3. B0／B1：近等參數的表示對照

先固定P033的G0=S0、G1=C1，原生op2/data3無END、L16、T1從頭混合、seed101/202/303。每學生3,000題，Echo／Neg各1,500，每(op,value)250次，15,000個target更新；沿用公開`multiset_lessons`產生完全相同的值流與時序，先寫出hash。

B0是原H72 MLP，2,595參數。B1是一層、單頭、d16的causal self-attention，兩個pre-LayerNorm、residual、ReLU FFN寬33、dropout=0，沒有額外final LayerNorm。以最後可見位置的輸出頭預測下一個0／1／STOP。

| B1 元件 | 規格 | 參數 |
|---|---|---:|
| 二進位embedding | 2 × 16 | 32 |
| 可學絕對位置embedding | 16 × 16 | 256 |
| Attention投影 | Q、K、V、output各16→16，均含bias | 1,088 |
| FFN | 16→33→16，含bias | 1,105 |
| LayerNorm | 兩個，各16個scale及bias | 64 |
| 輸出頭 | 16→3，含bias | 51 |
| 合計 | 與MLP相差1參數，約0.039% | **2,596** |

學生只收到原本的`Q + 目前答案前綴`位元序列。教師強制時的前綴、自由生成時的前綴依原基線規則；不新增BOS、profile、Q／答案分界、算符分類、資料位對齊或oracle特徵。padding／causal mask只表示可見位置，STOP仍由模型輸出，不由教師依長度截成「正確」。不要把parser或固定copy／flip公式藏進學生。

跨架構只能使用配對seed與明確初始化規則，不能聲稱權重相同。B0沿用原初始化；B1事前固定embedding與各投影初始化、LayerNorm初值、Adam／學習率／梯度裁剪及數值精度，寫入manifest；選擇只能依工程穩定性與訓練資料，不能根據已查看holdout分數挑配置。若多次修改，全部列為開發試驗，另凍結最終比較。

主比較6個配對（兩split × 三seed）。新增B1六條；若新runner／套件會改動B0行為，先重現B0六條並驗與P033-T1逐題結果及完整狀態一致。既有封存能直接使用時，明列為引用歷史控制，不冒稱這輪重跑。新增網路要有小型數值梯度檢查、causal遮罩無未來token影響、checkpoint還原／重播與標籤不進自由推論的實際驗收；這些是新學習器必要工程門檻。

### 判準與成本

所有學生跑完固定預算，不因holdout低分加訓或挑seed。主要表同時列每seed的已教Echo／Neg、val／test逐題全對率、首次錯誤、資訊位與STOP、teacher-forcing與free-run，不用混合八值總正確率掩蓋未教題。保留全部失敗輸出與曲線。

「穩定修復本批未教組合」的強判準是B1六個學生每人四個heldout（兩op × val/test）全對，且每人12個已教組合全對。若僅部分提升，照實報分子／分母與配對差異，不改成已學會通用規則；亦不把未達全對當成沒有任何改善。沒有跨seed、split的一致改善，就停止這條配置的擴張，分析失敗再另寫新計畫。

參數接近和題次相同不代表計算成本相同。分報實際參數、target更新、矩陣／attention MAC、softmax與normalization成本口徑、峰值記憶體或array bytes（名稱分清）、牆鐘時間。原MLP的dense MAC與attention不能直接共用未核對的公式。若B1有穩定改善，再另立等MAC實驗；不能事後挑一個最有利的成本終點。

## 4. 後續分流與停止條件

V1/V2（未見數值與未見算符—數值搭配）仍是獨立未完成項。B1若改善，下一步才凍結這項分流以及四／五資訊位的新holdout manifest；同時記錄每個語義值及每個(op,value)跨階是否曾出現。測試集不進訓練、不用測試正解調logit門檻。四／五位成功也須限定其profile與數學範圍。

B1若失敗，不能推論SLE不可學或所有attention無效；也不要連續增加H、層數與新算符直到碰巧成功。先檢查已教題能否達標、首錯與前綴依賴，將下一個單一變因另立事前方案。整串輸出與去前綴內容是不同歸納偏好，須獨立記錄，不混入這一批。

P031仍保留為共用教材與真NN／VM入口工程：另立啟蒙manifest，最初0和1都示教，當階沒有盲測就明說，升階不能把已見語義換碼後重新叫未見。這項建議不修改已封存題庫，更不是P032失敗原因。

## 5. 交付、歸屬與 NVIDIA

開跑前保存source commit／檔案hash、確切split、課程hash、初始化與完整optimizer設定、停止條件、成本公式及檢查版本。輸出到新目錄；不要改P030/P032/P033歷史checkpoint。完整trace、truth table、模型／Adam／RNG、失敗例與重播結果須能追溯。

執行者以Codex T記新訓練；本文件仍為ChatGPT Pro A。使用者混合教學構想保留U歸屬。Pro本輪只讀診斷、封存核對及parser修復的T在[證據入口](../../experiments/spiral_neural/20261112_pro_review/README.md)另列。

本次Pro環境`nvidia_status=skipped_unavailable`：沒有可用OpenRouter／NVIDIA工具或相應憑證環境變數，實際呼叫0次。這不否認Codex P033已有一次真API審查。執行新實驗時，若本機worker可用，派一項公開唯讀審查：檢查E900 no-op與Adam差異、B1的參數／成本公式、標籤可見性及反例。候選仍須程式驗證，不等待worker阻塞實驗，也不把模型意見當PASS。

