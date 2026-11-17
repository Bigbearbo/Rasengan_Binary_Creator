# 成熟特徵轉移：事後唯讀分析

新增訓練 0、神經 forward 0、來源推論 0。以下只整理已保存的結果。

主要驗收仍看事前定義的 validation whole-answer 指標；不以 test 或事後 pair 指標替換。

|條件|Seed|Train 正確|Val 正確|Test 正確|首次 Val95|連續兩點 Val95|Val AUC|全部 variants 都對的無序 pair|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|mature_hidden|101|3251/8240|839/2096|1192/3120|None|None|0.3860|58/396|
|mature_hidden|202|3145/8240|729/2096|1133/3120|None|None|0.3031|45/396|
|mature_hidden|303|4149/8240|1071/2096|1499/3120|None|None|0.4330|58/396|
|random_hidden|101|3334/8240|804/2096|1223/3120|None|None|0.3603|49/396|
|random_hidden|202|3269/8240|820/2096|1124/3120|None|None|0.3700|32/396|
|random_hidden|303|3658/8240|1003/2096|1265/3120|None|None|0.4242|41/396|
|raw_projection|101|4833/8240|1249/2096|1840/3120|None|None|0.4803|127/396|
|raw_projection|202|3509/8240|889/2096|1147/3120|None|None|0.3944|83/396|
|raw_projection|303|4710/8240|1200/2096|1650/3120|None|None|0.4853|130/396|

## 無序 pair 的配對錯誤

每個非等 pair 的兩個方向、四個 opcode 共八種變體不視為八個獨立 pair。每個 test seed 都是相同 396 個無序 pair，其中 12 組相等。

|Seed|A|B|兩者整組全對|僅 A 整組全對|僅 B 整組全對|兩者都非整組全對|
|---|---|---|---:|---:|---:|---:|
|101|mature_hidden|random_hidden|27|31|22|316|
|101|mature_hidden|raw_projection|39|19|88|250|
|101|raw_projection|random_hidden|37|90|12|257|
|202|mature_hidden|random_hidden|19|26|13|338|
|202|mature_hidden|raw_projection|36|9|47|304|
|202|raw_projection|random_hidden|26|57|6|307|
|303|mature_hidden|random_hidden|20|38|21|317|
|303|mature_hidden|raw_projection|37|21|93|245|
|303|raw_projection|random_hidden|32|98|9|257|

各 opcode、方向、tie、交換一致性、錯 bit 分布與來源 decoder 正確性條件關聯，完整保留於 JSON。全部 test 錯例逐列保存，並附原 NPZ 與 row index。

## 可支持的判讀範圍

成熟與隨機組的配對差異可以回答：在已存在該來源銀行、相同 263 參數新 head 與固定教材預算下，成熟表徵是否有額外幫助。raw 組具有明示的保資訊編碼座標先驗，需同時報告，不能只挑成熟對隨機的有利對照。

Train 與 heldout 分數可辨認是否明顯只記住訓練題；即使 train 本身也低，仍不能僅憑這一輪就把原因唯一歸給 head 容量、最佳化或表徵壓縮。下一個測試應事前固定、另用乾淨保留資料，不回頭挑這輪最有利 seed/checkpoint。

這不是新的正式 MAX 算符、完整 SLE 管線或自主終身成長成果。
