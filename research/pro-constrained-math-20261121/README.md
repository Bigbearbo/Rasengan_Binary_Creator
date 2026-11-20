# Constrained arithmetic service comparison

The 20-unit hand-filled serial adder with a borrow bit and a conventional independently specified serial adder/borrow machine can be lowered to identical fixed LUT4 netlists. Both use 22 LUT4 and 19 flip-flops with synchronous parallel input load, one load edge and eight work edges. Adding the less-than output to the existing nine-bit sum costs both designs one LUT4, one FF and zero extra edges. The full-state equivalence test covers 524,288 internal states; endpoint tests cover all 65,536 byte pairs. These are abstract fixed netlists, not placed silicon, and assume fixed weights after compilation.

For the full 7-bit arithmetic language profile, all 49,152 legal 201-bit questions and all 57 bits of every answer matched between the original 358-unit four-operation network and both RV32 programs. The RV32I program including the framing code fits in 292 bytes; the otherwise identical target with multiplication instructions takes 264. Both use software division. Program sizes exclude CPU silicon and the memory-mapped IO window. Neural update rounds and retired CPU instructions are different cost units.

| Operation | Cases | Neural rounds | RV32I instructions | RV32I+Zmmul instructions |
|---|---:|---:|---:|---:|
| ADD | 8,256 | 2 | 27 | 27 |
| SUB | 8,256 | 2 | 29 | 29 |
| MUL, full product | 16,384 | 3–9 | 38–80 | 37 |
| DIV, quotient and remainder | 16,256 | 18 | 48–116 | 48–116 |

The same arithmetic routines with already-decoded operands are 180 and 152 bytes. Full framing adds 112 bytes to either program. Both frame generators match 128 actual input frames from the original ×3 teacher export. The full domain uses independent canonical generators and arithmetic checks. The standalone original scorer was unavailable; the actual four-op network weight hash was verified against the upstream receipt and the complete outputs were compared. There are no gradient updates or learning claims.

Run the public elementary example with `python bit_arithmetic.py`. It uses only single-bit multiplication and truncated single-bit addition for transitions, jointly producing unsigned less-than and nine-bit sum for all 65,536 byte pairs. Fixed pin selection and the loop environment are outside that gate count.

The private archive includes full-frame firmware and machine code, simulators, original weight builders, fixed checkpoint, packed cases, exact outputs, netlists, SHA-256 list, and the top-level command `python -B replay_all.py`. The archive identity will appear in ARCHIVE.md. A full-device size, timing or energy ranking needs a separate common target and complete implementation.
