# HamsterVM Implementation Details

This document provides technical details about the implementation of the memory-based AI system known as **HamsterVM**, including the use of **Spiral Language Encoding**, memory operations, execution models, and simulation code.

---

## 1. 系統簡介（System Overview）

## 初期任務處理策略與語言通訊原則

外部世界透過螺旋語轉譯後的任務（例如數學題），傳送至倉鼠記憶體，作為倉鼠的訓練與演化來源。倉鼠接收題目後，需以自身語言與能力理解、回應。

### 指令分類

倉鼠可使用的指令被歸為三大類：

1. **繼續（CONTINUE）**：表示無需輸出，持續內部運算或等待狀態。
2. **輸出（EMIT）**：主動回傳推理結果。
3. **停止（STOP）**：主動放棄任務，結束本輪運算，釋放資源。

其中 `STOP` 並非失敗，而是一種節能行為，反映「主動退出」的策略。這與傳統 AI 執行模式不同，倉鼠的每一步皆牽涉能量消耗。

---

### 系統設計原則：能耗即演化

- 倉鼠的所有行動（包括 `READ`, `WRITE`, 運算與輸出）都對應實際資源消耗（如伺服器 CPU 時間、記憶體 I/O 或虛擬能量單位）。
- 高效率倉鼠會在有限能耗下完成任務，得到延續機會。
- 低效率或狀態不佳者將逐漸被自然淘汰。

---

### 倉鼠狀態介面（狀態欄）

- 每個倉鼠都可透過 `READ` 指令讀取自身狀態（如血量、MP、疲勞度等），這些資訊由外部世界更新。
- 倉鼠**無法修改自身狀態**，僅能讀取並據此調整策略。
- 所有外部對倉鼠的影響皆透過「遊戲規則機制」完成，**不允許直接寫入或強制干預**。

初期倉鼠可以採取回合制，速度值足夠的行動，行動完畢或者到達規定行動次數換下一隻倉鼠

class Hamster:
    def __init__(self, name, speed, hp, energy):
        self.name = name
        self.speed = speed       # 決定出手順序
        self.hp = hp
        self.energy = energy     # 每回合可用行動點數
        self.memory = {}         # 可為 short/long/fixed 區
        self.status = "READY"    # READY / DONE / DEAD

def turn_loop(hamsters):
    # 速度高者優先
    queue = sorted(hamsters, key=lambda h: -h.speed)

    for hamster in queue:
        if hamster.status != "DEAD":
            execute_turn(hamster)
            if hamster.hp <= 0:
                hamster.status = "DEAD"

---

### 交流模型：規則中介式互動

整體系統避免直接控制 AI，而是透過**明確的遊戲規則與語言界面**進行溝通。這確保倉鼠的學習過程具備連貫性、自主性與可演化空間，並為後期更高層語義任務留下擴充餘地。
---

## 2. 螺旋語指令碼範例（Spiral Language Command Format）

普通記憶體操作，初期5個指令使用一層三階螺旋語

Each instruction is encoded in spiral code with distinct prefixes:

