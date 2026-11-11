# Natural-language Spiral Memory — public parser prototype (SNL-MEM-0.2)

This is a **human-readable experimental grammar** with nested scopes, vocabulary expansion, provenance/dependency tracking, and explicit end markers. It is **not** the bitwise SLE token codec and has not been shown to improve AI long-term memory or neural learning.

`spiral_core.py` originates from a separate ChatGPT Library research experiment in `/AI研究記憶/螺旋語記憶_平行實驗/v0.2_底層語法/`. The original offline test corpus contains mixed historical research notes, so **only code and a new synthetic public test** have been published here. These six public tests ran successfully on 2026-11-11.

```bash
python -m unittest -v test_spiral_core_public
```

The earlier full 32-assertion comparison used a separate real research-memory dataset and should not be conflated with these synthetic fixtures. See parser source comments, and do not infer superiority to Markdown from byte-size comparisons of semantically non-identical records.
