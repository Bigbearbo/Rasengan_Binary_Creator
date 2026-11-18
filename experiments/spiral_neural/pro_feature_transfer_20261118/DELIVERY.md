# Immutable archive and packaged replay

Run: `pro_feature_transfer_20261118_v1`

Archive: `sle_feature_transfer_20261118_v1.zip`  
Size: **69,558,801 bytes**  
SHA256: `88afb3c9072a29b90382ab25281757c9e682ae68c37e5d71eb181c9c0a01a855`  
Members:289; hashed payload files:288; ZIP CRC:PASS.

The complete archive has been saved in the owner's research exchange and its exact filename and byte count were independently listed. It contains source copies, data/splits, paired batch streams, all81 checkpoints, full predictions/features, failures, reports and verification receipts. Obtain this exact archive from the owner; the public repository does not contain the weights or large caches.

## Replay

```bash
python replay_archive.py /path/to/sle_feature_transfer_20261118_v1.zip --receipt /path/to/new_replay_receipt.json
```

[replay_archive.py](replay_archive.py) pins the archive identity, checks every member/hash and CRC, extracts to a new temporary directory, restores original nanosecond mtimes, and executes the independent verifier. The old audit receipt is retained under another name in the temporary extraction. The released ZIP/checkpoints stay unchanged.

The packaged replay was actually executed on the immutable ZIP and passed. See [packaged_replay_receipt.json](packaged_replay_receipt.json):289 members and288 payload hashes verified; all99 prediction files/272,016rows,27 feature caches/121,104rows and9,360source readouts rechecked. It repeats144 early optimizer recurrences for verification and performs **zero new experimental updates**; no full training repeat or model continuation.

The original independent audit and this packaged replay each use144 diagnostic recurrences (288 total verification recurrences in this delivery). The experiment itself remains36,864 updates. Exact environment:Python3.12.14,NumPy2.3.5; one BLAS thread.

Preregistration:4798c3a4dbd15d0b3c00b90581092536102a88c4. Source lock:23e738f4491fa755d6152491cc5a78f82824e99d. Results:d3851ff0496515e45683b15c98f37250c33f338d.

A successful archive save and replay do not constitute a Windows receipt. Dot transport acceptance remains separate from scientific verification.