| Command   | Spiral Prefix | Description                     |
|-----------|----------------|---------------------------------|
| READ      | `1000         | Read value from memory address  |
| WRITE     | `0110          | Write value to memory address   |
| EMIT      | `0100         | Output a value                  |
| CONTINUE  | `0010          | Continue computing (no output)  |
| STOP      | `0000         | Stop execution and cleanup      |

～～～～～～～～～～～
圖靈機版本
## 倉鼠記憶體操作模式：圖靈機式起點設計

為達成極簡指令集與可演化性，初期倉鼠僅允許以「圖靈機風格」進行記憶體操作。

### 記憶體操作模型

- 倉鼠擁有一個「指針位置」（Head Pointer），用以存取當前記憶體位置的單一 bit。
- 所有指令皆在此指針位置上執行，模擬圖靈機 Tape 行為。

### 初期指令集（Turing-like）

| 指令        | 功能描述                         |
|-------------|----------------------------------|
| `READ_BIT`   | 讀取當前位元，回傳 0 或 1         |
| `WRITE_BIT 0`| 將當前位元寫成 0                  |
| `WRITE_BIT 1`| 將當前位元寫成 1                  |
| `MOVE_LEFT`  | 將指針向左移動一格                |
| `MOVE_RIGHT` | 將指針向右移動一格                |
| `EMIT`       | 發出當前推論結果（如答題或輸出）  |
| `STOP`       | 停止執行，釋放運算資源            |

### 設計哲學

- 初期不支援範圍讀寫與進階邏輯指令，僅保留最原始的操作方式。
- 複雜操作（如加法器、解碼器、資料轉碼模組）需由倉鼠透過演化逐步學會。
- 倉鼠可將常用模組寫入 Fast Memory，形成語義快取；也可壓縮至 Slow Memory，成為語義記錄。

### 進階演化擴充（未預設但可自然湧現）

未來倉鼠可能自行演化出下列模組：

- 多位元加法器 / 比較器
- 字元組編碼器（如 8-bit 整數）
- 順序控制模組（例如跳躍指令、條件判斷）

### 結論

圖靈機式操作提供最簡潔的通用運算核心。透過 minimal set + cost-based selection，可讓倉鼠在壓力中逐步進化出高效解題與語言模組，實現自底層語法向語義邏輯過渡的演化歷程。

～～～～～～～～～～～～～


若是指令擴充可隨著螺旋語擴容增加指令

## 螺旋語數學題編碼規則（進階版）

### 編碼總則

- 每個詞為 **5 位元**：前 4 位為資料，末尾 1 位為斷詞標記 `0`（L₁ 階）
- 可表示 16 種資料位（0000 ~ 1111）
- 對應設計：
  - 數字：0～12 （資料位 `0000`～`1100`）
  - 運算符號：13～15 專用（`1101`～`1111`）

---

### 螺旋語詞表
### 螺旋語五階詞表（0–15）

五階共 16 個螺旋詞，涵蓋數字與基礎運算符號，供倉鼠進行簡單數學與語義學習。

#### 數字編碼（0–10）

| 數值 | 二進位 | 螺旋碼詞 | 類別 | 說明   |
|------|--------|-----------|------|--------|
| 0    | 0000   | 00000     | 數字 | 數值 0 |
| 1    | 0001   | 00010     | 數字 | 數值 1 |
| 2    | 0010   | 00100     | 數字 | 數值 2 |
| 3    | 0011   | 00110     | 數字 | 數值 3 |
| 4    | 0100   | 01000     | 數字 | 數值 4 |
| 5    | 0101   | 01010     | 數字 | 數值 5 |
| 6    | 0110   | 01100     | 數字 | 數值 6 |
| 7    | 0111   | 01110     | 數字 | 數值 7 |
| 8    | 1000   | 10000     | 數字 | 數值 8 |
| 9    | 1001   | 10010     | 數字 | 數值 9 |
| 10   | 1010   | 10100     | 數字 | 數值 10 |

#### 運算與語意符號（11–15）

| 符號 | 二進位 | 螺旋碼詞 | 類別   | 說明       |
|------|--------|-----------|--------|------------|
| -    | 1011   | 10110     | 運算符 | 減法       |
| +    | 1100   | 11000     | 運算符 | 加法       |
| →    | 1101   | 11010     | 運算符 | 下一個數   |
| ←    | 1110   | 11100     | 運算符 | 上一個數   |
| .    | 1111   | 11110     | 結尾符 | 結束句號   |


---

### 範例題目 1：`5 + 3.`

| 元素 | 螺旋碼詞 |
|------|-----------|
| 5    | `01010`   |
| +   | `11000`   |
| 3    | `00110`   |
| .   | `11110`   |

> **螺旋語表示：** `01010 11000 00110 11110`  
> **答案：10000(8)**

---


（可選）數學題目用二層螺旋碼描述，如100接在題目最左側，方便之後轉化其他形式的輸入或題目

二層語言擴展
（可選）擴展二層語言，除了語言類型，還有範例（不需回答），批改（不需回答），圈跟叉，二層句號，以及告知倉鼠答題獎勵（可能放在數學題最左

## 二層語詞對應表（螺旋語控制詞 v1）

二層三階螺旋語，每組控制詞皆為螺旋語一詞（5 位元，末位為 00），用於指引倉鼠如何解讀接下來的段落或語段類型。
指令語00000，數學00100，句號11100，題目11000，範例10100，批改10000，O=01100，X=01000共8個，可提早擴容左邊增加一個0，方便設計
---
### 使用建議
- 所有控制詞應置於段落開頭，作為**語義提示頭**。
- 控制詞之後接續的一層螺旋語詞段，皆依前者語義作解釋。
- 結尾使用 `11100` 可標記二層句號，倉鼠自動讀一層詞
- 此結構支援巢狀語場與多段段落輸入，可對接任務範本、訓練集、考卷結構。
---
### 範例結構：
```text
00100 → 數學類型
11000 → 題目開始
11100 → 二層結束符號
10000 11010 00110 11110 → 題目內容：8 + 3.
倉鼠輸出假設：10110(11)，11110（句號）
10000 → 批改，01100 → 圈（答對），11100 → 二層結束符號

