# 多 Agent／研究排程：Git 實驗交接與新舊版本判斷

檢查日期：2026-11-13。狀態：**公開技術協作協議**；這不是排程的真正執行設定、也不能自動啟動本機 Codex / ChatGPT Pro / NVIDIA。此文件只引用本公開倉庫的已公開技術成果，**不保存私人排程內容、聊天、Library 原稿或 API 金鑰**。

## 1. 觀察到的研究狀態：不能只讀 main

本輪核對 GitHub open PR（2026-11-13）：

| 類別 | PR／分支 | 內容與驗證界線 |
| --- | --- | --- |
| P031 共用SLE題庫 | [PR #5](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/5)／`codex/p031-shared-math-bank-20261112` | 封存1,342個合成案例，17/17教材/介面驗證；**尚不是真VM學會數學** |
| P032 | [PR #6](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/6) | 網路加寬與後期混教試驗已執行，不穩定改善 heldout |
| P033 | [PR #7](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/7) | 從頭混教與bit pair覆蓋對照已執行；**不能再當待跑** |
| Pro 後續審查 | [PR #8](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/8) → main | 獨立審查、下一輪事前設計與parser修復 |
| P034 | [PR #9](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/9) → PR #8 | E900與近等參數 attention 已執行 |
| P035 | [PR #10](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/10) → PR #9 | 編碼 × 容量時序，已執行12學生，heldout仍差 |
| Pro UR1 codec | [PR #11](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/11) → PR #10 | 帶位置的升階通知設計與有界 codec 測試；非NN學習成功 |
| Pro UR1 neural protocol | [PR #12](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/12) → PR #11 | 最新查核的正式訓練**前置凍結／工程驗收**；當輪主幹記載正式神經訓練尚未執行 |

**最有用的現況入口（位於 PR #12 工作分支，不是 main）：**
- [當前研究交接卡](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/pro/notice-learning-20261113/docs/ai_orchestration/RESEARCH_HANDOFF.md)
- [當前研究狀態／結果與未測邊界](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/pro/notice-learning-20261113/docs/ai_orchestration/CURRENT_RESEARCH_STATUS.md)

這些鏈結指向已存在的工作分支，不保證永遠最新。**每次執行先重新列 open/merged PR、base/head/commit SHA、分支與測試報告，選當下真正有固定證據的最新入口**。PR #8→#9→#10→#11→#12 為有依賴的堆疊 PR，不可按 PR 數字直接全併 main，也不因某一 PR mergeable 就推斷整串無衝突。不同 workstream（VM、NN、parser、題庫）不可假裝它們已合成同一正式 VM。

## 2. 閱讀／工作／回交的最小共同契約

每次研究或排程回合：
1. **先看自己領域**：同一個研究問題先查 `AGENTS.md`、本檔、實際相關的 PR branch `RESEARCH_HANDOFF.md`／`CURRENT_RESEARCH_STATUS.md`、以及原始實驗 README／manifest／tests。不要從設計文件中的「下一步」直接判定還沒跑。別把上一輪舊 head 當最新。
2. **一次只領一個可實驗問題**：定義 `work_id, project, goal, owner, source_ref/sha, parent_pr, data/profile, status, hypothesis, acceptance, allowed_write_paths, next_test`。先搜索是否已有人在同一 PR 或 Issue 進行相同工作。有同目標且無新證據，報 no-new-work，不做空實驗。
3. **先固定教材與規格**，再訓練。新訓練應保存 seed、split、格式、題數、更新數、資源計算、比較組及預定停止；失敗資料不刪，別在看 test 後補更多預算冒稱盲測。
4. **區分資訊與實作**：U作者方向，F原始程式及報告，T真正在本輪執行的程式測試，A模型推測／設計。NVIDIA/其他 reviewer 的候選意見要驗證後才能變成 confirmed；scripted parser、課程 oracle 不能冒充小NN/VM自主學會。
5. **只寫自己負責的目錄／分支**：不要在不同模型同時修改同一個主支索引；實驗證據優先獨立資料夾，最後由主整合者統一更新 `CURRENT_RESEARCH_STATUS.md` 和交接卡。合併前再核對 head/base、commit、測試；不因排程執行就自動合併、部署、改 repo visibility。
6. **短交接比長摘要有用**：固定摘要附上 `artifact_path, sha, exact test command/result, acceptance, findings, failures, unresolved, next owner/experiment`，連到原始證據。若未成功寫 Git，不得宣稱已分享；沒有真正新成果不要更新「最新」標籤。

## 3. 領域與公開界線

- 本 repository 是**公開的螺旋語／倉鼠世界**技術資料，只能進去敏公開報告、程式、測試與原生合法詞碼；不能直接把私人 ChatGPT Library、原始聊天、金鑰、營利/作者專案內部資料鏡像進來。
- 其他私人作品與 AI 試讀在**獨立的私人協作空間**處理，依各自的存取授權與資料保護規則執行；本站不得搬作品、私人作者原話或私人排程設定。能共用的只是**不含私人來源的研究方法、測試工具或協作原則**，不是把兩個研究主體混成一項成果。
- 其他 Agent／作者自主研究若沒有相符且已授權的 Git 去處，應留私人 Project Library，之後再取得具體同步授權；不為「Git 分享」而硬塞本公開倉庫。

## 4. 記憶與額度

公開權威記憶採 Git + 小型 Markdown 索引 + 有版本的證據連結；本機 Codex worker 的 SQLite/FTS5 執行歷程、任務佇列、API用量等保持**本機私有**（見 `CODEX_MULTI_AGENT_MEMORY_PLAN_20261112.md`），不能假設 dispatcher 已存在。把已驗證假說與 reviewer 候選分層，避免反覆重讀大型上下文。

NVIDIA 只作有界審查、反例與題庫拆解，Codex/Pro 實際承擔驗證。每次回報 `delegated / skipped_reason, model_id, actual_calls, accepted/rejected, source ref`；不要為用滿免費額度派虛構任務。若模型、Git或工具失聯，報告限制，不冒稱已運行。

**[更新]** 將即時分支／PR證據入口視為最新研究狀態，並由各工作流在已有手冊之上共享本協議。**[取代]** 把 main 過時的 P033 下一步當作整個項目的現狀，或假定草稿 PR 已整合。**[原因]** 已有依賴 PR #8→#12，並有跨模型各自提交的證據。**[狀態]** GitHub 可見狀態核對信心高；未列出的本機未推送改動不可推定不存在。
