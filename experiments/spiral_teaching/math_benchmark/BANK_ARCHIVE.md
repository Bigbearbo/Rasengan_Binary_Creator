# 完整合成題庫

`bank.zip` 內只有 `bank/manifest.json`、`bank/questions.jsonl`、`bank/teacher-labels.jsonl`。解開後可直接將 bank 目錄交給 StudentBank。zip 不含程式、私人狀態或憑證。

```text
python -m zipfile -e bank.zip <新的解壓目錄>
```

也可用 `python -B run_checks.py --out <新證據目錄>` 從零生成。兩者問題檔與標籤檔雜湊相同；PUBLICATION_MANIFEST.json 保存封存與解開檔案的 SHA256。生成器已逐題驗證既有語法。壓縮僅用於保存／傳輸，學生仍接收解開後原始 SLE 0/1，未比較壓縮學習效率。
