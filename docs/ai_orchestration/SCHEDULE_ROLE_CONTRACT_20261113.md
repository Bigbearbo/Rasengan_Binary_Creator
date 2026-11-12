# 定時研究 Agent 的技術責任邊界與 Git 交接契約（2026-11-13）

本文件提供螺旋語／倉鼠世界**公開技術研究**可共用的角色路由，不記錄使用者私人排程 ID、私人聊天或私人研究材料。真正排程、是否啟用、頻率及執行環境以 ChatGPT Automations 的即時設定為準；**本文件不能啟動、控制任何本機 Codex、NVIDIA 或其他 Agent**。

| 研究職責 | 優先來源 | 可以寫入的成果 | 不應重做的事 |
| --- | --- | --- | --- |
| 螺旋語語法與協議 | `docs/spiral_language_research_index.md`、原始 MLP、版本／詞表、Pro UR1 實驗分支 | 不破壞相容性的語義規格、解析器反例、round-trip 證據 | 不冒充 NN 自主習得，也不替 VM 算題 |
| 倉鼠 VM 成長與驗證 | Library 工作入口實際最新 ZIP、`experiments/hamu_vm/` 的當前 Git 分支與測試 | VM 執行／記憶／HP／交易的可重現程式與測試 | 不重做小NN模型訓練，不把宿主實驗說成 guest 自治 |
| 小型 NN 教學與成長 | 已實測 P030–P035，當前 `CURRENT_RESEARCH_STATUS.md`／`RESEARCH_HANDOFF.md` 所在分支，題庫 PR #5 | 有事前凍結 manifest、完整 seed、negative result、checkpoint／重播的控制實驗 | 不從 main 舊 P033 機械重跑；不可繞過明示的 SHA 授權門檻 |
| 多 Agent Git 交接／共用記憶 | `docs/ai_orchestration/GIT_RESEARCH_HANDOFF_20261113.md`、本倉庫 AGENTS、最新 PR DAG、原共用記憶計畫 | owner/基底 SHA/PR 關聯更新、版本查核與路由 mock、去重證據 | 不代替各研究員重新跑科學實驗，不自動合併 stacked PR |
| 記憶維護 | Library 當前主題活檔、L0/L1/L2/L3/L4 索引，與公開 Git 的可驗證技術來源 | 去敏索引與過時來源修復、證據版本對照 | 不自動複製私人 Library、聊天、金鑰或不可公開原稿 |

## 新回合的最小檢查

1. 實際查 `open/merged PR`，對照 head/base/sha、最新有實測證據的 entrypoint。PR #8→#9→#10→#11→#12 為歷史依賴鏈的當時快照，不能把 PR 數字當永久事實，也不能因 PR mergeable 就自動合併。
2. 記 `workstream / topic / scope(profile,codec,stage) / baseline_sha / owner / status / acceptance`；若已有同樣工作且無新證據，停止重做，改為別的可驗證問題。
3. 在動作前區分 U（作者）、F（原始資料）、T（本輪實測）、A（模型推論）；引用歷史測試不能冒稱本輪 T；模型對自己報告的同意不是驗收。
4. 需要運行模型時先凍結資料 split、seed、預算／成本、測試 gate；不得因保留集失敗而偷偷補訓。NVIDIA 免費 reviewer 需確認本機 API 真正可用、必要使用權與公開資料界線，不能假裝已呼叫。
5. 建立隔離分支或目錄，來源和失敗實驗保留；讀寫前核對 SHA，避免兩個排程同時覆寫同一 `AGENTS.md`、`CURRENT_RESEARCH_STATUS.md` 或歷史 checkpoint。交接由目前 owner 或單一整合者更新；同時運行不代表共享檔案鎖。
6. 回報 `source_ref, verified_scope, test_command+result, unresolved, next_owner, commit/PR`。若無新實質成果可回報 no-new-work，不強制每次排程都產生報告或一個 Git commit。

## 私人／公開研究隔離

此 Git 倉庫僅收可公開的 SLE/VM/NN 技術證據。其他使用者私人 Agent-作者計畫與《有下文》作品以其 Project Library 及獲授權的獨立私有倉庫為主，**不跨專案鏡像**。跨領域僅可分享通用、不含私人來源的測試方法；不把私人原話轉成技術合成資料後冒充原始作者資料。

**[更新]** 相同研究問題的單一 owner、最新 PR 與證據邊界成為跨排程交接的固定步驟。**[取代]** 靠 main 的過時下一步或多個排程各自維護完整相同領域的摘要。**[原因]** P031–P035／UR1 已有多模型並行分支與多輪封存；未對齊將重做或互相覆寫。**[狀態]** 這是協作規則，不代表 runtime dispatcher／持久任務鎖已實作或九個排程已各自成功產出結果。
