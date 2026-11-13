# 視窗GPT：E3 進度審查、新組合實測與下一個決策

日期：2026-11-14（台北）。作者：視窗GPT及受指派的獨立審查代理。本輪承接 Codex PR49 `915219a4a787ea1452b798104d2158a6d8c82410`，另行審查獨立研究 PR55 `e745264ba8da233486b4632e69b093ac2833d7fb`。兩條模型歷史分開。本目錄只新增研究材料，不改舊實驗、權重、教材或停止規則；沒有新訓練。

## 結論

Codex 主線已完成 F2 教學及一個降步幅穩定性對照，E3 已續教至合計九輪。三個正式終點的 E3 為 900／879／897，舊四類為 3599／3600／3599；五類連續兩輪全對的原門檻仍未達。

本輪另先公開凍結規格，再以三個正式終點做第三詞／第四詞的 2×2 唯讀介入。101 號學生在三組新題各900/900，合計2700/2700；202為2633/2700，303為2681/2700。這已是原題庫以外、有限的新組合遷移證據，不能繼續只說「尚未測過新組合」，也不能把另一條 PR55 的新詞失敗套到主線。

[更新] 主線除了已教題擬合，現在已有第三詞變更及無關第四詞變更下的直接遷移證據，101在本次全部新題完全正確。[取代] 上輪僅確認固定900組題庫，尚無本主線的新組合推論結果。[原因] 凍結規格後實際產生8100筆新題回答，另2700筆原題回答精確重現封存輸出；三個完整模型狀態未變。[狀態] 本次有限介入結果信心高；任意組合、任意長度的通用複製仍未證明。

下一個正式訓練建議是從三個實際終點做固定小預算的 `0.001 vs 0.0003` 步幅配對對照，先不加入E4、不換架構。這是 A 候選，未執行；詳細規格及需要討論的目標取捨在 [NEXT_DECISIONS.md](NEXT_DECISIONS.md) 和 [機器可讀候選](next_training_candidate.json)。

## 已完成的 Codex 主線

E1/E2/E3代表回音前1/2/3詞；F1/F2代表翻轉前1/2詞的資訊位，每詞尾0保留，S是外部停止動作。每一類有900個固定四詞payload；a/b涵蓋30×30，c/d每組固定，並非30⁴全域。

| 階段 | 實際結果 | 應保留的界線 |
|---|---|---|
| [PR33](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/33) F2混教 | 三個學生都曾四類3600全對；只有101通過連兩輪 | 202/303的cap40正式失敗終點保留 |
| [PR43](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/43) F2步幅 | 首次全對state下一輪，0.001三個都保持3600全對；歷史0.003流失7/5/52題 | 起點是PR33首次全對的19/22/19輪，並非PR33正式終點；只驗下一輪穩定性 |
| [PR47](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/47) E3一輪 | 低步幅E3 229/54/182，舊錯3/2/8；高步幅E3 240/76/33，舊錯23/32/74 | 新增能力與舊題零流失未同時成立；沒有同更新量的純舊題第三臂，不能把全部遺忘單獨歸因E3內容 |
| [PR49](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/49) 低步幅追加8輪 | E3 900/879/897，五類總分4499/4479/4496，各4500題 | 三個都在cap8停止，從未有五類全對輪次；未取代正式終點為最佳checkpoint |

固定原報告：[PR49 RESULTS](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/915219a4a787ea1452b798104d2158a6d8c82410/experiments/spiral_neural/20261113_codex_e3_continuation/RESULTS.md)。PR49在台北11月14日00:43:33更新；PR55在04:53:04更新。本輪來源快照見 [source_snapshot.json](source_snapshot.json)，只代表可見Git狀態。

本輪獨立以0 NN方式核對17個manifest列出的公開檔及272個ZIP成員，獨立解碼4500題標籤、重建3×8課序、檢查21個沿用函數AST、完整state承接及全部24個epoch銜接，重算121500筆封存生成的分數、核對159300筆已存TF記錄。全部通過，未發現推翻主線結果的具體錯誤。這不是重訓或重建中間gradient/logits。程式與結果：[mainline_record_audit.py](mainline_record_audit.py)、[mainline_record_audit.json](mainline_record_audit.json)。

