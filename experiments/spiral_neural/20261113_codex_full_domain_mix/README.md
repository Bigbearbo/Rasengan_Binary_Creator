# 完整8-bit數值域 Echo／Neg 混教

固定原 P030 Model AST、H69，因 Q14／答案9 而用最小 L23，共3453參數。獨立數值 profile nop2/nd8，op0複製8資訊位、op1只翻8資訊位，尾0與外部STOP照常。0..255全部合法、兩op共512題全部訓練，沒有val／heldout洞，也不是AE1的END／UP控制profile。

每epoch洗牌全512題，5120target updates。最多40epoch／204800updates／1,427,251,200 training denseMAC／學生。每epoch末只用完整訓練全集greedy生成判定：兩op各256/256含STOP連續兩epoch才停，失敗重置streak，否則40停。不依分數重生教材或延長。

先執行 `--engineering --source ORIGINAL_P030.py --out NEW_CHECKS`，只做有界合成native更新與mock流程驗收。`--prepare --source ORIGINAL_P030.py --out NEW_PREREG` 凍結完整source、plan、512Q pool、三完整初態及每seed全部40×512×(op,value)課序。兩者均不啟動正式學生、不讀新分數。文字UTF-8/LF、SHA依原bytes。

root／reviewer核准並完成Git事前提交後，才能一次 `--execute --manifest NEW_PREREG/manifest.json --approved-manifest-sha SHA --prereg-commit COMMIT --out NEW_SCIENCE`。入口只依本包、既有Python／NumPy，不靠原機器路徑、不操作Git、不呼外部模型、不自動retry。

每epoch保存fullstate、loss／更新前正確數、逐target `[inputID,position,pred,loss]` canonical digest及全部512生成tokens／分數／streak。沒有逐target完整state hash或IO。僅seed101完整獨立target-loop重播，核對每epoch digest、fullstate、probe與停止；202／303明列未計畫replay。全部primary及該replay完成後，才算final全512題完整TF／logits／CE，重用最後一epoch的自由生成。

固定16action生成wrapper檢查context overflow，不使用old generate8、不依真答案長度截斷、不補STOP。train每target6969MAC、每epoch35,681,280；推論每forward3381MAC。實際花費、epoch probe、seed101 replay、final TF、array69060bytes／學生、walltime分開報，保留停止／失敗與未通過結果。

這是擴大8-bit及必要window的完整有限範圍學習，與前輪同時改變題域／context，不能當純題數因果對照；沒有盲測或未見運算元泛化主張，也不證明無界算法、內部router或神經升階。
