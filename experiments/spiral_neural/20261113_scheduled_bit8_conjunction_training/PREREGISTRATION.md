# AE1 bit8＋bit16 組合教學：事前凍結（optimizer 尚未啟動）

work_id: SLE-AE1-BIT8-CONJUNCTION-TEACH-20261113-12
owner: 獨立小型神經網路研究；不修改 Pro/Codex/VM/語法/UR1 工作樹。
parent: Draft PR #42，head `3f6af7aba3c257a8a9fd3ac7728a3b42bc461037`；四筆母模型與課程實際從 PR #40 封存（兩 seed 各一份）。
唯一訓練干預：兩臂各新增 16 個 r2 題（4 b × a0–3，c1,d0），control b=16,17,20,21；conjunction b=24,25,28,29，即只在第二資料詞 b 中添加 bit8。兩臂同時新引入 c1；c1 與追加題數、r2、a、d、權重起點、課序、計算與訓練方式在臂間完全相同。母課程原有 120 次呈現，但只有 96 個 distinct Q；24 個重複由原教材保留，不能虛稱 120 個 unique。加入後每臂 136 次呈現、112 個不同 Q、每輪 1408 teacher target，16 個追加題與母課程互不重複。
合法 profile: SLE-AE1-n5-v1。Q=`01+010+3bit(r)+0+4*(5bit ID +0)+111100`，39 bit，ID0–29；30 END，31 UP 保留，不能任意填；A 前 r 個完整 6bit 資料詞後由 NN 自主輸出 S，禁止 oracle 回填。新增樣本 `r2,a0,b24,c1,d0` raw Q=`010100100000000110000000010000000111100`，預期 A=`000000110000S`。學生輸入僅原生 01 Q＋先前生成/teacher prefix，160維 slot one-hot、64 tanh、3 logits，L80、cap32，10499 參數，每一步 10432 dense MAC。

split: 訓練保持原 PR40 120 題（60 r1＋60 r2）與追加16題；primary val b26,27 × a4 × c1,d0（2 Q）；primary test b26,27 × a5 × c1,d0（2 Q）；兩臂各相同。b26/27 均未在本輪教材出現，研究人員在 PR #42 已見相近 domain，**不是 researcher-blind**。secondary: 追加域 a0–3、原 seen b16–21 c0、舊 base train/val/test、r1無關b、原 c0 題域。不得看 primary 改超參數。

seeds 101,202；各從對應 PR40 mixed parent F32 checkpoint 完整相同權重開始，各臂新 Adam lr0.003；固定 100 epochs × 1408 targets，batch64，22更新/epoch，2200更新/學生，4學生8800更新，563200 target presentations；訓練前向密集 MAC 上限5875302400，**不包含反向/optimizer**。同 seed 的兩臂採相同 `default_rng(seed+131000+epoch).permutation(1408)` 的 slot 序列。沒有提前停、額外 seed、best-checkpoint 選擇或學習率變更。

資料 SHA256：parent_course.json `e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a`; parent weights seed101 `ac022fdcac1c6e9de5b78e1667519a6443e05c7f8e48fe4b84514432a1576009`, seed202 `048c719e8c2afbbcac579b80a2f820989eb68ba030a1f2ce7c2747474897a157`; local runner `run.py` SHA256 `ae6c3e0d3c129d86100f1d4d686818fa7f2cf3f4f8631aed9494121fb23efeca`; local complete prereg JSON SHA256 `1f0442de163b03fffb1e8bfbb0159f2dae2d09c1d9c8a8b3f8c7f98c269af029`，兩者將同原件隨實驗 ZIP 交付。Git 本 prereg 是公開凍結戳，不等於 runner 檔已上傳。

**事前 gate:** 驗證 source/course/weights SHA、合法 Q39/raw fixture、保留原母教材重複數與分布、追加16 unique與母課程不交叉、heldout不交叉、模型10499參數、兩 seed F checkpoint 在舊 c0 b16..21 各36/36且新 c0 b24..29 各0/36，才允許訓練。已於 optimizer 之前在本地 `python run.py gate` PASS。另保留一次 preflight FAIL：錯把原120列要求為120個 unique，發現原有24對重複，修正 gate 不改教材、不做更新。

**Primary gate:** 兩seed各自 conjunction 臂在 val+test 的 b26/27,a4/5 共4題至少3/4，且 control 臂至多1/4；兩seed都達成才PASS，否則FAIL。任何結果保存完整 raw Q/expected/actual、全部失敗、最後weights、評估 forward/MAC及兩原權重雜湊。測本有限位元組合遷移，不聲稱已學通用copy，更不聲稱 SLE 優於普通binary或真正數學能力。

U：作者希望原生01 NN能學、可辨因泛化、資源固定；F：PR40權重、PR42既有失敗與 P030–P035 歷史；A：目標位置直接教組合 bit8+16 能遷移至相同高位、未教低位的 b26/27；T（執行前）：唯讀 source/checkpoint 引用及 gate PASS，無新訓練。NVIDIA/本機 Codex/Gemini 尚未呼叫，預計0；未授權 worker/API 不調用。

下一owner：獨立驗證者／Codex，先審核原始 weights + raw bits，後續新研究另立 pre-reg、別調這批 test。
