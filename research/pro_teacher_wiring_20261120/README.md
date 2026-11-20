# Teaching an eight-bit borrow student

Can a handfilled borrow gate tell a student which inputs to attend to? Once a student stalls, does it matter which intermediate answer the teacher supplies? The two studies use independent cohorts. Each student shares a frozen 19-unit S1 adder, reads its own previous borrow bit, and takes eight rounds per example. The tested answer is unsigned A < B. A perfect student produces the exact borrow bit at **every round on all 65,536 ordered byte pairs**.

## Temporary wiring

Sixteen paired seeds received 64 distinct examples each, labeled with the final comparison only. All learned coefficients started at zero. The student sockets were physically permuted, with semantic names shared between teacher and student. The teacher supplied three port names (and, in one arm, their signs). Bias and coefficient magnitudes were learned.

| Inputs open to the student | Perfect after 64 updates | Perfect after 256 |
|---|---:|---:|
| All 19 inputs and bias throughout | 0/16 | 0/16 |
| Three blind ports and bias, then all inputs | 1/16 | 1/16 |
| Three teacher ports and bias, then all inputs | 10/16 | 10/16 |
| Three teacher ports with signs and free bias, then all inputs and signs free | 13/16 | 13/16 |
| Three teacher ports and bias throughout | 10/16 | 14/16 |

The one successful blind draw selected the actual teacher ports. Of the six unsigned teacher-port students still imperfect at 64 updates, four eventually passed with the scaffold in place and none passed after release. In a post-training analysis, keeping only the teacher ports and the student's learned bias made 7/16 unrestricted students perfect without further training. That intervention used the teacher's known wiring.

## Targeted remediation

In a fresh cohort with the three teacher ports, 37/64 students were already perfect at 256 updates. The remaining 27 had endpoint errors on their own training examples. Their checkpoints were cloned, and each arm supplied one target for each training example at every update. For erroneous answers the target could be a final answer or the answer at a selected intermediate step. Each arm reassessed its own errors. Correct endpoint answers kept final-label supervision throughout.

| Supervision on erroneous examples | Perfect after 32 remedial updates | Perfect after 64 further endpoint-only updates |
|---|---:|---:|
| Continue final labels | 1/27 | 1/27 |
| Uniformly random step | 23/27 | 24/27 |
| First incorrect step | 27/27 | 27/27 |
| Uniformly random incorrect step, added after seeing the main results | 26/27 | 26/27 |

The first-error arm issued 2,438 hints, the random-step arm 7,747, and the random-incorrect-step arm 5,578. Selecting a genuinely incorrect step requires an oracle that can inspect intermediate predictions. The choice of index also carries information. The one-student difference between the two wrong-step arms leaves the particular value of the earliest position uncertain. The original S1 nine-bit sum and stop schedule remained exact on the full byte domain. Generalization to wider numbers, new operations or learned socket names remains to be tested.

## Replay

Use the intact authorized study archive named `sle_wiring_remediation_20261120_v1.zip`. It contains the original S1, previous experiment code, expected results, and the input and checkpoint records used for verification. Published code paths in this folder match their locations inside the ZIP. The archive contains the detailed protocols expected by the scripts in addition to the two public preregistrations here.

From this repository's root, on a machine with Python 3.12.14, NumPy 2.3.5 and SciPy 1.17.0, run the commands below. Replace the ZIP path with the local path to the authorized copy. The comparison checks that each public script has exactly the same bytes as the archived version. The runner then verifies the archive hashes and uses a temporary working directory for training and evaluation.

```sh
archive=/path/to/sle_wiring_remediation_20261120_v1.zip
study=research/pro_teacher_wiring_20261120
replay_dir="$(mktemp -d)"
python -m zipfile -e "$archive" "$replay_dir"
for src in replay.py transfer.py audit_transfer.py audit.py remedial/remedial.py remedial/explore_wrong.py remedial/check_scores.py
do
    cmp "$study/$src" "$replay_dir/$src" || exit 1
done
python -B "$replay_dir/replay.py"
```

A full run ends with `PASS: 9 byte-for-byte reproductions; archived inputs unchanged.` Training and scoring use CPU and require no network calls. The archive includes the prior study code and private reference records needed to run this check.

| File | Role |
|---|---|
| `PROTOCOL.md`, `REMEDIAL_PROTOCOL.md` | Public preregistrations for the two main studies |
| `replay.py` | Verify hashes, reproduce the prior baseline, run training and all audits |
| `transfer.py` | Train five paired arms, score checkpoints at 0, 64 and 256 updates |
| `audit_transfer.py` | Check all 240 wiring checkpoints against a separate reference |
| `audit.py` | Rebuild the board with integer shifts, recheck the 80 final models, test pruning |
| `remedial/remedial.py` | Branch the stalled students into the three preregistered teaching conditions |
| `remedial/explore_wrong.py` | Run the additional random-incorrect-step comparison |
| `remedial/check_scores.py` | Check 354 remediation checkpoints across the main and exploratory arms by an independent state-counting method |
