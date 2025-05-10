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

初期5個指令使用一層三階螺旋語

Each instruction is encoded in spiral code with distinct prefixes:

| Command   | Spiral Prefix | Description                     |
|-----------|----------------|---------------------------------|
| READ      | `1000         | Read value from memory address  |
| WRITE     | `0110          | Write value to memory address   |
| EMIT      | `0100         | Output a value                  |
| CONTINUE  | `0010          | Continue computing (no output)  |
| STOP      | `0000         | Stop execution and cleanup      |

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

#### 數字（0～12）

| 數字 | 資料位 | 螺旋碼詞 |
|------|--------|-----------|
| 0    | `0000` | `00000`   |
| 1    | `0001` | `00010`   |
| 2    | `0010` | `00100`   |
| 3    | `0011` | `00110`   |
| 4    | `0100` | `01000`   |
| 5    | `0101` | `01010`   |
| 6    | `0110` | `01100`   |
| 7    | `0111` | `01110`   |
| 8    | `1000` | `10000`   |
| 9    | `1001` | `10010`   |
| 10   | `1010` | `10100`   |
| 11   | `1011` | `10110`   |
| 12   | `1100` | `11000`   |

#### 運算符號（保留位）

| 符號 | 資料位 | 螺旋碼詞 | 說明     |
|------|--------|-----------|----------|
| `+`  | `1101` | `11010`   | 加號     |
| `→`  | `1110` | `11100`   | 下一數   |
| `.`  | `1111` | `11110`   | 結束句號 |

---

### 範例題目 1：`8 + 3.`

| 元素 | 螺旋碼詞 |
|------|-----------|
| 8    | `10000`   |
| +   | `11010`   |
| 3    | `00110`   |
| .   | `11110`   |

> **螺旋語表示：** `10000 11010 00110 11110`  
> **答案：10110(11)**

---

### 範例題目 2：`5 + 6.`

| 元素 | 螺旋碼詞 |
|------|-----------|
| 5    | `01010`   |
| +   | `11010`   |
| 6    | `01100`   |
| .   | `11110`   |

> **螺旋語表示：** `01010 11010 01100 11110`  
> **答案：10110(11)`

（可選）數學題目用二層螺旋碼描述，如100接在題目最左側，方便之後轉化其他形式的輸入或題目



## 倉鼠接收數學題任務流程設計（初期）

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
～～～～～～～～～～～～

---


## 4.記憶體結構（ Memory Architecture）

Hamsters operate using three memory types:

- **Fixed Memory**: Read-only genetic info (e.g., race, base stats)
- **Long-Term Memory**: Writable, disk-speed (used for knowledge accumulation)
- **Short-Term Memory**: RAM-like, fast but volatile

Memory is accessed via bit-addressed fields encoded in spiral format.

---

## 5.Register運算（ Register-Based Computation (Optional Layer)）

Advanced hamsters can use registers for temporary computation:

- ALU operations on binary sequences
- Conditional branching simulated via indirect memory checks
- Future plans may include: ADD, XOR, SHIFT encoded in higher spiral layers

---

## 6. 模擬代碼（Code Simulation (C++ Example)）

Below is a simplified VM loop example (full code in `vm.cpp`):

STOP 0           → [End of program]

