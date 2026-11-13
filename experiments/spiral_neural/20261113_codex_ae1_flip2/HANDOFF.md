# F2研究交接

2026-11-13，Codex。唯一正式session36593已exit0 CLOSED，沒有待續跑NN。三個原PR28模型都曾在第19／22／19輪把四類各900題全部答對；只有101完成連續兩輪全對，202／303在40輪上限未達此標準。這區分了「固定題庫曾經學會」與「繼續更新後能保持」，不能把後兩者寫成從未學會。

|Seed|首次四類全對（輪）|正式停止|新bit更新|
|---|---:|---|---:|
|101|19|27輪，兩連勝|972,000|
|202|22|40輪上限，未兩連勝|1,440,000|
|303|19|40輪上限，未兩連勝|1,440,000|

末輪E1/E2/F1/F2：101=900/900/900/900；202=900/900/899/869；303=900/899/900/898。末輪共10800題的STOP位置與各詞尾零都正確；不能把1/3兩連勝解讀成只有一個曾學會。

父PR28 result5ceec0c42507bb5646dc0d87089f4a86e0e6269c，prereg5fb6ee26a088f8b4794594346fee7c4988744f18，manifest b8d385db584aec294f5363556f045aecb3ceb8864dc20f4816c30bc591426d95；本PR33當前head為結果入口。完整原parent及40輪課序在inputs.zip，所有實際state、baseline／epoch／finalTF／錯題／word-error-churn資料在science ZIP，不重啟此批、不選回較早state代替正式終點。

新正式更新3,852,000次，training dense MAC 81,107,712,000。新非更新forward分為baseline 110,027、輪末probe 3,854,661、最後TF 108,000，合計4,072,688次。父版舊成本不重計。正式runner耗時6440.997966秒，含baseline／訓練／probe／state I/O／最後TF及後置guard，不是純kernel時間；前置凍結、Git與獨立驗收另計。

獨立raw NumPy驗收PASS：107個實際epoch、396,000個baseline與epoch完整自由生成、108,000個最後TF logits／機率／CE；119份science NPZ、120份凍結課序與113份逐點證明。額外forward 4,072,688、dense MAC 42,486,281,216、optimizer0，驗收耗時203.697496秒。逐題word／bit／STOP／雙軸首錯／QID失去恢復均從保存tokens獨立重算；全部凍結來源、state、receipt及原logs前後SHA相同。

沒有正式全訓練重播；trace／中間optimizer軌跡未重建。參數／原Adam及raw-prefix教法固定，這是同bank持續學習，不是copy算法或blind泛化證據。Pro E3/E4未執行；下一輪先凍結單變因保持測試，暫定學習率對照但尚未跑。不能直接沿用「舊三類baseline必須全900」而默默修補202終點，任何新round都要明列parent與新gate。

Git只新增本實驗目錄，PR33留待審查，不自動合併。NVIDIA實呼1次候選拒絕，Gemini skip已有原因；TEAM本輪AE1-FLIP2-20261113結束前summary確認。詳細限制、成本、全體失敗及指標定義見RESULTS／protocol／publication-manifest。
