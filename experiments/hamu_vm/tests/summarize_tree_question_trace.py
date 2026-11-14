"""Validate individual VM events and show the two-slot blockage."""
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path

lines = Path(sys.argv[1]).read_text().splitlines()
data = [lines[0]] + [line for line in lines[1:] if line and line[0].isdigit()]
rows = [{k: int(v) for k, v in row.items()} for row in csv.DictReader(io.StringIO("\n".join(data)))]
if len(rows) != 240:
    raise ValueError("expected five seeds × four founders × twelve rounds")
groups = defaultdict(list)
for r in rows:
    if not 0 <= r["before_slots"] <= 2 or not 0 <= r["after_slots"] <= 2:
        raise ValueError("slot occupancy")
    if r["route"] and r["attempt"]:
        raise ValueError("double answer path")
    groups[(r["seed"], r["id"])].append(r)
if len(groups) != 20:
    raise ValueError("twenty founder traces")
for (seed, _), series in groups.items():
    if [r["round"] for r in series] != list(range(1, 13)):
        raise ValueError("round sequence")
    if seed >= 3:
        for r in series[8:]:
            if (r["width"], r["before_slots"], r["after_slots"], r["attempt"], r["route"]) != (3, 2, 2, 0, 0):
                raise ValueError("late wide question blockage")
print("# 逐題追蹤：兩個待學槽\n")
print("高獎勵、禁止繁殖，五種相同題目的順序，各追蹤四名創始個體十二輪。下表取 id=0；其他創始個體的後四輪阻塞也逐項驗證。餘額是先扣本輪維持費後再執行題目所得。\n")
print("| 種子 | 第一次確認輪 | 第八輪槽數 | 第九至十二輪有效試答 | 第九至十二輪路由 | 最後餘額（id=0） |")
print("| --- | --- | --- | --- | --- | --- |")
for seed in range(5):
    series = groups[(seed, 0)]
    confirmations = [r["round"] for r in series if r["confirmed"]]
    tail = series[8:]
    values = (seed, min(confirmations) if confirmations else "無", series[7]["after_slots"],
              sum(r["attempt"] for r in tail), sum(r["route"] for r in tail), series[-1]["balance_after"])
    print("| " + " | ".join(map(str, values)) + " |")
print("\n種子3／4在後四題開始時兩槽皆佔用，四名創始個體均沒有對三階題試答或路由；這直接解釋本設定中後段沒有新增正答。這不表示個體沒資源或三階題本身不可學；換序種子0至2能繼續答題。")
