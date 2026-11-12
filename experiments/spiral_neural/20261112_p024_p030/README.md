# P024–P030 實測封存與可攜重跑

2026-11-12。這是Codex本機已實跑的**公開合成研究成果**，供GPT與Codex透過Git對照設計與證據。Git原有P027/P028/P030/P031文件多為設計，不能當成已完成結果。

先讀[GPT交接](GPT_HANDOFF.md)與[結果索引](../../../docs/ai_orchestration/CODEX_EXPERIMENT_RESULTS_INDEX_20261112.md)。原始本機實驗沒有因本次出版重新選seed、延長失敗預算或改分割。

## 實測結論

|本機實驗編號|實際改動|主要結果與限制|
|---|---|---|
|P024|逐步0/1/STOP RNN，整串獎勵|與新跑並行對照均未學會；不能單獨歸因於自回歸|
|P025/P025B|完整題目＋分隔符＋前綴，RNN/MLP|仍失敗；直接前饋MLP不需跨步hidden，但原教學方案不足|
|P026|逐token +/-1、整串對才換題|只見8/1/12種題，保留全0/64；教材阻塞|
|P027|調度與CE對照|獎懲＋每題換保留64/60/64；CE＋正確前綴＋每題換三seed皆64/64；同100k更新亦同|
|P028（本機）|教材檢查提前停止|CE於2496/2304/2688題次確認，保留皆64/64；獎懲較慢且不全滿分|
|P029（執行上游P028）|資料階n1→8、不回教舊階|全部升到8，n8額外960/768/768題次；含短題成本沒有一致優勢；test32/30/31之32|
|P030第一批|純01、動態/固定/瓶頸容量、持續Echo→Neg→Zero→END|9學生中只有fixed303到END驗證過關，但該階test僅1/3；多數train全對、未教值失敗|

P024–P029輸入可含外部題答分隔符；**P030取消分隔符，只有0/1輸入、0/1/STOP輸出**。STOP不是SLE END。P029不是全語言課程；P030第一批不是完整計畫，神經轉碼器、ASCII/通用輸出競賽及P031數學題庫尚未實作。

## 內容與版本

- `reports/`：中文結果、事前設計與PNG/SVG，保留成功與失敗。
- `source_snapshot/`：實驗當時原始程式，逐byte保留；原本有本機路徑，供歷史比對，**不要直接執行**。
- `src/`：可攜副本。只改路徑綁定、依賴定位與選用繪圖依賴；學習/資料/門檻公式不變。完整變更見`portability-patches.json`。
- `evidence/`：各輪plan、compact、摘要、測點、split、模型/optimizer checkpoint；大的curve/probe及CSV以gzip保存。
- `artifact-manifest.json`：封存檔案大小/SHA256；有轉換的檔案另記本機原始SHA。manifest本身不列入自身雜湊。
- `omitted-traces.json`：112份完整逐題trace未上傳，記其相對路徑/大小/SHA，留本機並可由完整重跑生成。
- `PUBLICATION_RECORD.md`、`publication-validation.json`：本次出版範圍與實際檢查結果。

合成模型checkpoint不含帳號、個人聊天、金鑰、Telegram資料或代理佇列。未收集其他本機工具目錄。證據JSON與報告把本機workspace前綴換成`LOCAL_WORKSPACE`；這些是來源註記，不是可執行依賴。

訓練環境為Python3.12.14、NumPy2.3.5。來源計畫基準含55d1037/ad6281c；本次出版從807cd49開始，保留1703c34轉碼計畫與807cd49的P031計畫，不將新計畫倒填為舊實驗已完成。

## 驗算封存模型

在repo根目錄，以有NumPy的Python執行（Windows請用實際Python執行檔，避免WindowsApps alias）：

```bash
python -m pip install -r experiments/spiral_neural/20261112_p024_p030/requirements.txt
python -B experiments/spiral_neural/20261112_p024_p030/reproduce.py validate
```

此入口不呼叫外部模型、不做完整重新訓練。它檢查SHA、非pickle/有限checkpoint、公開內容高信心secret pattern，實際從checkpoint重算121組實驗指標，並重跑CE、停止規則、oracle與擴容邊界檢查。secret pattern只是輔助，公開範圍主要由明確檔案白名單與人工審閱決定。

## 從零重新訓練

```bash
python -B experiments/spiral_neural/20261112_p024_p030/reproduce.py run --experiment P030 --work ../sle-neural-rerun
```

可選`P024`、`P025-RNN`、`P025-MLP`、`P026`、`P027`、`P028`、`P029`、`P030`。`--work`必填，且必須在此封存目錄之外；請用獨立工作目錄。不覆寫`evidence`，同名run已有plan時原程式會拒絕覆寫，不自動刪除。

主程式輸出包含自身的完整決定性重播；依硬體與NumPy/BLAS版本，walltime不同，跨平台不能僅以bitwise權重一致作唯一判斷。本次可攜P030另從零完整重跑並核對原始trace hash與checkpoint陣列，結果詳見出版記錄。

在相同訓練環境下，P030重跑後可比對逐題trace SHA、全部陣列與科學指標：

```bash
python -B experiments/spiral_neural/20261112_p024_p030/verify_reproduction.py --work ../sle-neural-rerun
```

若重繪圖，在Python環境另安裝matplotlib，再對新`--work`執行`src/p030_summarize.py`或`src/summarize_monotonic_curriculum.py`，並設定`SLE_RESEARCH_WORK`為相同輸出根目錄。歷史PNG/SVG已隨報告附上。

## 研究界限

固定長度STOP正確不等於學會Echo；教師prefix準確率不代替自由生成；oracle語法能力不算學生能力。舊保留分割已用於分析，不是全新盲測。P030每op只有6個train值、1個val、1個test，樣本極小，不能以某seed單題通過評定普遍能力。未使用外部parser在學生推理時代算答案。
