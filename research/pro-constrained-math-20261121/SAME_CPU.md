# Same CPU, identical frame boundary

The original recurrent four-operation network was lowered directly to RV32I. Every nonzero input coefficient and every signed readout is implemented by the binary, with integer thresholds evaluated on every round. In the same instruction simulator and ABI, each image was executed on all 49,152 legal frames and produced the same complete 57-bit answers, with canonical stream digest a3292bbad3e44fcf81ac0fa5af152af2cf497ac31c33e1af1eda48c30fe77f23.

| Deployment | ROM bytes | Scratch RAM bytes, beyond packed IO | Total instructions retired | Mean per case |
|---|---:|---:|---:|---:|
| Direct fixed-weight evaluation, RV32I | 46,556 | 1,248 | 5,147,489,280 | 104,725.94 |
| Task-specific arithmetic, RV32I | 292 | 0 | 2,506,048 | 50.99 |
| Task-specific arithmetic, RV32I+Zmmul | 264 | 0 | 1,940,160 | 39.47 |

The 2,054× ratio on base RV32I applies to these specific binaries and instruction counts. The neural image is a direct unrolled implementation, not the best possible compiler. Total CPU silicon area, per-instruction cycle timing, energy and a complete four-operation hardwired implementation remain unmeasured. The first comparison in README.md demonstrates why lowering to a fixed circuit can change the outcome for a simpler task.
