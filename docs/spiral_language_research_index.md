# 螺旋語研究程式入口 — Codex 導覽（2026-11-11）

## 2026-11-13 Pro／Codex 輪流研究

先看[當前交接卡](ai_orchestration/RESEARCH_HANDOFF.md)。Pro 已對最新可見的 Codex P035 做[新的有界唯讀核對](../experiments/spiral_neural/20261113_pro_p035_review/README.md)，沒有實質 finding；另完成[第一批 UR1 神經通知實測](ai_orchestration/PRO_NOTICE_LEARNING_RESULTS_20261113.md)。三學生及全部重播已跑完，最後已教17/36、保留0/18，強判準0/3；已教未穩、錯誤主要先出現在地址。下一棒Codex先審核並另凍結更新次序診斷，不擅自延長原實驗。以下歷史段落保留各自時點。

## 2026-11-13 Pro 更新：有位置的升階通知

[UR1 設計](ai_orchestration/PRO_UPGRADE_NOTICE_DESIGN_20261113.md)依使用者的三份通知、局部回覆與尾兩碼控制構想，定義新 profile 的結構地址、目標寬度與一次提交規則。[獨立 codec 與測試](../experiments/spiral_neural/20261113_pro_upgrade_notice/README.md)只驗證有界協議，未做神經訓練；根控制寬仍固定，未完成任意根擴張。本分支已整合 Codex P035，保留 P034／P035 的完成狀態；此前 [Pro 小網路／成長審查](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/4e2ded91166a4fd9348dccf8fc71ddf01e991645/docs/ai_orchestration/PRO_SLE_SMALL_NETWORK_REVIEW_20261112.md)保留獨立固定入口。

## 2026-11-12 Pro 更新：現況與下一輪研究

先讀[研究現況](ai_orchestration/CURRENT_RESEARCH_STATUS.md)與[ChatGPT Pro後續設計](ai_orchestration/PRO_RESEARCH_DESIGN_20261112.md)。Codex的P033覆蓋／從頭混教／續訓控制已在PR #7完成；[Pro獨立核對及解析器修復](../experiments/spiral_neural/20261112_pro_review/README.md)另列實測歸屬。下方歷史段落保留其封存時點，不以舊「未完成」覆蓋較新的固定證據。

[Pro小網路與成長假說審查](ai_orchestration/PRO_SLE_SMALL_NETWORK_REVIEW_20261112.md)補充原始假說邊界、onehot零值與padding區別、P030局部遷移、三checkpoint機制探測、相關原論文及尚未執行的編碼×成長比較；不把E900／固定三位元attention當成SLE優勢已獲驗證。

## 2026-11-13 Codex 接續：P034／P035 已完成

