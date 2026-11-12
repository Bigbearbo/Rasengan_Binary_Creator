# 完整八位數值域 Echo／Neg 混教

三個模型在完整512題全部正確，Echo及Neg均各256/256，於第26／23／18輪連續兩輪通過而停止。這是0..255完整範圍的學習，沒有在同長度內挖洞。完整結果見 [RESULTS.md](RESULTS.md)，接續紀錄見 [HANDOFF.md](HANDOFF.md)。

## 題庫與事前規格

獨立數值profile nop2/nd8，資料詞八資訊位加尾零，op0複製、op1只反資訊位，兩者再自行輸出STOP。0..255全部合法，非AE1的END／UP符號串profile。每輪512不同Q各一次，固定seed洗牌；每輪5120targets，最多40輪。兩op全256/256含STOP連續兩輪才停，失敗即重置streak。

原P030 Model class AST、69個tanh hidden與Adam不改；正確Q14／A9使窗口需L23，共3453參數。生成wrapper cap16加context guard，不用舊generate8、不按正解長度裁切或補STOP。raw Q與答案前綴是學生唯一輸入。

事前commit `1d6ab7fd7fbb75525886226b10b1ed0a744ad9ff` 已公開完整初態與全部40輪課序，13檔byte回讀後才啟動一次正式命令。三學生停止長度由訓練全集分數決定，未依分數加長上限或重生教材。

| 檔案 | 內容 |
|---|---|
|`run_full_domain.py`、`protocol.json`、`test_full_domain.py`|凍結driver、範圍及7項工程驗收|
|`manifest.json`、`source-freeze.json`、`inputs.zip`|9成員：原source、plan、512題pool、3fullinit、3份40輪完整課序|
|`independent-pre-run.json`、`protocol-review.json`、`engineering-checks.json`|獨立可攜／數學及實際工程紀錄|
|`seed101.zip`、`seed202.zip`、`seed303.zip`|所有實際epoch的state／512輸出／統計、initial/final、fulltruth、全部失敗|
|`compact.json`、`timing.json`、`storage.json`、`execution-start.json`|正式摘要、分列成本、儲存與prereg紀錄|
|`independent-result-review.json`、`audit-evidence.zip`|一次獨立NumPy驗收、數值proof、程式、實際stdout及receipt|
|`publication-manifest.json`|所有公開bytes／SHA、ZIP成員及完整224science檔inventory|
|`EXTERNAL_REVIEW.json`、`external-context.json`|NVIDIA公開方法候選與本機處置，無私聊或原API帳號記錄|

全部primary及指定replay結束後才計final TF，直接重用末輪free結果。僅seed101完整replay，202/303明列not_planned。每target只保留prediction/loss串流digest，不保存或冒稱獨審重建全部中間權重。

## 從公開包重現

使用manifest記錄的Python3.12.14／NumPy2.3.5。下載同目錄driver／protocol／tests／manifest／inputs.zip；正式入口只靠這些檔案，不依原機器路徑，不執行legacy main或呼叫外部模型。輸出必須是尚不存在的新路徑。

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python -B run_full_domain.py --execute --manifest manifest.json --approved-manifest-sha dabdb58a54ffd93afa350f19876a53550bcfcfd6de9b5199ee8b3b26d2b8d658 --prereg-commit 1d6ab7fd7fbb75525886226b10b1ed0a744ad9ff --out ../new-full-domain-science
```

此命令實際訓練三個新學生與指定seed101重播，並按凍結規則提前停止；原環境參考為26／23／18輪。若只讀證據，解開三seed ZIP到同一新science資料夾，再複製manifest／compact／timing／storage／execution-start，能還原224個原science檔。Walltime不是逐位重現判準。

來源保存者可用`--prepare --source ORIGINAL_P030.py --out NEW_PREREG`重建輸入，公開重現不需要這步。原source亦在inputs.zip。`--engineering --source ORIGINAL_P030.py --out NEW_CHECKS`僅作有界合成與mock驗收，另有native6updates／16forward，不算正式seed；mock20480target calls／4probe不是神經更新。

## 判讀

本批是完整有限域的掌握程度與停訓驗收，不是盲測或未教值泛化。擴大題域時也加大必要窗口，不能單獨歸因題數。完整範圍成功不識別記憶／一般算法；更長詞、多詞AE1、router與成長效益都未由本輪測試。詳細實際成本及source／輸入未變證據見RESULTS與獨審JSON。
