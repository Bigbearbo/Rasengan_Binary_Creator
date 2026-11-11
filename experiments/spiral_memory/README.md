# Natural-language Spiral Memory — public parser prototype (SNL-MEM-0.2)

This is a **human-readable experimental grammar** with nested scopes, vocabulary expansion, provenance/dependency tracking, and explicit end markers. It is **not** the bitwise SLE token codec and has not been shown to improve AI long-term memory or neural learning.

`spiral_core.py` originates from a separate ChatGPT Library research experiment in `/AI研究記憶/螺旋語記憶_平行實驗/v0.2_底層語法/`. The original offline test corpus contains mixed historical research notes, so **only code and a new synthetic public test** have been published here. These six public tests ran successfully on 2026-11-11.

```bash
python -m unittest -v test_spiral_core_public
```

The earlier full 32-assertion comparison used a separate real research-memory dataset and should not be conflated with these synthetic fixtures. See parser source comments, and do not infer superiority to Markdown from byte-size comparisons of semantically non-identical records.

## 擴充研究資料（2026-11-12）

使用者 Library 內的平行記憶實驗已另外建立 [research_archive_20261102/](research_archive_20261102/) 公開衍生版本：v0.1、v0.2 的測試、比較報告、AI 直讀與 R02 詞表。內含部分識別碼／來源路徑替換，舊測試數值不得直接引用為新資料。原本的六個純合成測試及此目錄既有 `spiral_core.py` 仍是快速公共入口。不要把公開化衍生語料回填到使用者私人正式記憶。
