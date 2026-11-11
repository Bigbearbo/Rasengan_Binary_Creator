# Spiral Language Parser — executable research prototypes (v0.1–v0.6)

These scripts are successive independent experiment layers, **not** one production-stable protocol and **not** neural language acquisition. The original artifacts were archived under ChatGPT Library `/倉鼠世界/螺旋語解析器_雙代理模擬_20261103/`. Sources first published from those dated artifacts on 2026-11-11.

## What is inside

`spiral_parser.py` implements fixed-profile bit-word parsing and a stored syntax tree. `spiral_dialogue.py` through `spiral_dialogue_v03.py` add scripted teacher/student communication, version handling, and persistent question-bank state. `spiral_tree_packet_v04.py` adds whole-tree snapshots and error recovery. `spiral_tree_packet_v05.py` adds delta packets and high-water re-encoding. `spiral_tree_nodes_v06.py` corrects **where the high-water mark is stored**: it lives inside `state.tree.math.operator_branch.highwater`, rather than a separate authoritative registry. Previous versions are **historical evidence**; do not silently rewrite them or present them as current semantics.

The two agents are **scripted** with prior knowledge of some message framing and a restricted function hypothesis library. There was no training of an uninitialized neural network. `fixtures/` contains small dated examples, not training labels for unrestricted evaluation.

## Re-run

From this folder (Python 3.10+, standard library only):

```bash
python -m unittest -q   test_spiral_parser test_spiral_dialogue test_spiral_dialogue_v02   test_spiral_dialogue_v03 test_spiral_tree_packet_v04   test_spiral_tree_packet_v05 test_spiral_tree_nodes_v06
python demo_branch_v06.py
```

2026-11-11 migration check: **75/75 tests passed** after extracting the original v0.6 archive. These validate the Python prototypes, not an LLM learning result.

## Protocol scope and guardrails

- Any bit-stream parse relies on applicable profile (`k`, `n`, word offset, message schema, version). Unrecognized syntax must not be committed as a confirmed semantic node.
- Keep **highest-ever-allocated** operator ID at each tree branch, not just `len(operators)` or `max(current operator IDs)`. Do not shrink it after deletion.
- Preserve old version encodings; generate new ones by profile while keeping semantic identities stable.
- Sync public tree nodes via verified whole/delta packets without overwriting the learner's private `question_bank`.
- A successful tree transfer does not imply transferred operator semantics can be executed by a new model; executable payloads would need explicit validation and sandboxing.
- Older packet headers have documented version-width limits; do not assert arbitrary unbounded extension has been implemented.

See `../../docs/spiral_language_vs_icfp2020_for_codex.md` (if moved to nested docs paths adjust this relative link).