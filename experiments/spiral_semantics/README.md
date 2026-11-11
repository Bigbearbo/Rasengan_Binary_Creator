# SLE exploratory semantics and lexicon experiments (SL09–SL18)

Independent Python studies, mostly symbolic/synthetic. They are **not** the production parser, proof that SLE is better than ICFP 2020, or a neural learner. The numbered scripts explore history root snapshots, recursive definitions, slot generations, lexicon upgrade alternatives A/B, scoping/semantic drift, dictionary synchronization, ICFP 2020 modulation as a transport DATA representation, hot concepts, and multiple receivers.

The upstream source is ChatGPT Library `/倉鼠世界/螺旋語_跨模型純01實驗/`. Preserve original filenames: later scripts import specific sibling files (notably SL16 needs SL14 and SL15; SL18 needs SL17).

Run Python 3.10+ with these files in one directory. Samples:
```bash
python 'SL16_獨立詞典同步與ICFP雙向Modulation驗證.py'
python 'SL18_多接收者詞典提升策略與離線成本驗證.py'
```
During migration on 2026-11-11, all Python files were syntax-compiled; SL16 and SL18 were invoked successfully. Other scripts were not individually rerun here. Distinguish modeled cost assumptions from real network/CPU measurement.