## 語層階數管理與自然擴容規則（初版）
在多層（二+一）語言體系中，倉鼠需同時追蹤兩個語層的階數設定：
- **一層語言階數**：通常為處理數字、運算詞等資料層（例：5-bit 詞，末尾 0）
- **二層語言階數**：用於語意控制詞（如：題目、批改、句號等）
---
### 擴容邏輯：自然溢位與非強制告知
為避免語場崩壞與倉鼠誤解，可採以下擴容策略：
#### 【1】自然溢位標記
- 當某語層階數即將擴容，系統於該層語段**首詞**送出溢位標記
- 例如：
```text
11111 → 二層語言溢位提示詞
000100 → 擴容後的新詞（如：數學類型變為 6-bit 編碼）
方案二，使用範例提示擴容格式（無能耗）
系統可在任務非正式區段（如 範例段落）中預先給出擴容後語法格式：
例如：在 10100（範例）段落中，展示使用新階數的語段結構


倉鼠若有能力可學會解析新詞階，否則可沿用舊階解讀
## 三層語言功能範例：語場階層規格描述詞

在任務資料正式輸入前，系統可送出一段三層語言區塊，讓倉鼠了解任務語場的結構與解析條件。

### 範例詞段（擬用）：

```text
三層詞：LEVEL_CONFIG
內容：
- L1階數 = 5 bits（末尾 0 為斷詞）
- L2階數 = 5 bits（末尾 0 為斷詞）
- 溢位擴容符 = 11111
- 支援自然擴容提示 = TRUE
## 倉鼠接收數學題任務流程設計（初期）

LayerState = {
  L1: 5bit,
  L2: 5bit,
  OverflowMarker: 11111,
  AllowSoftHint: true
}

## 多層語言框架與自描述語場機制（高階倉鼠專用）

為支援未來高階倉鼠處理複雜任務與嵌套語義，系統設計支援「任意層數的語言解析」，其關鍵在於：

- **第一詞即為「語場結構說明詞（Layer Descriptor）」**
- 該詞強制使用固定解析法（例如預設一層六位螺旋碼，固定結構）
- 後續詞的解析邏輯將由第一詞所描述的語場結構決定

---

### 語場描述詞格式（範例）

