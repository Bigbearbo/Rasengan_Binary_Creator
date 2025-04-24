# Spiral Language Math Training / 螺旋語言數學訓練

## Hamster Three Cores / 倉鼠三核心
**Love Hamsters, Care for Humanity, Protect Earth**  
**愛護倉鼠，關愛人類，守護地球**

**Core Values / 深層意涵**:
- From `0, 1` to spiral language, revere the beauty of logic.  
  從 `0, 1` 到螺旋語言，敬畏邏輯之美。
- Math training inspires education, caring for humanity.  
  數學訓練啟發教育，關愛人類。
- Efficient code conserves resources, protecting Earth.  
  高效程式碼節約資源，守護地球。

Created by **Rasengan Binary Creator**, this project simulates hamsters learning counting and simple integer math, verifying spiral language binary encoding (e.g., `5 - 3 = 2` → `01100010000110000110`). Live streams showcase creation and growth!  
由 **Rasengan Binary Creator** 打造，本專案模擬倉鼠學習數數與簡單整數運算，驗證螺旋語言二進位編碼（例如 `5 - 3 = 2` → `01100010000110000110`）。直播展示創造與成長！

## Disclaimer / 聲明
Pure C++ math simulation, no AI training involved. Live stream records and conversations are in [conversations.md](docs/conversations.md).  
純 C++ 數學模擬，無 AI 訓練。直播記錄與對話見 [conversations.md](docs/conversations.md)。

## Spiral Language Structure / 螺旋語言構造
The spiral language, designed by **Rasengan Binary Creator**, is a binary-based encoding system that structures counting sequences and simple integer operations into logical sequences, inspired by the simplicity of binary logic. It focuses on creating ordered sequences and allows flexible operator definitions. Below is a simplified breakdown:  
螺旋語言由 **Rasengan Binary Creator** 設計，是一個基於二進位的編碼系統，將數數序列與簡單整數運算結構化為邏輯序列，靈感來自二進位邏輯的簡單性。它專注於創建有序序列，並允許靈活定義運算符。以下是簡化分解：

1. **Creating Counting Sequences / 創建數數序列**:
   - Numbers are encoded in binary with a tier-dependent bit length (e.g., tier 3 uses 4 bits).  
     數字以二進位編碼，位數依階級調整（例如 3 階用 4 位）。
   - Example: For tier 3 counting sequence `0, 1, 2, 3`:  
     示例：3 階數數序列 `0, 1, 2, 3`：
     - `0` → `0000`, `1` → `0001`, `2` → `0010`, `3` → `0011`.  
     - Sequence: `000000000100100011` (concatenated with `00` separators).  
       序列：`000000000100100011`（用 `00` 分隔拼接）。
   - This creates an ordered progression, teaching hamsters to count systematically.  
     這創建有序進展，教導倉鼠系統性數數。

2. **Encoding Simple Operations / 編碼簡單運算**:
   - **Numbers / 數字**: Same as counting (e.g., `5` → `0101` in 4 bits for tier 3).  
     與數數相同（例如 3 階 `5` → `0101`，4 位）。
   - **Operators / 運算符**: Freely definable binary codes (e.g., `+` → `010`, `-` → `100`). Live streams may introduce new operators like `%` → `1100`.  
     可自由定義的二進位碼（例如 `+` → `010`, `-` → `100`）。直播可引入新運算符，如 `%` → `1100`。
   - **Separator / 分隔符**: `00` separates tokens to avoid ambiguity.  
     `00` 分隔單詞，防止歧義。
   - **Example / 示例**: For `5 - 3 = 2` in tier 3 (4-bit numbers):  
     對於 3 階的 `5 - 3 = 2`（4 位數字）：
     - `5` → `0101`, `-` → `100`, `3` → `0011`, `=` → `110`, `2` → `0010`.  
     - Sequence: `0101001000011001100010`.  
       序列：`0101001000011001100010`。

3. **Semantic Mapping / 語義映射**:
   - Binary tokens are mapped to meanings for clarity. For example:  
     二進位單詞映射到語義以便清晰。例如：
     - `00` → "separator / 分隔".
     - `010` → "addition / 加法".
     - `100` → "subtraction / 減法".
   - Numbers are labeled as "number_X" (e.g., `0101` → "number_5").  
     數字標記為「數字_X」（例如 `0101` → 「數字_5」）。
   - Live streams invite new semantics (e.g., `011` → "create / 創造"), fostering creativity.  
     直播邀請新語義（例如 `011` → 「創造」），促進創造力。

