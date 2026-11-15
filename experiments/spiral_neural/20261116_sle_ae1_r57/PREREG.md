# R57 事前凍結｜合法 01 題角色配對，固定模型新題域

狀態：**PREREGISTERED — 0 R57 neural forwards / 0 optimizer updates**。Owner：獨立小型神經網路研究員。Parent：Draft PR #107，base commit `793920dab695dba9a8e1fe53010c65fd59cb3723`。只在新的研究分支寫入；不自動合併，也不覆蓋 Pro/Codex 或倉鼠 VM 工作。

唯一變因：**評估題域**。維持 R52、R55、R56 三組已完成訓練的原有 checkpoint 完全凍結，在尚未回答過的合法 SLE 39-bit *完整 Q 位元串* 上，將相同四個資料詞 `a,b,c,d` 各配成 r=1 與 r=2 一對，診斷答案角色與第二詞來源的轉換。此輪不增加訓練、不改輸入路由或解碼、不補 seed。題目數值0..29本身在歷史實驗已曝光：**這是新 exact-Q 的前瞻性測試，不是新數值域盲測**。

合法 profile：`SLE-AE1-n5-v1`，原生輸入 `01+010+bin3(r)+0+4*(bin5(v)+0)+111100` (39 bits)；`r ∈ {1,2}`，`a,c,d∈[0,29]`，低b層0..5，高b層24..29；預期真值 `r*(bin5(answer operand)+0)+S`。教師真值獨立計算、不可在自由生成時提供模型。Seed學生101/202/303；manifest RNG `default_rng(57011)`，拒絕與歷史1740個已知Q重複。每組48個運算元四元組，共96個獨立Q，平均分配高/低b；validation 16組=32Q，test 32組=64Q；歷史保留80Q只作曝光對照。合計96+80=176 Q ×3學生×3組模型=**1584** 次完整回答。所有輸入為合法原生01，STOP另作輸出類別S，不可只驗第一詞。

參數：R52=10465（10,457 backbone+8 static gate）；R55=10465（10,457 backbone+8 trainable slope；另8 frozen static gate buffers）；R56=10465（10,457 backbone+8 fitted static gate）。本輪更新數0，訓練MAC0；dense forward每次10,920 MAC，推論forward數待實測，反向成本0。

事前聯合 gate（全部同時成立才PASS）：(1) 96條不與歷史Q重複且48個角色配對合法；(2) R55新test整串含S正確數 ≥ R52+8（192次回答）；(3) R56新test整串含S正確數 ≥ R52+8；(4) R55每seed相對R52最多少4題；(5) R56每seed相對R52最多少4題；(6) PyTorch與獨立NumPy各1584條完整重播一致、sample logits差小於1e-5。不在看test後修改門檻。另完整報每seed、r1/r2同組都對、b高低組、gain/loss、正確STOP與歷史保留。

固定檔案 SHA256：manifest `fb08b8da670c8837fd99ddc54011268f18e00e820dc6b941bfd7200cedaaa420`；Python runner `fcf5383423c9d586b81606ce0f17217f757a54b1d44f73b9725d2bad758838d3`；完整 prereg JSON `5c5423c442007d06d9a88c51bb2a03a7cf2bbbbb6174755c8152ee020c0b26d3`。來源精確檔案SHA另在本輪凍結JSON，將與程式、原始模型封於最終可攜ZIP。每次執行先比對來源SHA。所有失敗同樣保存。

U：作者要求SLE 01 學生真實訓練、輸出、泛化與獨立分工。F：PR #107及 R56 可重播 ZIP 的 R50/R52/R55/R56 原始權重及程式。T：至凍結時僅建立且靜態檢查manifest與SHA，**沒有模型推論**。A：新角色配對能揭露來源權重的遷移能力，是否有優勢尚未知，信心低。NVIDIA=skipped（此環境沒有已授權可呼叫的worker/API key），實際0；本機Codex=0；Gemini=0。

Next owner：同一獨立小網路研究員完成唯一一次推論及兩路重播；報告負結果，不用這批已檢視題目調參並再稱盲測。
