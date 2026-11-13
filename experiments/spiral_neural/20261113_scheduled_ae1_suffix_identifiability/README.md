# AE1 r1/r2 的後兩詞保留測試為何不能識別複製規則

日期：2026-11-13；owner：獨立小型 NN 研究排程（非 Codex/Pro）。獨立研究分支：
`research/scheduled-nn-ae1-suffix-identifiability-20261113`，base 為 Codex PR #26 frozen pre-run commit
`966297559b4f4dedc4b8cf655258d4036cc21cc8`。**不修改或執行 PR #26 frozen runner、manifest、inputs.zip 或正式 NN。**

## 事前問題、單一變因與資料界線

問題：對固定四詞 `SLE-AE1-n5-v1`，當模型只被教 `r=1/2`，把第三、第四詞換成完全沒出現在配對教材中的組合，能否區分「真正逐詞回音」與「第一、二詞查表死記」？

只改第三、第四個普通資料詞；固定 `01+010`、參數 `r`、前兩詞、總長39位、`END=111100`。合法普通詞ID 0..29，詞碼 `format(ID,"05b")+"0"`；輸出為前 `r` 個完整6位詞 + 模型自己應輸出的外部 `S`。此處 `S` 是分析用的完整標籤，不是另一個原生01詞。

依 PR #26 frozen `payload_bank()`：先列舉 `(word1,word2)` 的30×30=900組，第三、第四詞由 NumPy `default_rng(331000)` 一次抽樣。由此重建900個凍結教材payload、r1/r2共1,800個可用於第二階段的題目；正式NN若第一階段未達標，r2根本不會教。查表控制則明確使用全部1,800筆已公開教材標籤作為自己的訓練集。測試集合為每個前兩詞搭配其餘899個合法後綴組，合計 **809,100種未見四詞payload，對r1和r2各一遍共1,618,200個未見問題**；原本1,800個已教問題保留作正對照。train/test以完整四詞payload區分，**在能決定答案的「前兩詞×r」投影上沒有holdout**，所以本測試本身不是辨因性NN泛化評估。

用凍結的1,800組 `(raw Q, raw answer)` 建立純查表對照（key只含參數三bit和前兩個完整詞的12bit；value是訓練教材已知完整答案，不從新測試Q計算）。逐一列舉全部30⁴合法payload及r1/r2，檢驗lookup與獨立評分答案是否相符。不使用神經模型、外部大型模型或學生的teacher oracle；評分程式依已公開profile生成標準答案，不餵給查表對照。

## 當輪可重現實測 T

執行環境：Python 3，NumPy 2.3.5；無GPU、無本機Codex、無NN執行。命令（從本目錄）：

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python check.py > /tmp/ae1_suffix_audit.json
diff -u results.json /tmp/ae1_suffix_audit.json
```

在此輪工作容器完成 `python check.py`，exit 0，`status=PASS`；包含 seed331000 的尾詞抽樣與公開 manifest 的4個選定位置頻數核對，及完整1,620,000個合法raw Q的窮舉比較。保存 `check.py`、`results.json`；本輪原始本機 bytes SHA256：`check.py=8bba1aeefc7a6c8fcbd8d030f0679b4403da1b4afec8b6204558fe56aa8d4c87`、`results.json=33321e80a22d3319b058b548f9995eaf3b59c42703614ae9751e96cc87478ba8`。上述SHA屬產生本輪結果時的工作容器檔案；公開Git回讀另核對。

結果：查表 **1,620,000/1,620,000 全對**，其中後兩詞未見問題 **1,618,200/1,618,200全對**。查表共有1,800條記憶，沒有規則式逐詞複製，無參數以外的神經能力；這只是構造出的可行替代策略，不代表真實NN已使用它。例：`010100100000000000000001100011110111100` 與 `010100100000000000000001110011110111100` 是合法且不同的Q，但r2正解都為 `000000000000S`。

資源和先驗gate：`seed=331000` 只重建 frozen 教材尾詞；split 如上；輸入／預測為原生raw bits；所用合法profile是 AE1-n5-v1；新NN students 0，forward 0，optimizer updates 0，訓練MAC 0；查表為1,800筆符號記憶。正式PR26的原學生規格仍為 seeds101/202/303、L80/H64、10,499參數、Adam.003、兩階上限各40epoch與原freeze成本；**本輪沒有消耗、替換或授權其正式訓練**。本輪gate是本地獨立重建、manifest頻數抽查、完整枚舉及退出碼；未做公開ZIP完整byte審核，不能冒稱核准其正式訓練。

## 結論及下一個可辨因實驗

**[更新]** 未見第三／第四詞的高分，即使完美，也不能排除前兩詞查表死記；後兩詞對r1/r2答案是因果無關的變因。**[取代]** 將「換後兩詞」列為可檢驗copy泛化的直接證據。**[原因]** 凍結題庫已完整覆蓋全部900組第一、第二詞組合，且r1/r2輸出只依賴其中前r詞。**[狀態]** 程式枚舉與文法結論信心高；NN內部策略未知。

真正可能區分策略的後續設計需要**新事前規格／另行核准**，例如訓練前先保留部分第一二詞組合做heldout，或完整訓練後另設r3/r4的凍結外推測試。不能用已看過PR26分數後才挑選的子集冒充盲測，也不能把新教材混入本次已凍結run。這些是A候選，非本輪已測。此輪**只做後兩詞干預的不可識別性檢驗**，不是平行訓練或新架構比較。

U：作者要求SLE原生01小神經網路、泛化、課程、可辨因實驗；F：Codex PR #26 `protocol.json`、`run_curriculum.py`、manifest與pre-run（僅讀）、PR #24、Pro PR #19／研究交接；T：本輪Python窮舉與完整結果；A：後續必須變更可預測資訊投影才能驗證複製泛化。NVIDIA：`skipped_unavailable`，本輪0次實際外部worker呼叫；亦未呼叫Gemini。Next owner：Codex/Pro或下一輪NN研究者於正式PR26執行或評分後，應避免以後綴替換準確率推斷通用copy；若要作新辨因實驗，先獨立凍結新split/成本/驗收且不覆寫PR26。
