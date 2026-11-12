# Pro：P030 擴網與升階機制探測

作者／執行歸屬：**ChatGPT Pro**，2026-11-12。T：限定機制探測，不是新一輪學習效能實驗。研究解讀與待驗設計見[小網路與成長審查](../../../docs/ai_orchestration/PRO_SLE_SMALL_NETWORK_REVIEW_20261112.md)。

## 固定來源與結果

來源為main commit `9118abf4e895204588f7c5aa1bfc2615d0ab52b8`的P030程式與三個dynamic學生在`1b_echo_n3`的checkpoint。腳本內核對來源與模型SHA256；模型以`allow_pickle=False`載入後複製。保存的[results.json](results.json)是可重播腳本的執行結果，包含24題的完整自由生成、逐seed狀態檢查與限制。

每個seed從L12/H68擴到L13/H69，40個合法舊prefix的logits差都是0.0，原權重／Adam m/v／birth／global step保留；舊raw題8/8正確，改成op2同語義題後、尚未適應時0/8正確。這區分擴網函數保持與新profile適應，不把零樣本適應視為使用者要求。

每個seed另在可丟棄副本上執行兩個optimizer更新，驗證新hidden的出邊先取得梯度、之後入邊也取得梯度。每次探測執行共六步，另有重播；不能稱完整課程訓練、收斂證據或成長效率提升。原checkpoint前後SHA相同，從未寫回；正式課程沒有回退舊profile。

原P030已報告算符擴位後持續學生以132/156/180題恢復，從零需288/276/288題；讀探測時必須一起保留這項局部遷移正面證據。

## 重播

從repository根目錄執行；需Python與NumPy。`--out`必須是尚不存在且位於P030封存外的目錄：

```bash
python -B experiments/spiral_neural/20261112_pro_growth_review/growth_microprobe.py \
  --p030-dir experiments/spiral_neural/20261112_p024_p030 \
  --out /tmp/sle-pro-growth-review-new
```

腳本沒有完整訓練迴圈，不呼叫NVIDIA、不改正式程式或checkpoint。結果附原始執行Python／NumPy版本；跨平台的浮點細節可能不同，故保函數斷言容差為2e-6，不能保證跨所有平台逐byte相同。公開結果在本環境獨立重播一致。

## 表示條件

目前程式中`0=[1,0]`、`1=[0,1]`、padding=`[0,0]`。因此「新增高位0不影響隨機新連線」不是此onehot實作的通用性質；保函數檢查的新增空間是padding。新profile中的合法零token、整段位置位移與後續共同更新需分開驗證。此處記錄限制，不改歷史計畫或checkpoint。

`manifest.json`保存來源、腳本與結果hash、實際檢查範圍。`nvidia_status=skipped_unavailable`、真實呼叫0次。歷史Codex訓練與本次Pro機制探測分開歸屬。