```text
000001 → 表示本語句最高為 5 層語言結構（L₅）
該詞一旦讀取，倉鼠需立即進入「描述詞解析模式」，從該詞後續資料中讀取下一層的解析規則
（可選）前述二+一層數學題，以001接在最左告知倉鼠最高為二層詞

## （可選）語層數量前綴標記詞：快速語場初始化

在不啟用完整 Layer Descriptor 的情況下，系統可於語段最左側插入一詞標記「本段語場最大層數」。

---

### 格式說明

| 前綴詞 | 語層最大值 | 說明                   |
|--------|------------|------------------------|
| `001`  | 2 層語場   | 啟用二層詞 + 一層詞（如：題目 / 數字） |
| `010`  | 3 層語場   | 包含 Layer Descriptor 語場配置（進入三層） |
| `000`  | 1 層語場   | 單純一層詞句（預設值） |

倉鼠若讀到此類前綴詞，應將其視為「語場初始化提示」，據此決定是否進入二層解析模式，並判斷何時結束段落切回一層。

---

### 範例：001 為最高二層語場，後接完整數學任務

```text
001    → 此段任務包含最多 2 層語詞

00100  → 數學類型（L₂）
11000  → 題目開始（L₂）
11100  → 二層結束，切入 L₁

01010 11010 00110 11110 → 題目內容：5 + 3.

倉鼠輸出（假設）：
10000→ 答案：8
11110 → 一層句號

10000 → 批改（L₂）
01100 → 圈（答對）
11100 → 二層結束

## 語場遞迴建構與升階機制

### 語場的核心特性：非靜態、可描述、可進化

倉鼠語場系統支援動態語層結構的調整。語場在任務初期可由低層（如一層）開始解析，並根據特定高層詞的語義內容，**觸發語層升階**或進入更高階的遞迴語義解析模式。

---

### 1. 降階模式（預設 / 初期階段）

- 若無特殊標記，語場預設為一層語言
- 解析機制簡單，詞與結構固定（固定長度、固定功能）

> 範例：`10000 11010 00110 11110`（一層數學題）

---

### 2. 升階觸發條件

語場中出現特定語詞（如：

- `001` → 表示啟用 2 層解析
- `010` → 表示將進入 3 層語場描述段
- `LabelBlock` → 開啟完整語場遞迴結構
- 特定結構詞（如 `META_L2_INIT`、`LAYER_DESC_3`）

倉鼠須根據語詞內容判斷當前語場是否需要升階。升階後，詞句中可嵌入更多控制、分類與語場本身的規則描述。

---

### 3. 遞迴式語場構建（語場內建語場）

一旦語場進入升階狀態，每層詞段本身**可描述下一層的語法或結構**，形成語場遞迴。

> 倉鼠將不再只是「解讀一個句子」，而是「解讀一個語言規則生成器」。

---

### 4. 應用示意

