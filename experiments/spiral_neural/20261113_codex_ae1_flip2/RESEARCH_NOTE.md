# Pro設計的採納與本輪取捨

2026-11-13，Codex。使用者要求參考Pro的新設計並繼續實驗，由本機協調者自行判斷。已重新讀Git PR28結果head5ceec0c42507bb5646dc0d87089f4a86e0e6269c及PR30head1e4812bd48404c8c03f659ed8a8d86dd5aa5852e的NEXT_PHASE全文，原文Git blob1a5a6bc96b84d1b308f66699aa69ab617e32c3e2已byte核對並保存參考快照。

採用F2優先：三舊類已完整掌握，PR30獨立唯讀報F2全題0/900、0/900、1/900，且第一詞僅82／116／231正確，不能假設只有新第二詞會錯。本機不重跑該研究；一次新baseline核對當輪新r2接線與當前父狀態，外部數值只作背景、不作閘門。

保留同bank、原Model／Adam／shape、fullparent狀態、兩連勝與40cap，僅新增F2。E3/E4與新組合診斷留到另輪，避免同時改變答案長度、資料、容量。採用逐詞、首錯、逐題失去／恢復，而非只看總分；這些可由既有輸出純程式導出，不加神經推論。

本輪不安排完整訓練重播。原learner AST已驗證且不改，工程聚焦新增Q/A、target pool、狀態承接、閘門和指標，再獨立數值驗算全部實際checkpoint的生成與最後TF；三個正式接續各一次，不做第四條重複訓練。沒有重播的trace digest／optimizer中間軌跡不宣稱獨立重現。這是看結果前的範圍決策，不依分數節省或追加預算。

PR29是另一批PyTorch batched Adam學生，PR30/31揭露並修正train suffix_mode別名及第一詞／第二詞的封存統計；不把那些24/6/6 split或864列混入本900bank、不重訓它、不改本機逐target Adam以追求不可比的耗時。新後綴正確也不能排除查表，延續PR27識別性限制。當輪只主張固定bank學習與保持。

來源入口：PR28 RESULTS／publication-manifest及公開checkpoint、PR30 NEXT_PHASE與results_summary。references/PRO_NEXT_PHASE.md與pro30-selected.json保存選定公開參考，不外送整份聊天／私人交接。NVIDIA只核四個合成標籤一次，候選本機逐字驗收；Gemini既有安裝／登入保留，analysis-only隔離未解skip。詳EXTERNAL_REVIEW。
