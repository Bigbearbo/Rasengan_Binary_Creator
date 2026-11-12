# 完整八位題域學習完成

2026-11-13，Asia/Taipei。Codex已完成三個新學生與唯一指定seed101完整重播；formal session77220 exit0，不重啟。

任務來自使用者要求更多不同題目、不要在固定長度內挖洞。固定nop2/nd8數值profile：op0Echo、op1Neg，八資訊位加尾零，0..255全部教，共512不同Q；每輪全題洗牌各一次，沒有內域heldout。Q14、答案9、STOP前23，原P030 Model AST／H69／Adam不改，固定L23、3453參數；這不是AE1或只改題數的因果對照。

三seed101/202/303最後Echo、Neg均各256/256含尾零與STOP，連2個epoch全對而在26／23／18輪提前停。累計題次13,312／11,776／9,216，target更新133,120／117,760／92,160。首次單epoch全對20／22／17；101有退步，因此不能把首次全對當穩定過關，也沒跑滿40cap。

Primary343040updates／2390645760training MAC；seed101 replay另133120／927713280。每輪probe及final TF另列，正式含重播與I/O共245.9613505秒。只seed101完整replay，202／303明確not_planned。每epoch完整state/probe/trace digest/停止判斷精確相符，不宣稱保存或獨算所有中間gradient。

獨立NumPy一次重算67epoch×512＝34304free、15360final TF，並核73science NPZ、三frozen init、120預生成排列、全部score／streak／stop／cost，全部一致。Audit另358400forward／1211750400MAC、0optimizer，metadata先驗且數值proof逐epoch持久化。主入口RESULTS.md、README.md及independent-result-review.json。

事前commit `1d6ab7fd7fbb75525886226b10b1ed0a744ad9ff`，manifest `dabdb58a54ffd93afa350f19876a53550bcfcfd6de9b5199ee8b3b26d2b8d658`，driver `9c100c1b8d6e9d1aca4acfc0f5a89d1a4716286aae1fae44692cbb5d0066593e`。三份完整初態／40輪全課序／512pool／source及plan已在Git先公開，formal開始前13檔byte回讀。固定源自PR20 head3fe2a9a，PR24是本輪分支入口，不自動merge。

所有224science檔、76公開NPZ、67輪全輸出、全部中途失敗與最後truth保留。完整範圍擬合成功可照實報告；不稱盲測、無界copy／flip、內部router、長度外推或AE1預訓練成功。下一棒不要拿更長詞L23越界當泛化失敗（n9需25），也不要把本次寬度／窗口／更新的同步變化只歸因題量。

已讀並行PR21的AE1算術診斷與PR23的離線PR-DAG工程metadata；沒有重跑、採用其候選或改其分支。舊P030/P033/UR1/AE1/PR20已完成，不列pending。Pro的主導航仍按原分支保留，接續時需核對明確owner／branch／SHA，不能只取最大PR號。

外部round FULL-DOMAIN-MIX-20261113：NVIDIA一次公開synthetic方法候選、cost0，僅scope提醒且無科學結果接受；Gemini既有工具隔離未驗證而skip，未重送。沒有背景排程、無限重試或新增通知／VM工作。
