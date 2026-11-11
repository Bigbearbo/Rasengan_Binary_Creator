# Archived bit-message codecs / framing helpers (2026-11-01)

These are original teaching experiment tools, preserved separately from later protocol prototypes. They do not prove an untrained neural learner acquired SLE.

```bash
python spiral_converter.py test  # 2040 round-trips
python spiral_wire.py test       # 262112 framing round-trips
node test_js.cjs                # 32736 JavaScript round-trips
```

During migration on 2026-11-11 all commands above ran and passed. The `spiral_wire` 16-one marker is an *early transport framing shortcut*, not SLE's native token segmentation. The converter requires known `n` and `k` and does not infer arbitrary unknown grammar.
