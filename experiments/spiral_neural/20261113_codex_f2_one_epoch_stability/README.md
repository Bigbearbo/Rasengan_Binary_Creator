# F2首次全對後：降低一步學習率的CPU配對實驗

2026-11-13，Codex，事前設計；尚未執行正式新推論／訓練。

從PR33三個原學生各自首次四類各900全對的完整state作新分支，只教既有凍結課序的下一輪：101的19→20、202的22→23、303的19→20。新分支只把Adam步幅0.003改為0.001，其餘模型／梯度／float32參數與FP64部分／clip1／birth-age／p-m-v-t-RNG-events及原900bank全部保留。使用原NumPy CPU，不切換GPU或Numba。

歷史原步幅下一輪已完整公開，從保存tokens重算流失7／5／52題。新分支每人恰36000逐bit更新，合計108000，training dense MAC 2274048000；固定一輪，不追到滿分或依結果換學習率。新全3先核baseline四類全對，之後才任何optimizer。

主要假說是三個seed的新流失總題數都嚴格少於各自歷史控制；持平不算支持。另保存每類整串、逐詞／資訊位／尾零／STOP、首錯與逐QID兩臂正錯交集，不能用pooled總分掩蓋seed或題型退步。

此起點選擇來自已查看的舊結果，歷史控制不是新跑學生。它只檢驗這三個已會state接著一次教學的局部影響，不代表新教材學習速度、未見題泛化或長期最佳學習率。原PR33正式終點保持原樣；這是另立受控分支，語法／編碼寬度未降階。E3/E4留待後續。

父結果commit f9d41eb28f067a222682e02c85c7371297bddde9，pubmanifest SHA193d2c49ccf052c55db808014cb837f80204789fc93388fd3955c4205720e9a4。正式前需source/input凍結、可攜gate、Git actual-byte回讀。最後以獨立raw NumPy核baseline、新臂、歷史control全部輸出及新臂TF；完整optimizer訓練重播事前設為0，不宣稱未保存的中間gradient／逐target loss軌跡已重建。
