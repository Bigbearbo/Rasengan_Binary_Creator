# P032：容量與教學比例對照已實跑

先讀 [結果與限制](P032-容量與教學比例實測結果-2026-11-12.md)，再看 [事前規格](P032-事前執行規格-2026-11-12.md)。

24條Neg分支＋12條共用暖身全部完成且完整重播一致。H72/H128、70:30/50:50、兩組6/1/1分割、三個seed。四格已教題各72/72，test依序0/12、1/12、1/12、0/12；沒有一個學生test兩題全對，B中途增長依條件不執行。未把工程PASS當學習成功。

`evidence.zip` 是篩選後的完整機器摘要／曲線／真值表／失敗題、24條Neg最終checkpoint、12條暖身最後checkpoint、NVIDIA候選審查與決定。解開會得到 `evidence/`；只有合成研究資料，沒有憑證、私人對話或字型快取。`local-artifact-hashes.json` 保留本機完整trace與其他snapshot的hash；全部軌跡可從程式與manifest重播。NPZ的驗收標準是陣列內容與optimizer/RNG相等，不依賴ZIP內部時間戳。

```text
python -m zipfile -e evidence.zip <新目錄>
python -B p032.py --out <新實跑目錄> --p030-archive <P030 checkpoint根目錄>
python -B summarize.py <新實跑目錄>
```

需要Python3.12與NumPy；本批3.12.14/2.3.5。P030 checkpoint根目錄的結構是`dynamic-101/2a_echo_op2/state.npz`等，可沿用已公開PR4封存。若只跑P032-A，未來可將D分離；本版命令會先執行D，沒有發現舊checkpoint會明確失敗。

`p030_reference.py` 原樣保留實際P030來源，`p032.py`只復用其模型／學習／語法，不執行舊main或改舊OUT。跨容量固定初始共同block與新增出邊0，不是中途增長實驗。`summarize.py`只統計已存資料；`plot.py`只繪圖，可用`--plot-deps`指定隔離matplotlib目錄，本批繪圖NumPy2.5.4未參與訓練。

NVIDIA任務N05-P032-20261112真實呼叫1次Lightning免費模型，cost0；候選逐項接受檢查／駁回錯誤推論，見報告與evidence中的nvidia-review.json。

P031共用題庫的PR5獨立保留、未混入本批教材；國小加法、新神經翻譯、11110儀式、真VM解題均未開跑。既有CMake工作流缺根CMakeLists.txt的限制未在本批修改。
