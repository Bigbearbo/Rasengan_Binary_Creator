# 新回音參數1、2：三個學生完成固定題庫

2026-11-13，Codex。三個fresh學生都完成事前課程，最後在同900組四詞資料上，r1與r2各900/900整題正確，包含資訊位、每詞尾零與學生自行輸出的STOP。每個學生均連續兩輪全對才停止，沒有跑滿任何40輪上限。

|seed|r1首次全對／兩連勝前進|r12首次全對／兩連勝完成|累計來源題次|target更新|最後r1／r2|
|---|---|---|---:|---:|---|
|101|3／4輪|6／7輪|16200|151200|900/900、900/900|
|202|3／6輪|4／8輪|19800|181800|900/900、900/900|
|303|3／4輪|8／11輪|23400|223200|900/900、900/900|

首次全對只在輪末觀察；202與303在首次全對後曾退步，因此不是精確首次學會時間，也沒有挑最好checkpoint。題次是完整target集合的來源題曝光：r1每輪900題，r12每輪1800題。targets全域洗牌，並非整題連續教。三模型重答同一批900組資料，不是2700組獨立資料。

|seed|r1階段題次|r12階段題次|r1總呈現次數／每題|r2總呈現次數／每題|
|---|---:|---:|---|---|
|101|3600|12600|9900／11次|6300／7次|
|202|5400|14400|12600／14次|7200／8次|
|303|3600|19800|13500／15次|9900／11次|

r12完整保留r1出口的權重、Adam m/v/birth/t、RNG與推論計數；加入r2後仍混合r1複習。兩個r的題數相同，逐target更新數為6300:11700，未作長度平權。

## 實際同題示例

凍結bank的pairID36，資料ID為[1,6,23,11]。以下直接取三學生已保存的最後自由生成結果，不增加模型查詢；三者皆相同。兩題只有r欄位改變，四個資料詞、順序和END都相同。

```text
01 010 0010 000010 001100 101110 010110 111100 → 000010 S
01 010 0100 000010 001100 101110 010110 111100 → 000010 001100 S
```

## 最後內容、尾零與停止

三seed每個都得到下列分數。r1回答一個完整六bit詞，r2回答前兩個；END不回覆。自由生成只接自己的前綴，不餵正解、游標或解碼特徵，不依正解長度截斷或強制STOP。

|r|整題含STOP|自由生成資訊位|自由生成尾零|STOP正確位置|正確前綴TF全部targets|
|---|---|---|---|---|---|
|1|900/900|4500/4500|900/900|900/900|6300/6300|
|2|900/900|9000/9000|1800/1800|900/900|11700/11700|

這些是已教集合分數；沒有另外的保留題或r3/r4探測。全部第一、二詞答案組合30×30皆教過，但每個first pair只搭配一組固定後兩詞，故只覆蓋900/810000個四詞payload，不證明未教suffix、任意長度或一般計數copy算法。課程、資料組成與舊Pro AE1不同，沒有等預算joint-training或lr對照，不能單獨歸因於課程、題量或固定位置。

## 凍結、執行與驗收

事前commit `966297559b4f4dedc4b8cf655258d4036cc21cc8`，manifest `dcf3ea17d1f5a179ccaa37b5f544f630ad274afdfa7b56ab93684d1a9344fe60`，runner `b95c9a96f096624c2d01ef6dcd1782070d1d3f172cfbc4a60b097754047895a6`。inputs.zip原bytes7291036／SHA `8eb05d5649c5568abf5da18a5b51ffa6c5a1be1e721481b1960d2e27cebe5efe`，13成員含source、plan、bank、1800Q、三份完整初態及六份40輪課序。

21個事前公開檔全部byte回讀後才開跑：20個由Git連接器，較大inputs.zip使用無認證公開GitHub blob API。PR建立UTC00:39:08，實際execution-start檔建立UTC00:39:51.628。授權與Git對照由協調者負責；知道公開SHA本身不是授權。git-prereg-receipt.json與execution-intent.json保存實際核對。

唯一正式session7462 exit0，stdout14269bytes、stderr0，無重啟。三primary全部完成後只指定seed101完整重播，重新得出每個phase、streak與停止決定；所有實際epoch的prediction/loss digest、完整state、生成與分數精確一致。202、303明列not_planned。沒有保存獨立replay state副本或逐target原始loss／中間梯度，不冒稱這些也被第二個程式重新驗算。

一次獨立raw-NumPy audit不import learner/driver，先驗全部metadata才做trained forward。重算40個primary epoch的59400次完整生成、54000個最後TF的logits／機率／CE，strict exact；核58個science NPZ、三份frozen initial、240份課序、phase完整狀態承接、所有first-full／streak／stop／exposure／成本與失敗清單，來源、輸入、science及execution metadata前後hash不變。40份epoch與3份student數值proof及成本逐步落盤。入口[review/post-run.json](review/post-run.json)，SHA `e125cdbbebab4478e0bd4665ebd87ba17e4d7767b160edb81c753e8874c0f75b`；明細及audit source同目錄。

## 實際成本

|部分|optimizer更新|非更新forward|training dense MAC|inference dense MAC|
|---|---:|---:|---:|---:|
|三primary訓練與輪末probe|556200|556173|11711347200|5801996736|
|唯一seed101完整重播與probe|151200|151176|3183667200|1577068032|
|最後已教集合TF|0|54000|0|563328000|
|一次獨立audit|0|610173|0|6365324736|
|事前native合成工程|6|32|126336|333824|

正式批次含重播、probe、epoch I/O、最後TF及後段input guards共712.2413899999956秒；不含timer前首次input validation、事前設計／工程／Git／外部審查或獨審，亦非純kernel時間。獨審25.51782500000263秒。工程另有54 mock targets與14 mock probes，不算神經更新／推論。MAC是矩陣結構計數，不代表硬體總FLOPs、能源或整體LLM費用；p/m/v/birth每學生209980 bytes，不是程序RAM峰值。

NVIDIA單次合成方法候選6.187秒、1921tokens、cost0；兩項錯誤疑點被本機字寬／獨立前綴長度算式否決，未作研究接受或重呼。Gemini現有安裝／登入保留，analysis-only工具隔離未解而skip。OpenAI原生實作與獨審分開記錄，不冒充外部真呼。詳見EXTERNAL_REVIEW.json。

全部實際science檔、完整事前輸入、每輪完整state／生成／中途失敗、truth、唯一replay記錄與獨審proof按publication-manifest.json逐檔封存，含bytes／SHA／CRC與byte往返檢查。不公開整份私人交接、聊天、帳號quota或憑證。不自動合併PR。
