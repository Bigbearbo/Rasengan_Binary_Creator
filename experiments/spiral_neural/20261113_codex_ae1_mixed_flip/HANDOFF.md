# 三類混合續訓完成交接

2026-11-13，Codex。唯一正式session20420 exit0已完成，不重啟。從PR26結果head7213cce112a8411b13dc128c49f9e88acfc9d65f的三個finalstate原樣續訓，不重跑舊實驗或初始化新學生。任務E1/E2原Q/A保留，新F1=opcode100、r1，反第一詞五資訊位、尾0不動；答案111110／111100只是字面內容，只有S停止。先讀RESULTS.md和review/post-run.json。

三模型先全部baseline，Echo兩類各900全對才有任何新optimizer。固定900payload、2700Q／24300targets每epoch，global shuffle seed+444000、40輪全課序預凍；三類均900/900兩連勝提前停，cap40不延長。L80/H64／原Adam.003不變，保留全p/m/v/birth/t/RNG／舊計數，新成本用差額。101唯一完整replay，202/303 not_planned。

事前commit6b9df16cb593c422426f6cb093a8ecfbe18d1e13／manifest a85457a3d7a6e06d7b20ad608d695a6f322a9b3daf38e714ff974fb7d7b6d218／runner3ad223a4f11d82d2c4ede86a97093d03a604bd22677c5c327936b393334037f0；21公開檔actualbyte核符後才跑，原inputs.zip7967750bytes／13成員／120課序／3parent原NPZ與公開member lineage均保留。

baseline三模型E1/E2皆900/F1皆0。混教首次三類全對5／8／6輪，兩連勝完成6／9／9輪；新增題次16200／24300／24300、新updates145800／218700／218700；最後三類每模型均900/900，全部TF正確。舊E1/E2最低101806/870、202899/851、303826/873，後續恢復；303首次全對後曾退步，不挑最好checkpoint，也不稱過程無遺忘。

新primary583200updates／12279859200trainMAC；唯一101 replay145800／3069964800，含從parent重做baseline但舊工作不重收。正式非更新baseline/probe/TF含replay合計899360F／9382123520MAC，overall wall821.947731799999秒。各train_one trajectory秒數不含baseline，scope見RESULTS。獨審一次729255F／7607588160MAC、0optimizer，8100baseline+64800epoch＝72900完整生成及72900TF全strict exact；來源／inputs／science／logs／receipt前後不變，proof逐段存盤。

整體gate先通過全部3baseline才有新optimizer，父p/m/v/birth/t/RNG精確保留，所有成本新delta另列。Native工程6updates＋32非更新F，mock97200targets／6probes不算神經更新。NVIDIA一次候選falsefinding本機否決，Gemini隔離未解skip，完整處置在EXTERNAL_REVIEW。所有實際science／父bytes／每輪state／錯誤／truth／replay與獨審封存，未存的rawpertargetloss、中間gradient和獨立replay state副本不冒稱再驗算。

本批完成後沒有待跑的舊NN；r3/r4、Flip2、不同N或新bank均未凍結／訓練／探測。現有結論是同900組固定bank下三類學習與保持，不是一般算法、內部router、保留題泛化或混教因果優勢。下一輪先核Git明確owner／branch／SHA，再另立課程；不改他人主導航、不自動合併PR28。