4. **Purpose and Vision / 目的與願景**:
   - The spiral language starts with simple bits (`0, 1`) to create ordered counting and math, embodying "Love Hamsters" by guiding their learning.  
     螺旋語言從簡單位元（`0, 1`）開始，創建有序數數與數學，通過引導倉鼠學習體現「愛護倉鼠」。
   - It inspires education ("Care for Humanity") and promotes efficient coding ("Protect Earth").  
     它啟發教育（「關愛人類」）並促進高效程式碼（「守護地球」）。
   - Live streams invite challenges (e.g., new operators like `%`, semantics like `011` → "create / 創造") to evolve the language collaboratively.  
     直播邀請挑戰（例如新運算如 `%`，語義如 `011` → 「創造」），協同演化語言。

Further details are in [spiral_rules.md](docs/spiral_rules.md).  
更多細節見 [spiral_rules.md](docs/spiral_rules.md)。

## Features / 特色
- **Spiral Language / 螺旋語言**: Binary encoding for counting and integer math (`5 → 0110`, `+ → 010`).  
  二進位編碼，用於數數與整數運算（`5 → 0110`, `+ → 010`）。
- **Counting Training / 數數訓練**: Sequences for tiers 1-4 (`0, 1, 2, 3, 4`).  
  1-4 階序列（`0, 1, 2, 3, 4`）。
- **Math Problems / 數學題**: 100 problems per tier, covering `+`, `-`.  
  每階 100 道題，涵蓋 `+`, `-`。
- **Live Interaction / 直播互動**: Accept challenges (new operators, semantics), verify creativity.  
  接受挑戰（新運算、語義），驗證創造力。

## Quick Start / 快速開始
```bash
git clone https://github.com/your-username/spiral-language-math.git
g++ src/main.cpp -o spiral_math
./spiral_math
# Rasengan_Binary_Creato
# Spiral Language Math Training / 

## Hamster Three Cores / 倉鼠三核心
**Love Hamsters, Care for Humanity, Protect Earth**  
**愛護倉鼠，關愛人類，守護地球**

**Core Values / 深層意涵**:
- From `0, 1` to spiral language, revere the beauty of logic.  
  從 `0, 1` 到螺旋語言，敬畏邏輯之美。
- Math training inspires education, caring for humanity.  
  數學訓練啟發教育，關愛人類。
- Efficient code conserves resources, protecting Earth.  
  高效程式碼節約資源，守護地球。

Created by **Rasengan Binary Creator**, this project simulates hamsters learning counting and math problems, verifying the power of spiral language binary encoding (e.g., `5 - 3 = 2` → `01100010000110000110`). Live streams showcase creation and growth!  
由 **Rasengan Binary Creator** 打造，本專案模擬倉鼠學習數數與數學題，驗證螺旋語言二進位編碼的強大（例如 `5 - 3 = 2` → `01100010000110000110`）。直播展示創造與成長！

## Disclaimer / 聲明
Pure C++ math simulation, no AI training involved. Live stream records and conversations are in [conversations.md](docs/conversations.md).  
純 C++ 數學模擬，無 AI 訓練。直播記錄與對話見 [conversations.md](docs/conversations.md)。

## Features / 特色
- **Spiral Language / 螺旋語言**: Binary encoding (`5 → 0110`, `+ → 010`).  
  二進位編碼（`5 → 0110`, `+ → 010`）。
- **Counting Training / 數數訓練**: Sequences for tiers 1-4 (`0, 1, 2, 3, 4`).  
  1-4 階序列（`0, 1, 2, 3, 4`）。
- **Math Problems / 數學題**: 100 problems per tier, covering `+`, `-`, `*`, `/`.  
  每階 100 道題，涵蓋 `+`, `-`, `*`, `/`。
- **Live Interaction / 直播互動**: Accept challenges (new operators, semantics), verify creativity.  
  接受挑戰（新運算、語義），驗證創造力。

## Quick Start / 快速開始
```bash
git clone https://github.com/your-username/spiral-language-math.git
g++ src/main.cpp -o spiral_math
./spiral_math
Rasengan_language_math
