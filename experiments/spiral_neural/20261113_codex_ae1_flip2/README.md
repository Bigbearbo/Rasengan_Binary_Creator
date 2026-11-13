# F2：四類混合續訓

2026-11-13，Codex，已執行並獨立驗收。三個原PR28模型都曾在第19／22／19輪把四類各900題全部答對；只有101完成連續兩輪全對，202／303在40輪上限未達此標準。這區分了「固定題庫曾經學會」與「繼續更新後能保持」，不能把後兩者寫成從未學會。

|Seed|首次四類全對（輪）|正式停止|新bit更新|
|---|---:|---|---:|
|101|19|27輪，兩連勝|972,000|
|202|22|40輪上限，未兩連勝|1,440,000|
|303|19|40輪上限，未兩連勝|1,440,000|

同900個四詞payload；回音E1／E2、翻轉F1／F2各900題，每輪3600題、36000個含STOP的target，全域洗牌。訓練用正確答案前綴交叉熵，測試用模型自己的輸出接回題目。三份完整父state與Adam承接，L80／H64／10499參數、學習率0.003均不改。F2各反前兩詞的5個資訊位，各尾0保留，只有S停止。

末輪各類整串正確數，每類900題：

|Seed|E1|E2|F1|F2|
|---|---:|---:|---:|---:|
|101|900|900|900|900|
|202|900|900|899|869|
|303|900|899|900|898|

本輪參考Pro [PR30下一階段設計](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/1e4812bd48404c8c03f659ed8a8d86dd5aa5852e/experiments/spiral_neural/20261113_window_progress_review/NEXT_PHASE.md)，選擇只加入F2、補逐詞／首錯／逐題lost-recovered；E3／E4留到穩定性釐清後另行設計。PR32是另一PR29 cohort的b-only唯讀介入，沒有重複本輪續訓。

Q39位，參數0010／0100分別表示一／兩組。前兩個普通詞ID覆蓋0..29的900組，後兩詞沿用既有bank；四類Q/A以raw bits輸入。答案prefix回接、cap32／L80 guard、無強制STOP或正解長度截斷。每輪target權重6300:11700:6300:11700，沒有做題長平權。全部三父版舊三類baseline通過後才更新，F2冷分數不作選seed或停訓streak依據。

新正式更新3,852,000次，training dense MAC 81,107,712,000。新非更新forward分為baseline 110,027、輪末probe 3,854,661、最後TF 108,000，合計4,072,688次。父版舊成本不重計。正式runner耗時6440.997966秒，含baseline／訓練／probe／state I/O／最後TF及後置guard，不是純kernel時間；前置凍結、Git與獨立驗收另計。

獨立raw NumPy驗收PASS：107個實際epoch、396,000個baseline與epoch完整自由生成、108,000個最後TF logits／機率／CE；119份science NPZ、120份凍結課序與113份逐點證明。額外forward 4,072,688、dense MAC 42,486,281,216、optimizer0，驗收耗時203.697496秒。逐題word／bit／STOP／雙軸首錯／QID失去恢復均從保存tokens獨立重算；全部凍結來源、state、receipt及原logs前後SHA相同。

本輪沒有完整正式訓練重播，三seed均not_planned、所有replay成本0。原learner不改，工程只有界合成接續測試；獨立驗收涵蓋保存狀態的輸出與計數，不宣稱未保存的逐target原始loss、中間gradient或optimizer軌跡已獨立重建。900組不是全部30^4輸入；沒有heldout、三／四詞回答、任意長度或內部copy／flip算法證據，也沒有early-mix／learning-rate因果對照。

詳細數據見[RESULTS.md](RESULTS.md)、[derived-readout.json](derived-readout.json)，版本與完整封存見publication-manifest.json。[RESEARCH_NOTE.md](RESEARCH_NOTE.md)列Pro設計取捨，[HANDOFF.md](HANDOFF.md)給下一棒；固定外部隊員的真呼叫、拒絕與略過見EXTERNAL_REVIEW.json。
