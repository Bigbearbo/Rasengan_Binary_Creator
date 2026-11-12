# 固定容量早混與晚混實驗

原P030 Model、L13/H69、2073參數，三個seed各一對early／late。最終六個學生的Echo／Neg已教題均各6/6；翻轉診斷兩臂皆1/6，未見穩定早混優勢。結果與限制見 [RESULTS.md](RESULTS.md)，接續狀態見 [HANDOFF.md](HANDOFF.md)。

## 凍結規格與公開證據

事前commit為`b5cb521e0c0864bff88609370f451f4c701be7c4`，先公開13個檔案並byte回讀，再啟動唯一正式命令。每學生2400題次／12000targets，Echo／Neg各1200、每個(op,value)各200；完整初態、每op資料序、前1200多重集合及最後1200 actual題流精確配對。只改前段op時序。

輸入是二元Q＋答案前綴。完整資料詞`1010`的Echo答`1010S`、Neg答`0100S`：只反轉三個資訊位，保留尾零，S為外部STOP動作。本固定三資訊位profile與AE1五資訊位多詞課程分開。

| 檔案 | 內容 |
|---|---|
|`run_early_mix.py`、`protocol.json`、`test_early_mix.py`|凍結的driver、範圍與5個工程檢查|
|`manifest.json`、`source-freeze.json`、`inputs.zip`|原參考碼／plan／三完整初態／六完整課序；ZIP共11成員|
|`independent-pre-run.json`、`engineering-checks.json`、`portable-checks.json`|事前獨審、工程與可攜驗證|
|`seed101.zip`、`seed202.zip`、`seed303.zip`|每seed的early與late全部science檔，含完整trace、state、truth、曲線與失敗|
|`compact.json`、`timing.json`、`execution-start.json`|單次正式命令的摘要、成本與preregcommit紀錄|
|`independent-result-review.json`、`audit-evidence.zip`|獨立NumPy與metadata驗收，含實際程式及紀錄|
|`publication-manifest.json`|全部公開檔與ZIP成員的bytes／SHA256及封裝核對|
|`RESEARCH_NOTE.md`、歷史pins/review|1171參數未測Neg、P030/P033先例及Pro PR19並行背景|
|`EXTERNAL_REVIEW.json`|NVIDIA單次公開審查及拒收、Gemini略過，無原API帳號記錄|

六條primary與六條完整replay都完成後才離線評四點×16合法Q。Primary原Model.lesson對replay獨立step迴圈逐target核prediction／loss／完整state hash，並在端點直接比對完整state。其餘審查範圍與真正額外成本分開記錄，不把replay算成新的學生。

## 從公開包重現

使用manifest記錄的Python3.12.14／NumPy2.3.5；把driver、protocol、tests、manifest、inputs.zip放在同目錄。正式入口只讀這些公開檔，不依原機器工作路徑，不執行原參考碼main，也不操作Git或外部模型。輸出必須是新的空路徑。

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python -B run_early_mix.py --execute --manifest manifest.json --approved-manifest-sha c97a49f84e85ad801c9c4e93fbbd1194c217382b23bb16b9afeab0711d9080c7 --prereg-commit b5cb521e0c0864bff88609370f451f4c701be7c4 --out ../new-early-mix-science
```

預期primary／replay各72000updates、303048000training dense MAC；所有state／trace／分數一致，walltime不作逐位相等要求。此命令會實際重新訓練六學生並做六重播；只想讀證據可解開三個seed ZIP到新science資料夾，再複製同目錄compact／timing／execution-start／manifest，還原原82個science檔。

來源保存者可用`--prepare --source ORIGINAL_P030.py --out NEW_PREREG`重建輸入；公開重現不需要此步。`--engineering --source ORIGINAL_P030.py --out NEW_CHECKS`是獨立有界合成驗收，原source可從inputs.zip取出；它有6次toy更新及3次toy推論，不訓練正式seed，不能把所有準備步驟都稱為零更新。

## 判讀界線

值5／6已在先前研究查看，只列曝光診斷。相同兩個值由三個seed重答，不能把跨學生題次當大量獨立新題。操作碼介入在空答案前綴重用首位TF logits，不新增forward，也不識別內部router。相等training MAC不等於推論、I/O或總成本相等。全部seed與失敗保留，沒有依結果續訓或選點。
