# 續訓來源與解讀

2026-11-13，Codex。使用者確認三種混合題：新回音1、新回音2、翻轉。保留PR26學生學習狀態與所有舊Echo raw bits，新增不衝突的當輪題型100，只教Flip第一組，組數欄位從一開始保留。

- 父結果PR26，commit `7213cce112a8411b13dc128c49f9e88acfc9d65f`，branch `codex/ae1-parameter-curriculum-20261113`；開工已重新核對open／unmerged、head相同。三模型的E1/E2各900/900，state包含Adam／birth／t／RNG，不能當全新學生或把父訓練費用再次列成本輪新更新。
- AE1原設計PR16 `685c6f92d9e5a335a2f2a7193d9b501918d90b00`，新回音010、n5資料、組數欄與END。舊numeric opcode含義屬不同profile，本輪不混入；原Model class AST不改。
- 新讀PR27 `cb5f6e8654b7f443cde1746c12442c8bd07f31b0` 的後綴識別性反例：r1/r2答案只依賴前兩詞和參數，查表也能處理任意後兩詞。因此本輪不把有限bank成功或後綴替換稱為通用copy。本機沒有重跑其162萬題窮舉。其引用PR26舊事前commit的未執行文字是歷史快照，接續以父結果7213cce與實際執行收據為準。

沒有與其他mixed policy／joint-from-scratch或相同更新但無Flip的臂做配對，所以只記新增F1與E1/E2保持的觀測，不唯一歸因於Flip語義、共享權重競爭、課程或Adam年齡。全部三模型baseline先檢查父回音，完整性失敗屬integration abort，不能修權重後仍冒稱同parent續訓。

NVIDIA僅收到選定合成事前規格，一次真呼、候選逐項本機驗收；Gemini既有安裝／登入保留，analysis-only隔離未解而skip，不重送未知呼叫。OpenAI原生實作與獨審是另一份記錄。外部結果不是程式／科學gate，詳EXTERNAL_REVIEW.json；不傳整份私人聊天、交接、憑證或帳號quota。
