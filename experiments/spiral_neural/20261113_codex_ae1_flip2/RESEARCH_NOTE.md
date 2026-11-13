# Pro設計的採納與本輪取捨

2026-11-13，Codex。使用者要求參考Pro的新設計並繼續實驗，由本機協調者自行判斷。已重新讀Git PR28結果head5ceec0c42507bb5646dc0d87089f4a86e0e6269c及PR30head1e4812bd48404c8c03f659ed8a8d86dd5aa5852e的NEXT_PHASE全文，原文Git blob1a5a6bc96b84d1b308f66699aa69ab617e32c3e2已byte核對並保存參考快照。

採用F2優先：三舊類已完整掌握，PR30獨立唯讀報F2全題0/900、0/900、1/900，且第一詞僅82／116／231正確，不能假設只有新第二詞會錯。本機不重跑該研究；一次新baseline核對當輪新r2接線與當前父狀態，外部數值只作背景、不作閘門。

保留同bank、原Model／Adam／shape、fullparent狀態、兩連勝與40cap，僅新增F2。E3/E4與新組合診斷留到另輪，避免同時改變答案長度、資料、容量。採用逐詞、首錯、逐題失去／恢復，而非只看總分；這些可由既有輸出純程式導出，不加神經推論。

本輪不安排完整訓練重播。原learner AST已驗證且不改，工程聚焦新增Q/A、target pool、狀態承接、閘門和指標，再獨立數值驗算全部實際checkpoint的生成與最後TF；三個正式接續各一次，不做第四條重複訓練。沒有重播的trace digest／optimizer中間軌跡不宣稱獨立重現。這是看結果前的範圍決策，不依分數節省或追加預算。

PR29是另一批PyTorch batched Adam學生，PR30/31揭露並修正train suffix_mode別名及第一詞／第二詞的封存統計；不把那些24/6/6 split或864列混入本900bank、不重訓它、不改本機逐target Adam以追求不可比的耗時。新後綴正確也不能排除查表，延續PR27識別性限制。當輪只主張固定bank學習與保持。

來源入口：PR28 RESULTS／publication-manifest及公開checkpoint、PR30 NEXT_PHASE與results_summary。references/PRO_NEXT_PHASE.md與pro30-selected.json保存選定公開參考，不外送整份聊天／私人交接。NVIDIA只核四個合成標籤一次，候選本機逐字驗收；Gemini既有安裝／登入保留，analysis-only隔離未解skip。詳EXTERNAL_REVIEW。

## 執行後更新

三個原PR28模型都曾在第19／22／19輪把四類各900題全部答對；只有101完成連續兩輪全對，202／303在40輪上限未達此標準。這區分了「固定題庫曾經學會」與「繼續更新後能保持」，不能把後兩者寫成從未學會。

三個原fullstate均有固定bank四類全對狀態，未達兩連勝不能寫成從未學會；滿分也不能寫成繼續更新從不退步。保留正式終點27／40／40，不選回較早checkpoint。下一輪優先固定資料、容量、課序只改一個保持穩定性變因；降低學習率是待驗證候選，不是已排除其他原因的診斷。E3／E4及blind-answer-pair測試仍未執行。

PR32已在本輪啟動前讀過：它使用PR29不同cohort、0更新、第二詞b-only介入，沒有重複PR28 F2新訓練。事前25公開檔全部actual bytes核對後，才啟動唯一正式command；研究成功門檻1/3，程式／數據獨立驗收PASS，兩者分列。
