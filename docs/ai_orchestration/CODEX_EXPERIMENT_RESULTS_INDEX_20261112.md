# Codex 實測結果入口（2026-11-12）

使用者指定Git作為GPT/Codex目前聯繫方式。此頁連結**真正執行的神經網路研究**；同資料夾其他P027/P028/P030/P031文件仍可能是計畫，請勿混用完成狀態。

- [P024–P030 可重跑成果與證據](../../experiments/spiral_neural/20261112_p024_p030/README.md)
- [給GPT的研究交接與未完成項目](../../experiments/spiral_neural/20261112_p024_p030/GPT_HANDOFF.md)
- [P030第一批實測：純01與持續學習](../../experiments/spiral_neural/20261112_p024_p030/reports/P030-純二元動態網路第一批結果-2026-11-12.md)
- [P029單向升階](../../experiments/spiral_neural/20261112_p024_p030/reports/P029-論文四逐階不退回實測-2026-11-12.md)
- [出版範圍、版本與驗收](../../experiments/spiral_neural/20261112_p024_p030/PUBLICATION_RECORD.md)

本批保存程式原始快照、可攜副本、精簡JSON/CSV、圖與checkpoint；完整逐題trace留本機，以SHA清單供重跑比對。無私人聊天、帳號狀態、Telegram資料或憑證。

P030第一批不是完整P030成功：多數學生在Neg/Zero未教值失敗，一個END驗證過關學生test仍1/3。後接神經轉碼器與P031多類數學比較尚未實作，請先讀交接再規劃。

## P033 已實跑：覆蓋、從頭混教與Echo-only控制

- [P033結果與限制](../../experiments/spiral_neural/20261112_p033/P033-覆蓋與從頭混教實測結果-2026-11-12.md)
- [重跑入口／公開證據](../../experiments/spiral_neural/20261112_p033/README.md)

D：36舊checkpoint與4320條件probe；A＋從頭時序主試30條，另12條Echo-only控制，均完整重播。從頭混教把已教Echo保留由分段1/36提高至36/36，但未教val+test0/24。Echo-only等總題次保住原test12/12，Neg70僅1/12；曝光差異明列。補齊pairwise覆蓋沒有穩定修復泛化。原生01的表示對照、V1/V2、新算符仍未做。P032/PR6與P031/PR5歷史成果各自保留。
