# 固定容量 early／late 混教

本實驗固定原 P030 Model、L13/H69、2073參數及三個配對seed。每臂2400題／12000 updates，Echo／Neg各1200、每個(op,value)各200。只改前1200題的op時序；每op完整值序列、初態、最後1200題逐項相同。

先以 `--engineering --source ORIGINAL_P030.py --out NEW_CHECKS` 跑有界合成驗收，再以 `--prepare --source ORIGINAL_P030.py --out NEW_PREREG` 保存完整 source、plan、三份初始完整state與六份2400題課序的ZIP／manifest／source-freeze。兩入口都不訓練正式seed、不讀新學生分數；新文字明確UTF-8/LF。

root／reviewer核准來源與輸入，並完成Git事前提交後，才允許一次 `--execute --manifest NEW_PREREG/manifest.json --approved-manifest-sha SHA --prereg-commit COMMIT --out NEW_SCIENCE`。正式入口只依本包、NumPy與Python，不依原機器工作路徑，也不操作Git或外部模型。

先完成六primary，再六完整重播，最後才離線測四個state點的全部16個合法Q。primary使用原Model.lesson；重播獨立逐target用原step，完整trace及state/Adam/birth/RNG/counters核對。訓練途中只有state保存，沒有分數或自動延長。

5／6早已曝光，只列診斷；不是新盲測。合法opcode-only probe用完整Q、空A前綴，重用TF第一輸出logits，不能據此宣稱識別了內部router。相等training denseMAC不等於相等推論／總成本。所有seed、失敗與停止狀態保留。