殘差定位比總分更有用：101僅F2一題先錯第二詞；202的21個E3錯題先錯第三詞；303的三個E3錯題及一個F2錯題都先錯第二詞。303的三個E3錯題在正確前綴TF下也僅第二詞有三個錯誤target，第三詞沒有TF錯誤；自由生成後三題卻跑到cap32。因此不能一概診斷為「第三詞學不會」或容量不足。舊13錯題全部恢復，但另產生2個新F2錯題，淨改善不等於零新遺忘。

## 本輪真正執行的唯讀 E3 檢查

事前公開commit：[898a385b33cf25ca6cd75f34fddf6b09812e3bfb](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/898a385b33cf25ca6cd75f34fddf6b09812e3bfb)，台北05:04:53。重新fetch並逐byte比對程式及protocol後，05:05:27才開始唯一一次實際推論。來源是三個PR49實際final-after-TF完整狀態，沒有挑seed或最佳checkpoint。

保留a/b。以合法ID的 `(值+1)%30` 改c或d：c是E3應輸出的第三詞，因此正解第三詞應變；d在三詞回音之外，因此正解不變。這不是單bit介入，加一遇進位可能改多個資訊位。兩個改c的cell共用900個新的(a,b,c)組合，在兩種d上下文各測一次；只改d的cell保留(a,b,c)，只更換無關上下文。全部2700個修改後Q均不在原4500個訓練Q中；三個學生合計8100筆新回答。

| 完整答案含S正確／900 | 101 | 202 | 303 |
|---|---:|---:|---:|
| 原題庫c0/d0 | 900 | 879 | 897 |
| 只改第三詞c+1 | 900 | 879 | 893 |
| 只改第四詞d+1 | 900 | 876 | 895 |
| 第三、第四詞都改 | 900 | 878 | 893 |

101在c變更時，900組都改對第三詞，前兩詞全部保持正確；應改的1783個第三詞資訊bit也全部跟隨正確。只改d時900組完整輸出全部不變且全對，兩者同改亦全對。這直接排除「只依a/b回放原本E3答案、完全不讀c」作為本次101行為的完整解釋。未見數值並不是測試變因：仍是0..29的已見值，測的是新組合與上下文。

202只改d，總分879→876，但有37個完整輸出改變：原本正確變錯20題、原本錯誤變對17題，兩邊都正確859題。863個不變輸出包含4個共同錯答。303只改d有4個輸出改變。這些反例保留，不能只拿平均高分宣稱所有學生已完全忽略第四詞，也不能用總分差3寫成只有3題受影響。

新推論先要求2700/2700原題輸出與封存逐串、cap/context flags、exact指標一致，才進入介入。這個2700是「精確重現封存」數，不是原題正確數；原題合計正確2676。其後用獨立raw NumPy、自己的生成前綴、cap32、外部S，不提供正確答案或答案長度給模型。完整p/m/v/birth/t/RNG/events/counters設為唯讀，來源與完整狀態執行前後雜湊相同。

實際總計10800個完整回答、205448次forward，其中基線51339、新介入154109；dense MAC為2143233536。推論主段約3.65秒，不包含研究、下載、稽核與發布。optimizer更新0、手工改權重0。所有原始回答保存於 [probe_evidence.zip](probe_evidence.zip)；[probe_summary.json](probe_summary.json)提供各詞、STOP、首錯及成對指標。只做這一次推論，不以結果改規格再重跑。

另一位代理以0NN方式獨立重新計分全部10800個保存答案、所有成對指標，核對凍結時間／bytes、來源state雜湊及成本，全部通過；這不是第二次神經推論。程式與結果：[e3_probe_record_audit.py](e3_probe_record_audit.py)、[e3_probe_record_audit.json](e3_probe_record_audit.json)。

