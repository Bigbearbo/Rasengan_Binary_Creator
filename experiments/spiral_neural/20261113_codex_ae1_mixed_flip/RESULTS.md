# 三個既有模型完成回音1／回音2／翻轉1混教

2026-11-13，Codex。直接接續PR26三個finalstate，無重置權重、Adam、birth、t或RNG。三模型baseline原回音兩類各900/900、新翻轉皆0/900；混教後三類均900/900含尾零與自行輸出的STOP，連續兩輪全對而提前停止。

|seed|首次三類全對|兩連勝停止|本輪來源題次|新增target更新|父t→最後t|
|---|---:|---:|---:|---:|---|
|101|第5輪|第6輪|16200|145800|151200→297000|
|202|第8輪|第9輪|24300|218700|181800→400500|
|303|第6輪|第9輪|24300|218700|223200→441900|

每輪2700 Q的完整target集合各一次，共24300 targets，逐target全域洗牌，並非整題連續教。三模型使用同900組payload、三類各900題；每題分別呈現6／9／9次，不是8100組獨立資料。首次全對僅在輪末觀察，seed303首次全對後退步，不以最好checkpoint代替兩連勝。全部早於40輪上限，未追加訓練或換seed。

## 舊回音確實一度退步

|seed|baseline E1/E2|混教中最低E1/E2|最後E1/E2/F1|
|---|---|---|---|
|101|900／900|806／870|900／900／900|
|202|900／900|899／851|900／900／900|
|303|900／900|826／873|900／900／900|

因此本輪的觀測是「新翻轉從0/900學到900/900，舊回音在既定混合練習中恢復全對」。不能說過程完全沒有遺忘，也沒有無Flip、不同混合比例或joint-from-scratch對照來隔離病因或政策優勢。最低值是已存曲線的描述統計，不影響課序、停止或checkpoint選擇。

每個學生最後E1/F1自由生成資訊位各4500/4500、尾零各900/900、STOP位置各900/900；E2為9000/9000、1800/1800、900/900。正確前綴TF每學生E1/E2/F1為6300/6300、11700/11700、6300/6300。原始truth與derived-readout.json保存逐類分解，沒有額外模型查詢。

## 同一份四詞資料的實際輸出

凍結bank pairID36，資料[1,6,23,11]。三個模型的原存最後自由輸出皆如下，只有題型或組數參數改變，資料及順序相同：

```text
01 010 0010 000010 001100 101110 010110 111100 → 000010 S
01 010 0100 000010 001100 101110 010110 111100 → 000010 001100 S
01 100 0010 000010 001100 101110 010110 111100 → 111100 S
```

翻轉只反第一詞的五資訊位，尾0不變；F1輸入ID0、1分別實際生成111110S、111100S。這些是字面答案內容，不執行UP／END；外部S才是停止。E1/E2原1800個Q/A與父資料逐bit相同。Flip100只屬選定AEM1 profile，不混用舊numeric Zero100。

## 事前公開與重現

父結果commit `7213cce112a8411b13dc128c49f9e88acfc9d65f`，三parent原NPZ與公開ZIP的SHA／Gitblob／member CRC及bytes精確核符。父public manifest還以Git連接器重新byte回讀。完整p/m/v/birth/t/RNG和舊計數均帶入，本輪成本只報新差額。

事前commit `6b9df16cb593c422426f6cb093a8ecfbe18d1e13`；manifest `a85457a3d7a6e06d7b20ad608d695a6f322a9b3daf38e714ff974fb7d7b6d218`；runner `3ad223a4f11d82d2c4ede86a97093d03a604bd22677c5c327936b393334037f0`。inputs.zip7967750 bytes／SHA `fa8168e7029b5f0d0892bd8b73c7f4e05b0293d3fc56f6956eb38671de9d5d36`，13成員含parent原bytes／來源證據、bank、2700Q、source及全部120份預生成課序。

21事前公開檔全部byte核對後，唯一session20420正式執行exit0，stdout10634bytes、stderr0。PR建立UTC01:40:26，execution-start實檔建立UTC01:41:43.083。三模型baseline全部舊回音通過時新optimizer仍0，才進入mixed訓練；baseline不計streak。Source核心freeze後未改，無重新啟動。

指定seed101唯一完整replay從parent重做baseline和全部實際epoch，逐epoch loss/prediction digest、fullstate、輸出、分數與停止精確一致；202/303 not_planned。沒有另存replay state副本、逐target原始loss或中間gradient，不冒稱第二程式獨算這些缺席資料。

一次獨立rawNumPy audit不import learner/driver：先完成全部metadata檢查，才重算8100 baseline＋64800 epoch＝72900次完整生成與72900個最後TF logits／機率／CE，strict exact；核所有parent來源、完整state承接、baseline只改推論計數、各輪新差額／全累積counter、first-full／streak／停止／失敗／成本。來源、frozeninputs、science、收據和logs前後hash不變。入口[review/post-run.json](review/post-run.json)，SHA `504fc39bd03920b22176db5718b0413cb1b15458fae09577defec07103a5bb1a`。baseline／epoch／student proof與成本逐段保存。

## 本輪新成本

|部分|新增optimizer更新|非更新forward|training dense MAC|inference dense MAC|
|---|---:|---:|---:|---:|
|三primary baseline|0|72898|0|760471936|
|三primary mixed訓練與probe|583200|583457|12279859200|6086623424|
|指定101 replay baseline|0|24298|0|253476736|
|指定101 replay訓練與probe|145800|145807|3069964800|1521058624|
|最後TF|0|72900|0|760492800|
|一次獨立audit|0|729255|0|7607588160|
|native合成工程|6|32|126336|333824|

正式新增訓練合計729000updates／15349824000MAC，非更新899360forward／9382123520MAC；父工作不重收。正式overall wall821.947731799999秒，包含全部baseline、primary/replay訓練及probe、state I/O、finalTF和後段inputguards；不含timer前首次input validation、事前工程／Git／外部審查／獨審，非純kernel。timing.trajectories各train_one秒數不含baseline，不能把單replay trajectory稱完整replay含baseline時間。獨審31.45865590000176秒。

工程另有97200 mock targets／6 mock probes，未用原optimizer，不計神經MAC。native6次update各含一次training forward，另32次非更新forward，總forward呼叫38；表格不把其中6次再算推論。MAC只計矩陣結構，不代表硬體總FLOPs、能源或整體LLM成本，209980bytes陣列不是程序RAM峰值。

NVIDIA單次候選4.75秒／2061tokens／cost0，其錯誤baseline和字寬疑點已由本機格式算式否決，未採為事實；Gemini隔離未解skip，既有安裝／登入不動。詳EXTERNAL_REVIEW。全部實際science、baseline、父狀態、逐輪輸出和中途錯誤、重播及獨審按publication-manifest封存；原始輸入保持exactbytes，不公開私人聊天、憑證或帳號quota。

範圍是同900組四詞資料的三類訓練域學習與保持。900不是全部30^4組合，沒有blind／新suffix、Flip2、r3/r4或長度外推測試，也不證明內部router、通用copy／flip算法或混教因果優勝。不自動合併PR。
