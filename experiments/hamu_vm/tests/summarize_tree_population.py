"""Validate all censuses and summarize either 12-round question schedule."""
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path

lines = Path(sys.argv[1]).read_text().splitlines()
mode = sys.argv[2] if len(sys.argv) > 2 else "fixed"
if mode not in ("fixed", "varied"):
    raise ValueError("mode must be fixed or varied")
start = next(i for i, line in enumerate(lines) if line.startswith("reward,breeding,reverse,"))
data = [lines[start]]
for line in lines[start + 1:]:
    if not line or not line[0].isdigit():
        break
    data.append(line)
rows = [{k: int(v) for k, v in row.items()} for row in csv.DictReader(io.StringIO("\n".join(data)))]
if len(rows) != 96:
    raise ValueError("Expected 96 complete censuses")
groups = defaultdict(list)
for row in rows:
    if row["balance"] != 200000 + row["rewarded"] - row["spent"]:
        raise ValueError("Resource conservation failed")
    if row["living"] != 4 + row["births"] - row["retired"] or not 0 <= row["living"] <= 8:
        raise ValueError("Population conservation failed")
    if sum(row[k] for k in ("off", "on", "after_failure", "reserve")) != row["living"]:
        raise ValueError("Policy census mismatch")
    if row["rewarded"] != row["reward"] * row["correct_answers"]:
        raise ValueError("Reward must follow actual answers")
    groups[(row["reward"], row["breeding"], row["reverse"])].append(row)
print("# 十二輪有限族群對照：" + ("變動題庫" if mode == "varied" else "單題") + "\n")
print("每次從四個各持有 50000 資源的創始個體開始；出生從親代轉移，沒有新生資源注入。\n")
if mode == "varied":
    print("每輪同一題提供所有存活個體，三種二階算符先交錯出題，第九輪起單向升到三階。片段表為有效 ZERO／XOR1／COPY／FLIP；這組沒有永久故障片段，與單題組的政策比較不可視為同一條件的效果。\n")
print("| 正答獎勵 | 繁殖 | 創始順序反轉 | 存活 | 出生 | 耗盡退場 | 關／開／失敗後／資源條件 | 最終資源 | 實際正答 |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for key, series in sorted(groups.items()):
    if [row["round"] for row in series] != list(range(1, 13)):
        raise ValueError("Missing rounds")
    row = series[-1]
    counts = "／".join(str(row[k]) for k in ("off", "on", "after_failure", "reserve"))
    values = (*key, row["living"], row["births"], row["retired"], counts, row["balance"], row["correct_answers"])
    print("| " + " | ".join(map(str, values)) + " |")
if len(groups) != 8:
    raise ValueError("Expected all eight controls")
print("\n政策沒有突變，只有既有政策在有限條件下的差異繁殖；十二輪結果不證明長期演化或一般最優策略。")
