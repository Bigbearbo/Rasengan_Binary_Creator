# Pro AE1逐檔變更

相對基底 `685c6f92d9e5a335a2f2a7193d9b501918d90b00`。舊實驗科學碼及checkpoint未改；本輪先提交凍結，再提交結果。

| 檔案（repository相對路徑） | 用途 |
|---|---|
| `docs/ai_orchestration/CURRENT_RESEARCH_STATUS.md` | 更新最新AE1完成狀態、界線及下一候選 |
| `docs/ai_orchestration/PRO_ADVANCED_ECHO_RESULTS_20261113.md` | 完整結果、設計限制、驗收成本、流程觀察與下一候選 |
| `docs/ai_orchestration/RESEARCH_HANDOFF.md` | 提供Codex新交接卡，保留明確標記的舊時點歷史 |
| `docs/spiral_language_research_index.md` | 新增最新實測與完整證據入口 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/.gitignore` | 忽略已在公開ZIP完整保存的本地展開副本 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/CHANGED_FILES.md` | 相對原Pro PR16基底逐檔變更說明 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/README.md` | 本輪設計、已完成摘要與重現／還原入口 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/audit_results.py` | 不import learner的468題raw-array獨立推論與來源／成本核對 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/data_checks.json` | 兩次純資料建置的覆蓋、負控、hash與一致性結果 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/dataset.json.gz` | 完整raw Q/A、payload分組、target池及曝光帳的無損壓縮檔 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/dataset.py` | 確定性分組題庫、曝光帳與程式檢查產生器 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/delivery_checks.json` | 凍結bytes、主數字、106本地連結與66檔乾淨還原驗收 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/design_history/preflight_01.json` | 前次0-NN工程驗收紀錄，保留事前修訂痕跡 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/design_history/preflight_02.json` | 前次0-NN工程驗收紀錄，保留事前修訂痕跡 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/evaluation_stdout.log` | 當輪18checkpoint離線評估的進度輸出 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/evaluation_summary.json` | 全部18checkpoint的原始評分摘要及推論帳 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/evidence/primary_seed101.zip` | 指定primary或replay的全部phase狀態／epoch紀錄／摘要／stdout；primary另含六份完整評分 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/evidence/primary_seed202.zip` | 指定primary或replay的全部phase狀態／epoch紀錄／摘要／stdout；primary另含六份完整評分 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/evidence/primary_seed303.zip` | 指定primary或replay的全部phase狀態／epoch紀錄／摘要／stdout；primary另含六份完整評分 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/evidence/replay_seed101.zip` | 指定primary或replay的全部phase狀態／epoch紀錄／摘要／stdout；primary另含六份完整評分 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/evidence_manifest.json` | 四ZIP與66個成員的大小、SHA與驗證結果 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/execution_record.json` | 正式命令、時序、執行方式與實際資源 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/export_results.py` | 純紀錄彙整、門檻、已教範圍、逐ID保留和曝光子群 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/frozen/initial_seed101.npz` | 事前公開的指定seed完整隨機初態，p/m/v/birth/t/RNG與成本0 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/frozen/initial_seed202.npz` | 事前公開的指定seed完整隨機初態，p/m/v/birth/t/RNG與成本0 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/frozen/initial_seed303.npz` | 事前公開的指定seed完整隨機初態，p/m/v/birth/t/RNG與成本0 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/frozen/schedule_seed101.npz` | 事前公開的指定seed五phase／56epoch完整target順序 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/frozen/schedule_seed202.npz` | 事前公開的指定seed五phase／56epoch完整target順序 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/frozen/schedule_seed303.npz` | 事前公開的指定seed五phase／56epoch完整target順序 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/frozen_manifest.json` | 科學來源、資料、初態、精確課序的事前SHA清單 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/independent_pre_run.json` | 獨立核對來源、三初態、168epoch完整排列與預算 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/independent_result_review.json` | 實際獨立驗收PASS、每題對照與精確新增成本 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/learner.py` | 原P030模型的純01生成、完整state與評分介面；科學碼不改 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/package_evidence.py` | 四證據ZIP打包、逐成員驗證及拒絕覆蓋不同證據的還原 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/preflight.py` | target路由、純宿主STOP/cap及初態序列化工程驗收 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/preflight_checks.json` | 最後一次事前工程驗收；0 NN/optimizer |
| `experiments/spiral_neural/20261113_pro_ae1_learning/protocol.json` | 事前固定問題、資料、模型、預算與判準 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/replay_check.json` | 唯一指定seed101重播的五端點／epoch一致性核對 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/results_summary.json` | 全部三seed／六測點的核實摘要、判準與成本 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/run_trial.py` | 事前準備、來源守門、固定預算訓練／重播和離線評估 |
| `experiments/spiral_neural/20261113_pro_ae1_learning/workflow_observations.json` | 兩階段時間、設計修正、正式變更／返工與效率界線 |
