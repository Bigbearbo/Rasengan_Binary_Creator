# Codex 實測結果入口（2026-11-12）

使用者指定Git作為GPT/Codex目前聯繫方式。此頁連結**真正執行的神經網路研究**；同資料夾其他P027/P028/P030/P031文件仍可能是計畫，請勿混用完成狀態。

- [P024–P030 可重跑成果與證據](../../experiments/spiral_neural/20261112_p024_p030/README.md)
- [給GPT的研究交接與未完成項目](../../experiments/spiral_neural/20261112_p024_p030/GPT_HANDOFF.md)
- [P030第一批實測：純01與持續學習](../../experiments/spiral_neural/20261112_p024_p030/reports/P030-純二元動態網路第一批結果-2026-11-12.md)
- [P029單向升階](../../experiments/spiral_neural/20261112_p024_p030/reports/P029-論文四逐階不退回實測-2026-11-12.md)
- [出版範圍、版本與驗收](../../experiments/spiral_neural/20261112_p024_p030/PUBLICATION_RECORD.md)

本批保存程式原始快照、可攜副本、精簡JSON/CSV、圖與checkpoint；完整逐題trace留本機，以SHA清單供重跑比對。無私人聊天、帳號狀態、Telegram資料或憑證。

P030第一批不是完整P030成功：多數學生在Neg/Zero未教值失敗，一個END驗證過關學生test仍1/3。後接神經轉碼器與P031多類數學比較尚未實作，請先讀交接再規劃。

## P032 已實跑：容量 × 教學比例（最新研究結果）

- [P032 結果與限制](../../experiments/spiral_neural/20261112_p032/P032-容量與教學比例實測結果-2026-11-12.md)
- [重跑入口、機器證據與checkpoint](../../experiments/spiral_neural/20261112_p032/README.md)

已完成D：37個舊checkpoint、456列完整真值表；A：兩組split×三seed×H72/H128×70:30/50:50共24條Neg分支，完整重播一致。各格已教題72/72，test0/12、1/12、1/12、0/12；原本會答的Echo test由24/24降到2/24，未支持直接加寬，B中途成長未執行。NVIDIA真實唯讀審查1次cost0，錯誤推論有逐項駁回。

P031共用題庫第一批另外保存於[PR5](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/5)，未混入P032教材；國小加法、神經翻譯、升階儀式與真VM解題仍待做。
