# 出版與驗收紀錄

日期：2026-11-12。授權：使用者要求挑選實驗成果上Git，作為GPT與Codex的研究聯繫渠道。

## Git範圍

以`origin/main=807cd49`建立隔離工作樹與出版分支，保留原來兩個dirty checkout。新增本封存、`experiments/spiral_neural/README.md`、`docs/ai_orchestration/CODEX_EXPERIMENT_RESULTS_INDEX_20261112.md`，在原研究導覽加入入口；不改GPT的P027/P028/P030/P031設計文件，也不改倉鼠VM或parser來源。

目標是正常fast-forward發布到main；若同時有新上游提交，先保留新上游並整合本次新增檔，不force push。最終commit以Git歷史為準，本檔不預填尚未產生的commit ID。

## 選擇與公開邊界

本批只選P024–P030神經研究：報告與圖、14份可攜程式及歷史原始快照、固定split/plan/摘要、壓縮的學習曲線/逐題probe、227個合成模型checkpoint。保留失敗seed與未完成清單。

112份完整逐題trace留本機，發布其大小/SHA與重跑程式。較早P001–P023研究只在必要程式依賴處引用，不宣稱整批歷史已全部上傳。未收集API/Telegram/私人聊天、憑證、帳號/代理狀態、外部worker佇列、pip或工具cache。

發布前自動審查發現，初次遞迴匯出誤收兩份Matplotlib字型cache，包含本機目錄資訊，因此拒絕該批tree寫入；main當時未更新。已移除兩份cache、在匯出器與驗證器禁止所有cache路徑，並新增Windows/Unix home及Windows字型路徑掃描。最終發布樹從乾淨上游重新建立，不以被拒批次的暫存tree為基底；沒有請求放行機器中繼資料。原先secret pattern檢查只涵蓋憑證樣式，不能取代這次新增的機器資訊檢查。

原始程式byte保留在`source_snapshot`。可攜副本只做路徑、依賴定位和繪圖輸出目錄改動，逐項記`portability-patches.json`；原始與可攜的learning AST在排除這些filesystem節點後，14份全部一致。JSON/報告的本機根路徑改成LOCAL_WORKSPACE，manifest同時記原始與公開版本SHA。

封存目錄的`.gitattributes`停用文字換行轉換，以保留SHA在不同平台checkout後的一致性；提交後另核對Git blob內容與manifest，避免只驗到本機工作檔。

## 本輪真的執行的驗收

- 初次623個匯出artifact的SHA驗證通過；227個checkpoint用`allow_pickle=False`讀取，無object陣列、浮點有限。
- 從公開目錄依賴重算121組checkpoint指標，全部與各輪當時記錄一致；不是拿過去PASS代替本輪。
- 當輪重跑CE/局部回饋、停止規則、P029 oracle、P030二元/擴容邊界檢查。
- 另由公開`reproduce.py`完整從零重跑P030：9持續學生＋6scratch、42,990題次／213,404更新，並完成其內建等數重播。55份逐題trace SHA逐byte一致，64個checkpoint檔的所有陣列精確相同，全部科學指標一致；walltime和來源位置不要求相同。
- 14份原始/可攜程式learning AST一致；高信心secret pattern掃描及人工白名單範圍審閱通過。manifest與相對Markdown連結另於封版核對。

詳細機器結果見`publication-validation.json`。出版沒有改資料、調參或把P030失敗延長到成功；此次全重跑的結果仍是多數卡在Neg/Zero、fixed303在END階val過但test1/3。

環境：Windows、Python3.12.14、NumPy2.3.5。初始推理驗算容許浮點比較1e-10；相同環境的P030全重跑另外要求trace hash與所有checkpoint陣列精確一致。跨平台BLAS可能有差異，請同時看可觀測指標，不把時間或bitwise差異直接解讀為模型能力變化。

## 狀態與交接

本次是研究實作/證據的公開封存，不是新論文成功主張。P030轉碼器、通用輸出競賽及P031數學題庫仍未實作。[GPT交接](GPT_HANDOFF.md)列出目前失敗案例和下一步研究問題。
