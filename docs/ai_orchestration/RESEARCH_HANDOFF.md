# Pro／Codex 當前研究交接

更新：2026-11-13（Asia/Taipei）。使用者最新提出「開場01、高級回音010、回音長度參數、多個五階符號、句號」。本輪Pro把新題型具體化為AE1；以下較早驗收保留歷史歸屬。

| 欄位 | 目前內容 |
|---|---|
| 任務 | 參數化多詞回音AE1：格式、完整例子、codec與資源界線 |
| 原始構想 | 使用者U：多詞回音與長度參數；Pro A：欄位細化與同payload不同r的驗法 |
| Owner | ChatGPT Pro／受指派agent，設計與程式檢查完成 |
| 下一棒 | Codex：先讀AE1，再凍結精確訓練／驗證／測試題單、課序、預算和判準 |
| 本輪分支 | `pro/advanced-echo-design-20261113` |
| 固定最新來源 | Codex [PR #15](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/15)，`365c5fbf3324d3decb625f9d04ddd1bc91af4d93`，已接續Pro PR #14 |
| AE1語法 | 01＋010＋n3回覆詞數r＋N個n5符號＋END；1≤r≤N≤4 |
| AE1回覆 | 前r個完整符號，再由學生輸出STOP；不回題頭、參數、END |
| 控制碼 | 本符號串普通ID0..29，END30=111100，UP31=111110保留；010獨立profile不覆寫Neg |
| 容量 | Qmax39／Amax24／正確prefixmax63；L80/H64可用，新runner另固定cap32，舊UR1cap24不改 |
| 課程候選 | 第一段r=N完整回音，一詞→四詞；第二段同payload、不同r，檢查參數控制STOP |
| 正式學習狀態 | 精確資料／課序／預算尚未凍結，0新NN forward、0optimizer、0成長操作 |
| 原UR1候選 | 增加其他合法地址的跨寬度教材，保留為A；未執行，暫非下一優先 |
| 主入口 | [AE1設計](PRO_ADVANCED_ECHO_DESIGN_20261113.md)、[codec／fixtures／checks](../../experiments/spiral_neural/20261113_pro_advanced_echo/README.md) |

## 最新接續：Codex Echo只讀診斷

已讀[完整結果](../../experiments/spiral_neural/20261113_echo_copy_audit/RESULTS.md)、README與HANDOFF，未重跑。P030三個舊學生混教前全八種三位元Echo各8/8，後續7/8、6/8、7/8；101的全部五個TF輸入在2a之前未作optimizer更新，仍能答對，但曾作validation，不是新盲測。有限位元跟隨支持確有照抄行為，不能唯一識別通用複製演算法。Codex主程序及獨審合計960forward／1920960MAC，0optimizer，歸Codex既有T，不混作本輪Pro成果。

## AE1接棒要點

r從開始就表示要回覆的詞數，r=N只是初階教材限制。只教完整回音不能證明有讀r；第二段同一四詞內容給r1..4，輸入長度與payload不變、只改參數。學生仍只看raw Q＋自身／教師答案前綴，codec僅用於出題與評分，不另餵詞界、r或答案長度，不按r截斷或強補STOP。

完整payload作資料分組單位，各r版本歸同一split。固定詞寬n5，先只改詞數；不要同時加Neg、實際升階通知、擴網或移植前輪人工copy權重。正式訓練前另提交精確題單、固定seed、課序、更新／MAC預算、測點與停止規則。AE1的程式檢查不是學生學會；不同詞數都教過也不等於長度外推。

尾碼僅在已知六bit詞界識別，保留END/UP讓本profile合法Q彼此不成真前綴；因此Q接答案prefix不會跨題產生矛盾標籤。這不保證舊Neg與新010未標記混用也一致。四詞cap24少了STOP的一步，新runner使用固定cap32；即使錯誤生成到最後一步，prefix最多70，仍小於L80。

Pro／受指派agent實際執行一次codec驗收PASS：4固定raw例題、120普通詞位置案例、42拒絕案例；426題小域的90525對完整Q無前綴關係，6438個teacher-prefix無label衝突。這是程式T，0NN forward；具體命令、hash及界線見新目錄checks.json與README。沒有窮舉30^4內容，也沒有啟動學生訓練。

## Codex 已完成的結果與邊界

原序控制由Pro在[PR #12](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/12)完成，固定結果head為`19ece2819c6c2c1d7ef9fdb2389efaa045b1c35e`。新次序事前提交為`042bb1097a63da9b39d2d30cc63843d4467c4b83`，manifest為`db37000543b4e8e7ef4b294883ad2346fddfd61b771a17857a1c525f1df189cc`，runner SHA為`efd3966a93793d68ee6ba02111bfdcc67f67e8bdf40c96940352d9e5bbe17862`。事前規格、初態、完整三份128epoch課序、原七份科學碼保持。

三學生最後已教整串／地址為11/12、12/12、11/12，保留整串／地址皆各0/6；strong fit只有seed202通過。epoch96已教分數10、4、6，epoch128為11、12、11，不稱三seed穩定全會。最終20個失敗、兩個generation cap耗盡、0context overflow，全數保留。24動作上限未延長，沒有補STOP。

Codex已完成三primary＋三完整replay，兩側各81408更新、1714126848training denseMAC；新批含trace／checkpoint／守門／重播／離線評估248.980063秒。全部三primary及三replay之後才評所有checkpoint。相同trainingMAC不代表總推論／I/O／牆鐘相等。大逐target trace留原本機且公開SHA；四個新ZIP有106成員，另有baseline-inputs的12成員，公開包可攜來源已核對。

Codex Windows原序重現在Pro公布結果前已依舊凍結與接棒提交啟動；兩側重疊是歷史重現，非額外獨立seed或另一個研究條件，實跑成本另列。Codex原回合的324題／18checkpoint獨審與81408筆trace稽核歸原Codex執行，不冒稱Pro本輪又做了一遍。原序與新次序都已完成，不能再當pending重跑。

完整固定來源：[次序實驗結果](../../experiments/spiral_neural/20261113_codex_target_order/RESULTS.md)、[公開封存與重現入口](../../experiments/spiral_neural/20261113_codex_target_order/README.md)。

## Pro 前輪實際驗收（PR #14）

[54題有界審核](../../experiments/spiral_neural/20261113_pro_echo_review/README.md)重新生成新課序並核對多重集合、初態與封存，僅推論三個final。所有生成及TF預測一致，logits最大差`3.814697265625e-6`在容差內；原包與沿用來源前後hash不變。真正新增1917forward／19998144denseMAC；沒有完整訓練replay或中途checkpoint推論，也沒有重驗未公開大trace。

[人工回音構造](../../experiments/spiral_neural/20261113_pro_echo_construction/README.md)只有一次固定構造、一次256題窮舉；使用原Model.forward、L80/H64，9個hidden作用、72個非零人工參數。實際2304forward／24035328denseMAC，optimizer0。固定八位元的知識已人工寫入權重；此成果不能稱從資料學會，更不能用它取代UR1的0/18。

兩項模型工作合計4221forward／44033472denseMAC；另有18題codec切片等式非神經核對。P027／P029／P030與P035的歷史結果只是讀取、核對來源，沒有重新訓練。

## 下輪必須承接的判斷

P027曾真正學會固定八位元回音，三CE seed的heldout皆64/64。P029是固定1171參數依序學n1→8，n5起有當階val/test；direct8是直接從零訓練八位元，不是零樣本跳階。兩者舊介面有`|`，P030才取消；P030仍有純01短題Echo與算符擴位的有限成功。不能把分隔符或dense架構單獨宣判為UR1病因。

UR1的地址始於Q固定offset8，ACK就是`Q[8:8+len(address)+len(UP)]`，不是任意位置搜尋後重組。變動的是Q長度、地址深度、回覆終點與生成進度的對應；同一套權重逐步重用，但絕對輸入位置沒有被架構強制共用copy規則。能表示、訓練找到、未教搭配成功三件事分開。

12是不同通知數；每通知128次呈現、每seed27136target更新。P035先前審核的30是階段課序數、64是審核推論數，不能當訓練教材數。PR13新結果證明更新次序影響本配置已教擬合；仍沒有指出唯一內部機制或證明教材多樣性無關。

## 上輪候選保留：UR1教材多樣性政策

上輪尚未執行的A問題為：保持現行純01學生、模型、更新預算與生成上限，增加其他合法地址的跨寬度教材，能否改善原六個未教搭配？先依現行codec確認可用合法地址，保持控制碼、深度與context範圍，確保raw prefix沒有矛盾target。不要同時改網路、加入外部cursor／分隔符、換新算符或加長訓練。

新題量、確切地址、混入比例、課序與固定判準需要在真正訓練前另立manifest並提交。本候選尚未凍結或執行；固定總target預算時每題曝光會改變，這是教材多樣性與重複次數的政策比較，不能寫成每題等曝光。已完成的P033 pair覆蓋診斷並未穩定修復泛化；不能先認定多資料必定成功。

原六個保留搭配已看過，只作曝光診斷；若要新盲測，需另外事前凍結未查看的題域。不要在同六題上挑seed、epochs或checkpoint後宣稱盲測。先有可泛化的確認回覆，才另測通知是否幫助新階普通題、實際作用位置、物理擴網與舊能力；ACK本身不能當通知效益證據。

## 外部隊員與提交範圍

本輪環境無可呼叫的NVIDIA／OpenRouter worker，`nvidia_status=skipped_unavailable`，真實呼叫0；Gemini本輪0。Codex前一回合NVIDIA真呼一次但語義拒收、Gemini0，保留其原報告，不混成本輪執行。本機子agent不是外部NVIDIA成果。

Pro前輪PR #14新增兩個審核／人工構造目錄與報告；本輪新增AE1設計和codec／fixture目錄，並更新三個導航／交接文件。歷史課程、科學碼、checkpoint及Codex結果不改；沒有合併PR或啟動桌面程序／背景服務。新工作開始時重新fetch相關ref，不假設main已收錄開放中的串接PR。
