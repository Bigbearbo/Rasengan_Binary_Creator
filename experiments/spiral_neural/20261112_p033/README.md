# P033：覆蓋 × 從頭混教已實跑

[結果與限制](P033-覆蓋與從頭混教實測結果-2026-11-12.md)／[事前規格](P033-事前執行規格-2026-11-12.md)。

完成D（36個舊checkpoint、4320條件反事實probe）、A四split×三seed共12條，以及從頭混教主比較12條＋後期混教補充6條。30學生全跑固定預算並完整重播。混教把已教Echo保留由分段1/36提高至36/36，但從頭混教未教val+test為0/24；單補pairwise覆蓋也未穩定修復泛化。

其後獨立補12條H3 Echo-only等總題次控制：原本Echo test12/12在只教Echo3000題後全保留，配對Neg70課程僅1/12。這支持額外多任務干擾，仍有Echo曝光量差異；沒有將補充控制混稱原30條。詳見報告與echo-only-followup-v2/機器紀錄。

`evidence.zip` 含機器摘要、曲線、真值表、反事實與首錯記錄、主要checkpoint、NVIDIA候選及驗收，解開成`evidence/`。完整其餘trace與snapshot留本機，逐檔hash公開。圖形的八值準確率包含6個已教值，不能把曲線.75當未見泛化成功。反事實上三角prefix可能刻意不一致，對角總一致，圖與資料均標記。

## 以公開成果重跑

PR6的evidence.zip有P032必要的36個模型與逐題表，但完整trace原本只存hash；本批附上六條實跑重現控制所需的30份trace，放`evidence/p032-trace-supplement/`，與原trace已逐題核對。為避免改動歷史封存，用以下程式組裝到新目錄：

```text
python -m zipfile -e <PR6的evidence.zip> <P032解壓目錄>
python -m zipfile -e evidence.zip <P033解壓目錄>
python -B prepare_p032_inputs.py --p032-evidence <P032解壓目錄/evidence> --p033-evidence <P033解壓目錄/evidence> --out <新的P032輸入目錄>
python -B p033.py --out <新的P033實跑目錄> --p032-run <新的P032輸入目錄>
python -B summarize.py <新的P033實跑目錄>
python -B echo_only_followup.py <新的P033實跑目錄>
```

組裝器只複製公開的模型、表與trace，逐檔驗SHA，不求解、不改輸入／答案，也不覆寫既有目錄。或直接使用原P032完整實跑目錄。

訓練需要Python3.12、NumPy，本批3.12.14/2.3.5。p030_reference.py與p032_reference.py是舊來源原樣副本，保留學習規則，沒有執行其舊main。diagnostic.py／p033.py是本批程式；summarize.py與plot.py只讀已存成果。繪圖另用隔離Matplotlib3.11.2／NumPy2.5.4，未改訓練套件。

NVIDIA實際一次Lightning免費審查cost0；候選不可靠推論逐項駁回，不當已驗事實。V1/V2、注意力／整串輸出、新算符、其他容量、神經翻譯、儀式和真VM解題仍未跑。
