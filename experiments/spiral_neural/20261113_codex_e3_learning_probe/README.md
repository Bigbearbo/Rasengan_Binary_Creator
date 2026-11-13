# E3 CPU：一輪已學進新題，仍會忘少量舊題

2026-11-13，Codex。先設計並Git封存，再執行；正式與唯一獨立驗收皆完成。主要零舊題流失門檻not_met，工程與數值驗收PASS。

|Seed|0.001新E3/900|舊題流失|0.003新E3/900|舊題流失|
|---|---:|---:|---:|---:|
|101|229|3|240|23|
|202|54|2|76|32|
|303|182|8|33|74|

冷E3都是0/900，舊四類各900全對。兩臂同一完整起點/課序/900payload，僅改學習率，各53100逐bit更新/一輪；總318600更新，原NumPy CPU正式命令約7分40秒。低η三seed均較少忘舊，新題表現依seed不同；不宣稱E3已學會或低η普遍最佳。

獨立raw NumPy重算40500自由生成題與369900TF位置，825965forward、0optimizer，strict exact。全90science/33NPZ/27proof/事前24檔快照與成本完整保存；沒有完整optimizer重播。

先讀[RESULTS.md](RESULTS.md)、[HANDOFF.md](HANDOFF.md)，事前設計原文見[DESIGN.md](DESIGN.md)與[protocol.json](protocol.json)。原24檔在preregistration.zip，publication-manifest.json列完整archive成員。公開機器個人路徑副本處理見public-redactions.json。