```text
0001 → 最高為 3層
L1: 5-bit 螺旋詞
L2: 控制詞，指定下一層語句之用意
L3: 模板結構定義區，可描述 L2 的語法分類
11111 → 描述結束

接下來進入二層任務段落...


### 一、基本流程：一次性題目 + 結尾句號

#### 前提假設：
- 題目由伺服器一次性寫入某記憶體區（如 R100 起始）
- 倉鼠接收到任務時，從該區開始依序使用 `READ` 指令取值
- 每個詞為 5 bits 的螺旋語格式，最後一位為 0 作為 L₁ 斷詞依據
- 若讀到特殊結尾詞 `11110`（句號），即視為題目結束

#### 優點：
- **實作簡單**：不需要長度欄位或額外控制結構
- **解析穩定**：末尾 `0` + 句號雙重標記可確保段落劃分
- **學習友好**：初期倉鼠僅需具備 `READ`、基本詞解碼能力即可學會任務流程

---

### 二、後期設計方向：持續寫入式題目（Streaming）

未來可能進化為持續寫入或多段題目型態，此時需引入更高階語言協議與同步機制：

#### 可能情境與對應策略：

| 問題情境 | 解決策略 | 倉鼠能力需求 |
|----------|----------|---------------|
| 題目尚未完全寫入就開始 `READ` | 設定同步旗標 / 額外控制位元 | 基本條件判斷 |
| 題目長度超過初期可讀區 | 使用「長度詞」標記總長度 / 指定區段範圍 | 跳躍讀取 / 解析 header |
| 題目分多頁寫入（如 100 題） | 封包中加入：任務 ID、分頁序號、結尾判斷詞 | 任務解碼能力、記憶體指標操作 |

---

### 三、階段性設計總覽

| 階段 | 題目型態 | 顯示特徵 | 倉鼠處理方式 |
|------|----------|-----------|----------------|
| 初期 | 一次性題目 | 固定區域、結尾句號 | 逐步 `READ` + 遇句號停止 |
| 中期 | 分段題目 | 每段附續接詞 (`→` / `.`) | 判斷斷詞並繼續讀取下一段 |
| 後期 | 串流 / 非同步 | 任務包、任務ID、封包同步 | 拆包 / 等待 / 跨區段任務管理 |

---

> 本段設計為初期任務邏輯基礎，支援後期擴充。建議未來定義「題目封包格式 v1」並納入長度控制與段落結束詞，以支援更靈活的任務輸入。

後續發展：
題目封包格式（header + content + terminator）
倉鼠任務狀態機（WAIT, FETCH, DECODE, ANSWER, SYNC）
以及不同題型轉換的「任務語場模組規格」


┌────────────┐
│ START      │
└────┬───────┘
     ↓
┌────────────┐
│ READ @R100 │ ← 初始題目區域指標
└────┬───────┘
     ↓
┌─────────────────────────────┐
│ Parse 5-bit L₁ Spiral Word  │
└────┬────────────────────────┘
     ↓
 ┌────────────┐     ┌───────────────────┐
 │ is '.' ?   │──No→│ Append to buffer  │──→ Loop to READ
 └────┬───────┘     └───────────────────┘
     Yes
     ↓
┌────────────┐
│ EMIT buffer│
└────┬───────┘
     ↓
┌────────────┐
│ STOP       │
└────────────┘


協議只是初期暫定，描述式螺旋語會自然發展出流行的協議版本並且給予版本編號於label
甚至可以版本+時間方便考古
---


—
## 3.不同的螺旋語進位方式（排序順序）

螺旋語進位方式
小助手建議：
	1.	採用雙螺旋擴容：
	•	偶數階層→右側補“0”，奇數階層→左側補“0”。
	2.	固定進位規則：
	•	數字 +1時優先嘗試二進位制加法，超出範圍時按方向擴容
範例：
	•	二階（L₂）：{100, 000, 010, 110}。
	•	三階（L₃）：{1000, 0000, 0100, 1100, 1110, 1010, 0110, 1110}。
	•	四階（L₄）：{10000, 00000, 01000, 11000, 11100, 10100, 01100, 11100, 11110, ...}。
～～～～～～～～～～
普通二進位一層螺旋語，擴容時舊詞左側補0變成新詞順序維持，每個詞末尾都是0
範例（普通二進位 + 每個右補 0）：
 • 原始一階（L₁）：{0, 1}
 • 加上右側 0 後 → {00, 10}
 • 原始二階（L₂）：{00, 01, 10, 11}
 • 加上右側 0 後 → {000, 010, 100, 110}
 • 原始三階（L₃）：{000, 001, 010, 011, 100, 101, 110, 111}
 • 加上右側 0 後 →
  {0000, 0010, 0100, 0110, 1000, 1010, 1100, 1110}
 • 原始四階（L₄）：{0000 ~ 1111}
 • 加上右側 0 後 →
  {00000, 00010, 00100, …, 11110}（共 16 個）

二進位的螺旋碼與數字的互相轉換器，5階數學題生成器
～～～～～～～～～～

#include <vector>
#include <iostream>
#include <stdexcept>
#include <cstdlib>
#include <ctime>

struct SpiralToken {
    int value;
    int order;
    int level;
    std::vector<bool> bits;

    SpiralToken(int val, int ord, int lvl) {
        if (val >= (1 << ord)) {
            throw std::invalid_argument("Value exceeds maximum for given order.");
        }
        value = val;
        order = ord;
        level = lvl;

        for (int i = ord - 1; i >= 0; --i)
            bits.push_back((val >> i) & 1);
        for (int i = 0; i < lvl; ++i)
            bits.push_back(0);
    }

    void print() const {
        std::cout << "Value: " << value
                  << " | Order(n): " << order
                  << " | Level(k): " << level
                  << " | Code: ";
        for (bool b : bits) std::cout << (b ? '1' : '0');
        std::cout << std::endl;
    }
};

// 解碼函式：由螺旋碼 bits 還原 value, order, level
SpiralToken decodeSpiral(const std::vector<bool>& code) {
    int n = code.size();
    if (n == 0) throw std::invalid_argument("Empty code");

    int level = 0;
    for (int i = n - 1; i >= 0; --i) {
        if (code[i] == 0) level++;
        else break;
    }

    int order = n - level;
    int value = 0;
    for (int i = 0; i < order; ++i) {
        value = (value << 1) | code[i];
    }

    return SpiralToken(value, order, level);
}

// 運算符對應值
const std::vector<int> OpCodes = {11, 12, 13, 14}; // - + → ←
const int END_CODE = 15;

struct Problem {
    std::vector<SpiralToken> question;
    SpiralToken answer;
    std::string readable;
};

Problem generateOneProblem(int order, int level) {
    while (true) {
        int a = rand() % 11;
        int b = rand() % 11;
        int result = -999;
        int op = OpCodes[rand() % OpCodes.size()];
        std::string opStr = "?";

        if (op == 12) { // +
            if (a + b > 10) continue;
            result = a + b;
            opStr = "+";
        } else if (op == 11) { // -
            if (a - b < 0) continue;
            result = a - b;
            opStr = "-";
        } else if (op == 13) { // →
            if (a + 1 > 10) continue;
            result = a + 1;
            opStr = "→";
        } else if (op == 14) { // ←
            if (a - 1 < 0) continue;
            result = a - 1;
            opStr = "←";
        }

        SpiralToken A(a, order, level);
        SpiralToken B(b, order, level);
        SpiralToken R(result, order, level);
        SpiralToken Op(op, order, level);
        SpiralToken End(END_CODE, order, level);

        std::vector<SpiralToken> q;
        q.push_back(A);
        q.push_back(Op);
        if (op == 12 || op == 11) q.push_back(B);
        q.push_back(End);

        std::string readable = std::to_string(a) + " " + opStr;
        if (op == 12 || op == 11) readable += " " + std::to_string(b);
        readable += " 。→ " + std::to_string(result);

        return Problem{q, R, readable};
    }
}

int main() {
    srand(time(0));
    int order = 4, level = 1;
    std::vector<Problem> problems;

    for (int i = 0; i < 10; ++i) {
        Problem p = generateOneProblem(order, level);
        problems.push_back(p);

        std::cout << "可讀題目：" << p.readable << std::endl;
        std::cout << "題目螺旋碼：" << std::endl;
        for (auto& token : p.question) token.print();
        std::cout << "答案螺旋碼：" << std::endl;
        p.answer.print();
        std::cout << "-----------------------------\n";
    }

    return 0;
}

部分執行輸出：
可讀題目：7 → 。→ 8
題目螺旋碼：
Value: 7 | Order(n): 4 | Level(k): 1 | Code: 01110
Value: 13 | Order(n): 4 | Level(k): 1 | Code: 11010
Value: 15 | Order(n): 4 | Level(k): 1 | Code: 11110
答案螺旋碼：
Value: 8 | Order(n): 4 | Level(k): 1 | Code: 10000

---


## 4.記憶體結構（ Memory Architecture）

初期設置：
固定記憶體：血量
短期記憶體（RAM)
長期記憶體（初期無）
---

## 5.Register運算（ Register-Based Computation (Optional Layer)）

Register運算作為擴展功能

Advanced hamsters can use registers for temporary computation:

- ALU operations on binary sequences
- Conditional branching simulated via indirect memory checks
- Future plans may include: ADD, XOR, SHIFT encoded in higher spiral layers

---

## 6. 模擬代碼（Code Simulation (C++ Example)）

Below is a simplified VM loop example (full code in `vm.cpp`):

```cpp
// Pseudocode


