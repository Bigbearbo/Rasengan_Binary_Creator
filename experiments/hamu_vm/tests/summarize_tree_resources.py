"""Summarize the controlled resource sweep; final balance is the stated objective."""
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path

text = Path(sys.argv[1]).read_text()
lines = text.splitlines()
start = next(i for i, line in enumerate(lines) if line.startswith("initial,observation_fee,"))
table = [lines[start]]
for line in lines[start + 1:]:
    if not line or not line[0].isdigit():
        break
    table.append(line)
rows = [{key: int(value) for key, value in row.items()} for row in csv.DictReader(io.StringIO("\n".join(table)))]
if len(rows) != 32:
    raise ValueError("Expected all 32 resource scenarios")
groups = defaultdict(list)
for row in rows:
    if row["balance"] != row["initial"] + row["rewarded"] - row["spent"]:
        raise ValueError("Account conservation failed")
    groups[(row["initial"], row["observation_fee"], row["reward"])].append(row)
names = {0: "固定關閉", 1: "固定開啟", 2: "失敗後開啟", 3: "失敗後且資源足夠"}
print("# 四題後資源餘額比較\n")
print("目的固定為最大化最終餘額；答對數另列，不把不答題的低花費稱為學習成功。費率為實驗參數。\n")
print("| 初始資源 | 每觀察費 | 正答獎勵 | 餘額最高政策 | 最終餘額 | 答對數 |")
print("| --- | --- | --- | --- | --- | --- |")
for key, group in sorted(groups.items()):
    if {r["policy"] for r in group} != set(names):
        raise ValueError("Missing or duplicated policy")
    best = max(r["balance"] for r in group)
    winners = [r for r in group if r["balance"] == best]
    print("| " + " | ".join(map(str, (*key, "、".join(names[r["policy"]] for r in winners), best,
        "、".join(str(r["correct"]) for r in winners)))) + " |")
print("\n低獎勵保留資源與高獎勵積極答題可能有不同優勢；本表不表示已演化出政策，也不計物理耗時或舊 HP 模型。")