以上支持有限範圍的新組合遷移，未窮舉所有c/d，未測E4或新詞寬，沒有建立研究者全盲外部測試，也未識別模型內部唯一機制。原五類連兩輪全對門檻依然未達。

## 另一條 PR55 為何不能直接套用

[PR55公開結果](https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/e745264ba8da233486b4632e69b093ac2833d7fb/experiments/spiral_neural/20261114_scheduled_weight_tying/RESULTS.md)報告六個新學生，詞編碼器共享／不共享兩臂的新第一詞均0/84，次要新第二詞17/84對1/84，主要門檻FAIL。這是其他研究者的T，本輪沒有重播那些權重。公開Git缺其checkpoint及raw完整包；有限附件查找未取得companion，不能稱附件不存在或以重新訓練代替。

本輪從公開程式獨立重建教材與156題manifest，匹配原凍結SHA：每epoch136次呈現、112個不同Q、1408個教師target。第一答案詞的「位值8」為1的教學次數是0/136；第二答案詞只有2/76。第一詞中位值4與2同時為1亦為0次，第二詞有6次。主要28題有20題需要第一詞bit8=1，另8題a6/7需要第一詞4與2同時為1。測試確實在考跨位置及組合遷移，失敗本身合理；它不能單獨定位為編碼器或容量失敗，更不能把0/28都只歸因bit8。

PR55程式先按固定offset對齊四個六bit詞，提供r欄位及從prefix長度算出的輸出位置onehot；它不使用已生成prefix的內容。兩臂的前端一致，差異是詞編碼器權重共享；後面的四詞向量仍串接，輸出解碼器未因而具備端到端詞位共用。外部輸入仍是01，但詞界與cursor並非學生自行從任意bitstream學到。這是已揭露的結構先驗，兩臂內比較仍有意義，與原主線MLP不是同一架構或等預算歷史A/B。

詳細新靜態證據及限制：[PR55_FINDINGS.md](PR55_FINDINGS.md)、[pr55_static_audit.json](pr55_static_audit.json)、[pr55_static_audit.py](pr55_static_audit.py)。`seen_baseline`48題只有16題是精確訓練Q，其餘32是已見值的新組合，應稱已見詞基準。未把其他研究者所報936/936回放冒稱本輪重跑。

## 重現、歸屬與檔案範圍

本輪U是使用者要求追最新進度、提出下一個建議與待討論決策。F是固定Git原件及先前報告。T包括本輪封存計分／教材重建與新唯讀E3推論；Codex先前訓練和PR55其他研究者訓練各自保留歸屬。A是下一步步幅對照及研究政策建議。

可在含有PR49來源與本目錄的checkout中執行唯讀檢查，輸出需為不存在的新位置：

```sh
python experiments/spiral_neural/20261114_window_progress_review/mainline_record_audit.py --repo . --output /tmp/new-mainline-audit.json
python experiments/spiral_neural/20261114_window_progress_review/e3_composition_probe.py execute --repo-root . --out /tmp/new-e3-probe --frozen-commit 898a385b33cf25ca6cd75f34fddf6b09812e3bfb
```

第二行會重做推論；閱讀本次結果不需要再跑。本輪實際只執行一次。PR55靜態稽核另需e745264的checkout，用 `pr55_static_audit.py --repo /path/to/pr55-checkout --output /tmp/new-pr55-audit.json`；不需要其權重或PyTorch。

新規格在凍結前經獨立0NN審查；修正d-only措辭並加上拒絕`python -O`的guard，再重新產生protocol及公開。PR55靜態分析自己的初版預期數20誤寫，assertion攔下後改成實際2；透明紀錄在JSON，並非上游bug。所有舊研究檔與state原樣保留，沒有merge、桌面Codex啟動或新正式訓練。

NVIDIA派工帳：task=`E3-next-step-readonly-review`，status=`skipped_unavailable`，可呼叫OpenRouter/NVIDIA工具未提供，實際呼叫0；三個原生協作代理的稽核、設計與實作不冒稱NVIDIA。Gemini呼叫0。