[P034／PR #9](../experiments/spiral_neural/20261112_p034/README.md)完成等Echo曝光與一個attention配置；[P035](../experiments/spiral_neural/20261112_p035/README.md)完成Pro後續input-codec×容量時序12學生篩查。P035最後已教144/144、operand-heldout5/48，配對interaction0/−1/0；共享答案文法與已查看小域限制保留。4/6曾在Neg教師答案出現，不能稱所有角色都未見。下方Pro／歷史段落保留當時語氣，不將舊待跑敘述覆蓋完成證據。

## 2026-11-12 新增：真正神經網路實測

[P024–P030 實測成果索引](ai_orchestration/CODEX_EXPERIMENT_RESULTS_INDEX_20261112.md)連到可重跑程式、機器證據、模型checkpoint與GPT交接。這與下列腳本式雙代理示範分開；P030只完成第一批，神經轉碼器與P031數學比較仍未實作。

這是 **Bigbearbo / Rasengan_Binary_Creator** 原有倉庫的補充目錄。2026-11-11 從使用者 ChatGPT 圖書館整理搬入可重跑的螺旋語研究成果。**沒有更動倉鼠 VM 主程式，也沒有聲稱本輪已把所有研究資料搬完。**

## 從哪裡開始

| 目標 | 入口 | 性質 |
| --- | --- | --- |
| 想直接跑先前的解析器／兩個 AI 模擬 | [experiments/spiral_parser/](../experiments/spiral_parser/) | **優先**；v0.1–v0.6 原始 Python、測試、持久化樹、增量語法包、錯誤回報 |
| 想教一個只接收 01 的模型 | [experiments/spiral_teaching/](../experiments/spiral_teaching/) | 實驗教學編碼器、二層協議驗證器、[歷史工具](../experiments/spiral_teaching/legacy/) |
| 想研究兩條詞典／版本／歷史／ICFP 調變 | [experiments/spiral_semantics/](../experiments/spiral_semantics/) | SL09–SL18 **符號與合成工作負載**，多個腳本有互相 import 依賴 |
| 想研究一套螺旋式自然語言記憶文法 | [experiments/spiral_memory/](../experiments/spiral_memory/) | SNL-MEM-0.2 **另一個獨立人類可讀文法**，不是 bitstream SLE |
| 想對比 ICFP 2020 外星語言 | [螺旋語 vs ICFP 2020](spiral_language_vs_icfp2020_for_codex.md) | 公平比較、原始文獻、待做實驗 |
| 想了解 2026 後續研究主張 | [研究路線](spiral_icfp_exchange_research_20261102.md)、[自然語言示例](spiral_language_natural_examples_20261103.md) | 歷史分析與設計候選，不是已執行標準 |
| 想讀原始 MLP 理論草案 | [原始中文論文](references/MLP_paper4_zh_original.md)、[早期協議](../spiral_language.md) | 歷史來源；多處語法細節在後續研究中仍有不同版本 |

## 最快重跑

```bash
cd experiments/spiral_parser
python -m unittest -q test_spiral_parser test_spiral_dialogue test_spiral_dialogue_v02 test_spiral_dialogue_v03 test_spiral_tree_packet_v04 test_spiral_tree_packet_v05 test_spiral_tree_nodes_v06
python demo_branch_v06.py

cd ../spiral_memory
python -m unittest -q test_spiral_core_public

cd ../spiral_teaching/legacy
python spiral_converter.py test
python spiral_wire.py test
node test_js.cjs

cd ../../spiral_semantics
python 'SL16_獨立詞典同步與ICFP雙向Modulation驗證.py'
python 'SL18_多接收者詞典提升策略與離線成本驗證.py'
```

驗證日期 2026-11-11（於整理環境執行）：解析器 **75/75** Python unittest PASS；自然語言記憶的**公開合成**測例 6/6 PASS；`spiral_converter.py` 2,040 組、`spiral_wire.py` 262,112 組、JS 32,736 組往返測試 PASS；SL16、SL18 有成功執行結果，其餘 SL09–SL17 在整理時通過 Python 語法編譯，但**沒有逐一重跑整套完整研究**。這些是**程式測試，不是 AI 真的學會語言**。

## 解析器版本重點

- v0.1–v0.3：切詞、雙端教學、題庫持久狀態、從簡入難、錯誤回報、舊題複習。
- v0.4：整棵語法樹打包、分包／重傳、校驗後原子套用。
- v0.5：差分語法包、依高水位決定詞寬、跨版本回編碼。
- v0.6：修正算符最大已分配編號（high-water mark）的位置。**權威數值存在解析器語法樹 `tree.math.operator_branch.highwater`**，不是 GPT 記憶，也不應只放樹外 registry；刪除節點不能縮減已用編號。
- 需要已知上下文（層級 `k`、資訊位長 `n`、offset、版本），不能把「已能處理已知版本」誤讀成「任意 01 皆可無共識唯一解碼」。
- AI 模擬學生具有腳本式策略和有限候選函數庫；**不是真正無語言神經網路從零學會**。

## 來源與公開邊界

使用者原始研究提案與論文記為 U，已存原稿為 F，真正執行程式測試記為 T，AI 新設計與推論記為 A。不同年份、不同實驗不能混稱最新一版。現有 `README.md`、`Hamu_VM_v0.1.cpp` 是更早的歷史資料；倉鼠 VM 另有較新 ZIP 研究線，**本次沒有替換 VM 或修改現有舊版程式**。

原始封存/更多歷史在使用者 ChatGPT Library：
- `/倉鼠世界/螺旋語解析器_雙代理模擬_20261103/`（v0.1–v0.6 ZIP 與報告）
- `/倉鼠世界/螺旋語_跨模型純01實驗/`（教學原始封包、研究腳本、逐輪記錄）
- `/AI研究記憶/螺旋語記憶_平行實驗/`（SNL-MEM 獨立研究）

此公開 GitHub **刻意沒有上傳**：跨聊天原始個人記憶筆記、完整人類／LLM 對話日誌、教師未公開答案表與不相干的 VM 新版 ZIP。原始碼若依賴這些資料，請改用明確的合成測例或先取得授權。不要因為測試不在 Git 就把原始通過數據冒稱已重新驗證。

## 後續建議

先讓 Codex 審閱已能跑的 v0.6 與各種詞表原型，然後在同等限制下比較 SLE 與 ICFP 2020：(parse\circ encode) 正確性、跨版本一致性、錯包修正、整樹／增量同步、字元／位元與執行成本、未見題泛化、已知規則保留率。維護時回報所有變更檔案、執行命令、實際 PASS/FAIL 和未完成部分。

## 2026-11-12：自然語言記憶平行研究補檔

[完整公開衍生研究檔案](../experiments/spiral_memory/research_archive_20261102/) 補入 SNL-MEM-0.1/0.2 的對照語料、解析與查詢程式、R01/R02 詞典、AI 自讀非盲案例與測試。**公開版本已替換部分私人識別碼及 Library 內部來源路徑，並非私人記憶的完整原樣備份；原始結果 JSON 和 ZIP 未上傳。** 2026-11-12 對公開化副本本地重測：v0.1 29/29，v0.2 32/32；僅是腳本規格測試。
