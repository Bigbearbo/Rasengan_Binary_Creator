# Pro：固定八位元 Echo 的人工權重構造

這是**人工構造的表達能力反例**，不是訓練學會、不是 UR1 成功、不是長度外推。先固定 `construction_plan.json` 的一個構造，再窮舉256個八位元問題一次；不呼叫 optimizer、不搜尋參數、不另測架構。

沿用 P035 封存的原 P030 float32／tanh／兩通道 onehot `Model`，L80/H64 共10,499參數。實際只用9個 hidden，其餘入邊、bias、出邊為零。所有生成步都呼叫原 `Model.forward()`；問題只有八個真實 bits，後續只接模型自己的輸出 prefix，沒有 `|`、cursor、Q長度或答案長度通道。

## 唯一一次實跑結果

固定構造窮舉一次，**256/256 全串正確、256/256 正確生成 STOP**，無 overflow／cap exhausted；沒有修改構造或重跑。實際生成2,304次原 `Model.forward()`，24,035,328 dense forward MAC，optimizer更新與training MAC皆0。最低 argmax margin為0.9998184442520142。

10,499個實體參數中只有72個是非零的人工設定值，啟用9個 hidden；評估前後p/m/v/birth/t/RNG逐陣列相同，歷史來源SHA亦未改。inference迴圈約0.0382秒，從讀計畫到truth寫出約0.1057秒，不是完整Python啟動時間或硬體總FLOPs測量。

完整結果見 [summary.json](results/summary.json)、[256題逐步trace](results/truth.json)、[人工state](results/constructed-state.npz)。**這是把固定copy規則人工寫入權重後驗證，不是學生從256題學到了規則，也不是零樣本訓練泛化成績。**

## 固定構造

令位置 r 的兩通道為 x[r,0]、x[r,1]，occupancy 為 `s_r=x[r,0]+x[r,1]`。合法 bit 的 occupancy 是1，右側 padding 是0；這完全使用原模型已提供的輸入表示。

N=8。若已輸出 i 個 bits，當前輸入長度是 N+i：

\[
g_i=s_{N+i-1}-s_{N+i}
\]

恰好在這個位置邊界時 g_i=1，其餘候選位置為0。八個 copy hidden 將位置 gate 與原問題的第 i 個 bit 合取：

\[
h_i=\tanh(10(g_i+x[i,1]-1.5)),\quad i=0,\ldots,7.
\]

第九個 hidden 偵測八位已全部輸出：

\[
h_S=\tanh(10(g_8-0.5)).
\]

令 `u=sum(h_i)+7`，三個 logit 分別為 `z_0=-u`、`z_1=u`、`z_STOP=2*h_S`。copy 時只有目前位置的 gate 能為真，原 bit=1 時 u 約為+1，否則約為−1；其他位置約為−1。到尾端 STOP logit 約為+2並勝出。這些權重對全部256題完全相同。

外部生成安全上限固定16，沒有在第九步強制補 STOP。原歷史 `generate()` 的八步上限不足以容納八 bits 加 STOP，因此本例只另寫 argmax 生成迴圈；原 `forward()`、學生參數形狀及數值公式不改。期望的 `Q+STOP` 只在自主生成完成後評分，沒有送回學生。

## 重現

需要 repository 內固定的 P035 reference、Python及NumPy；輸出目錄必須尚未存在：

```bash
python -B experiments/spiral_neural/20261113_pro_echo_construction/construct_echo.py \
  --out <new-output-directory>
```

腳本保存已固定計畫、人工 state、256題每一步實際 prefix/logits/action、結果、來源 hash與成本。來源 SHA 有守門，評估前後驗證p/m/v/birth/t/RNG不變；固定構造未成功或技術失敗也會保存結果，不自動重跑。

## 能支持與不能支持的結論

這個構造說明固定形狀的 Echo 加 STOP 可以由目前這一類全連接 MLP 表達。人工寫入答案生成規則不等於梯度下降已從有限教材找到它。UR1 還要處理不同問題長度、地址深度與回覆長度；本例不替換其實際訓練結果：原序歷史結果為 train17/36、heldout0/18，最新 Codex target-order 結果為 train34/36、heldout0/18（[PR13，15b7788](../20261113_codex_target_order/RESULTS.md)）。本例也不宣稱H64對所有可變長度摘錄任務都已足夠。

## UR1 的起點其實固定

UR1 的 `ROOT_HEADER=00111100` 恰為8 bits。地址從0-based位置8開始；count在8…11，第一個child ID在12…15。m4／m5／m6只改地址後的通知詞，**不移動Q內的地址起點或既有地址位元**。地址深度增加會增加後續地址元件，因而移動第一份UP的起點，並非要搜尋任意區段。

由 codec 的 `encode_notice()` 與 `encode_reply()` 可直接得到：令 `a=4(d+1)` 是地址長度，`w=m+k` 是一份UP長度，則

```text
Q = 固定8-bit header + 地址 + UP + UP + UP + END
A = Q[8 : 8+a+w]
```

所以ACK是從固定offset8開始的一段**連續摘錄**。本輪沒有再執行UR1神經評估；這是已定義格式的直接分析。可變之處主要是Q長度、摘錄終點與當前已生成前綴的長度。相同總prefix長度可對應不同輸出位置，學生需學會根據Q的格式來選當前應讀的來源bit與STOP時機；它沒有被額外餵一個答案cursor，但padding occupancy已提供長度線索。

UR1這批例子都在有限L80範圍內，不是任意無界長度問題。原序歷史結果的最終已教題為17/36；最新 Codex target-order 提高為34/36，三個seed分別為11/12、12/12、11/12，heldout仍為0/18（[PR13，15b7788](../20261113_codex_target_order/RESULTS.md)）。因此，不能把原序描述成12道教材都已死背成功，也不能把最新結果描述成所有學生皆完整擬合；次序改動已改善擬合，卻仍不能只由這些分數判定唯一失敗原因是dense架構。固定形狀copy能被表達、固定訓練程序是否找到它、不同形狀組合能否泛化，是三個不同問題；本輪整體判讀見[Pro Echo審查](../20261113_pro_echo_review/README.md)。
