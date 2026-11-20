# Learning to merge eight addition rounds into four

This component experiment starts with a mastered one-column addition readout. The student can use its own consecutive fine decisions as local training examples for a new two-column cell. A separately trained readout chooses a one-column read, a two-column read, or STOP. During joint evaluation the classifier acts at the student's current cursor and the arithmetic cell receives the student's own carry.

With four whole examples per arithmetic seed and the affine-in-five-bits structure plus constant, all 16 fitted arithmetic cells computed every legal intermediate result and exact final nine-bit sum on every ordered pair of bytes. Paired human-specified coarse labels and the fine student's own merged labels were identical. An unconstrained 32-context lookup learner scored 0/16 full solutions at four examples, 12/16 at 64. A bounded exhaustive search of 15,625 candidate integer affine cells also identified a unique working solution from four **final answers only** in all 16 seeds. Output binary interpretation, model class, choice of possible widths, and the pre-existing fine cell are provided. These outcomes reflect a small structured task.

With constant read banks, all 16 paired learned arithmetic and round-cost policies completed every addition in four arithmetic updates and one STOP decision. Final-answer-only controller training retained eight updates. If adjacent columns in either operand change banks, a wide read is physically illegal. The round-cost policy correctly varied the read size across all 65,536 width-eight layout pairs, with one operand pair per layout; a fixed two-column policy succeeded on 256 layouts. In three named layouts every operand pair was tested, yielding four or five arithmetic updates according to the observed tags. The archived handfilled T3 teacher independently checked student drafts. Arithmetic updates, physical reads and terminal decisions have separate costs. Calendar time or silicon speedup has not been measured.

## Reproduce

Use Python 3.12, NumPy and SciPy. The complete private project archive identified by ARCHIVE.txt contains the original T3 sources at teacher/upstream/, expected results, trained checkpoints, raw bytes and source hash ledger. In a clean working copy of this directory with those original teacher sources, run:

```sh
export OPENBLAS_NUM_THREADS=1
python -B arithmetic.py
python -B endpoint.py
python -B check_endpoint.py endpoint.json
python -B policy/stride.py --output policy/result.json
python -B policy/check_policy.py policy/result.json --output policy/checked.json
python -B policy/recover.py policy/result.json --output policy/recovery.json
python -B joint.py
python -B teacher/verify_teacher.py
```

The arithmetic runner includes its source and ARITHMETIC_PROTOCOL.md hashes in its output. Keep both unchanged when comparing the JSON digest to the private archive. The code specifies training seeds, ordered sample generation, all budgets, negative controls and scoring rules. The original T3 modules are provided only through the project exchange.
