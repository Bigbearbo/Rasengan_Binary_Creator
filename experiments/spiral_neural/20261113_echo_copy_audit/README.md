# Echo 只讀行為與曝光診斷

原 P030 的三個模型都曾在固定三位元域完整照抄；後續混合教學後，三個模型都把 101 回成 100。本次沒有訓練，只檢查六份既有快照，分辨題目位元依賴、逐位置教師曝光及答案前綴補完假說。結論與完整限制見 [RESULTS.md](RESULTS.md)。

## 公開內容

| 檔案 | 內容 |
|---|---|
|`diagnose.py`、`protocol.json`、`test_diagnose.py`|凍結的診斷程式、範圍與七個合成工程測試|
|`input-manifest.json`、`source-freeze.json`|事前本機凍結的來源與輸入 hash|
|`inputs.zip`|六份既有 NPZ、15 份實際 trace、兩份原參考碼、兩份公開來源核對，共 25 個成員|
|`compact.json`、`results.zip`|主程序摘要及六份完整逐題／TF／配對／曝光帳；含全部失敗|
|`evidence.zip`、`verification.json`|設計與程式守門、獨立數值驗收及原始檔前後核對|
|`verify_originals.py`|在原工作區核對原始 25 檔，不載入舊模型|
|`EXTERNAL_REVIEW.json`|外部隊員呼叫與拒收摘要，不含帳號或原 API 記錄|
|`publication-manifest.json`|以上公開檔案的 bytes、SHA256 與 ZIP 成員 hash|

這是事後只讀診斷，先有本機方法／輸入凍結及 code gate，再實跑一次；沒有將 Git 發布日期冒稱事前訓練註冊。原參考碼與六份 NPZ 對應既有公開來源，來源 commit 及 manifest blob 見 input manifest。

## 從公開包重現

使用 Python 3.12.14、NumPy 2.3.5；這是凍結 manifest 實際記錄的版本。下載同目錄的程式、protocol、測試、manifest 及 inputs.zip 後，於該目錄執行。每次輸出目錄必須是尚不存在的新目錄。

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python -B diagnose.py --engineering --out ../echo-new-engineering
python -B diagnose.py --execute --manifest input-manifest.json --approved-manifest-sha 7a691fcf1b55e49cb01bef5c4f6debb3b72cbed0ca39733eb8588170b639f54d --out ../echo-new-results
```

`--execute` 只讀公開 ZIP，不依原機器路徑，不執行舊 main，並禁止 optimizer、成長及 training=True。主程序原結果是 480 次 forward、960480 dense MAC、0 次 optimizer；重現也應得到相同逐題預測、摘要及學習狀態 hash。wall time 會因機器而異，不用它判斷重現成功。獨立審核使用另一份 NumPy forward 直接重算，實際程式與結果保存在 evidence ZIP。

`--prepare --workspace-root WORKSPACE --out NEW_PREREG` 僅供來源保存者從既有資料夾重建輸入包；公開重現不需要此步。`verify_originals.py` 同樣只供核對原工作區；公開輸入完整性依 publication manifest、input manifest 與 ZIP 成員 hash 核對。

## 統計單位與解釋

每份快照評八個合法 Echo 的自主生成與 40 個正確前綴 TF targets。當前位翻轉與未來位控制重用 24 個資料位 logits；報告「兩側正確且跟隨／不變」及原始 token 翻轉／不變，避免把相同錯答案當作成功。未來位的 12 個條件只含八組不同整題配對。

歷史 trace 第三欄是預測字串，教師前綴由真答案重建。15 條原題序與六份 t 均核對；整題曝光、完整教師答案、raw prefix 的相同／衝突標籤分開列出。不把驗證／測試 forward 或歷史重播算成主要模型又受教。

八種三位元輸入是已曝光的有限域。完整成功能支持本域的照抄行為，仍無法區分所有查表與複製演算法，也不能證明任意長度泛化。2a 到 2b 同時增加更新、Echo 曝光與 Adam 年齡，不能將差異單獨歸因 Neg。
