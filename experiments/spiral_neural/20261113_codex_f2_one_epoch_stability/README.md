# F2 CPU：學會後降學習率，下一輪三模型全對

2026-11-13，Codex，正式執行與獨立驗收完成。從PR33三個首次四類全對的完整存檔，沿用各自既有下一輪課序，只把Adam學習率0.003改為0.001。模型仍為10499參數、L80/H64，原NumPy CPU；每人恰36000逐bit更新。

|Seed|舊0.003下一輪流失|新0.001下一輪流失|新E1/E2/F1/F2|
|---|---:|---:|---|
|101|7|0|900/900/900/900|
|202|5|0|900/900/900/900|
|303|52|0|900/900/900/900|

事前主要假說「三個seed都嚴格少流失」通過。正式單次命令197.79秒，新增108000更新、2274048000training dense MAC；baseline／新生成／最終TF另計324000forward。獨立一次純NumPy重算32400自由生成題及108000最終TF targets，432038forward、0optimizer，strict exact。

這只證實三個已接觸900payload題庫的選定state能把滿分保持到下一輪，不代表未見題泛化或長期最佳學習率。原PR33終點不變；E3/E4尚未執行。完整optimizer重播事前設定為0，中間gradient／loss軌跡未獨立重建。

先讀[RESULTS.md](RESULTS.md)與[HANDOFF.md](HANDOFF.md)，設計見[protocol.json](protocol.json)。完整state、答案、TF、課序、原source、前後驗收與成本收在各ZIP及publication-manifest.json；原prereg23檔逐byte快照在preregistration.zip。

事前封存commit dbebad71af32ea208dd85171347a4185e2e7e23d，manifest SHA1079366438d667f7bce2ac8fce983792b6c7bf935f4a200fb9eda4e9612e328c。公開副本的機器個人路徑處理見public-redactions.json，其他科學資料保留原bytes。
