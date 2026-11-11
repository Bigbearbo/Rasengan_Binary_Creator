# SNL-MEM 記憶系統研究：公開衍生資料庫（2026-11-12）

來源：使用者 ChatGPT Library `/AI研究記憶/螺旋語記憶_平行實驗/`，原始日期 2026-11-02。這次是**複製、公開安全化與核對**，未搬動或刪除 Library 原檔。不是完整私人記憶倉庫的鏡像。

## 入口

- [v01/](v01/)：SNL-MEM-0.1 階層標籤版本；含 `build.py`、`比較測試.py`、`記憶查詢.py`、同一 14 筆事實的 Markdown/SNL/JSON 衍生對照。
- [v02/](v02/)：SNL-MEM-0.2 自然語言組合、語義作用域、R01/R02 詞表、16 項非盲 AI 直讀案例及 32 項機器測試。
- [../spiral_core.py](../spiral_core.py)、[../test_spiral_core_public.py](../test_spiral_core_public.py)：2026-11-11 已上傳的 v0.2 公開核心與六項純合成測試。本目錄 v02 的 `spiral_core.py` 是封存自足副本，**切勿視為另一條正式實作主線**。

## 本次公開化處理

原始研究將多個使用者專案的實際記憶當作 14 筆對照語料。由於這個 GitHub 倉庫是**公開**的，本版本把 `Y001/Y006` 替換為 `PUB001/PUB006`，把特定私人專案名稱換成「發布流程示例」，將部分 ChatGPT Library 來源路徑改成 `fixture://...` 標記。替換的 `fixture://` 是**測試示例**，不是可存取的證據 URL。各檔為衍生副本，不可冒充逐字相同的原始研究檔。

原始兩個 ZIP 封存未公開，以免無意附帶私人資料或重複包裝內容；原始機器結果 JSON 及歷史「初輪統計」未複製，以免與改寫語料不一致。歷史報告保留作方法背景，**其原始 bytes、時間比較不能套用公開衍生資料**。執行下列測試將在各目錄產生新的本機 JSON 結果。

## 可重現的本輪核查

2026-11-12 在暫存的公開化副本執行：

```bash
cd experiments/spiral_memory/research_archive_20261102/v01
python 比較測試.py                 # 29/29 checks passed, 14 records
python 記憶查詢.py --格式 螺旋語 --ID H006

cd ../v02
python test_core.py                # 32/32 structural assertions passed
```

上面是**本次實際執行公開衍生副本**所得，不代表 GitHub Actions 已跑或 Codex 本機已跑；報告中的模型語義理解、長期記憶優勢與跨模型泛化都**沒有**因此得到證明。

## 給多模型共用記憶 MVP 的使用方式

先閱讀此 README 和 [整合計畫](../../../docs/ai_orchestration/CODEX_MULTI_AGENT_MEMORY_PLAN_20261112.md)。可借鑒：stable ID、scope/版本、來源標記、狀態、依賴、可回溯取代、不同來源資料的隔離；但 SNL-MEM **不是已決定採用**的任務記憶儲存格式。

Codex 應用相同預算比較普通 Markdown 索引與 SNL-MEM，先驗正確性、來源追溯、增量更新與 token 成本，再決定要不要引入自然語言語法層。不可因本研究名稱含「螺旋語」就擅自取代既有 bitstream SLE。
