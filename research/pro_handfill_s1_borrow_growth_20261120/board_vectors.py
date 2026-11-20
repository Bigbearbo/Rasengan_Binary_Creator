"""Create reference vectors for S1's internal board; these are not SLE language frames."""
import argparse
import hashlib
import struct
from pathlib import Path

RECORD = struct.Struct("<I H B B B")
def build():
    data = bytearray()
    for a in range(256):
        for b in range(256):
            carry = 0
            carries = 0
            exactly_two = 0
            borrows = 0
            for k in range(8):
                value = ((a >> k) & 1) + ((b >> k) & 1) + carry
                carry = int(value >= 2)
                carries |= carry << k
                exactly_two |= int(value == 2) << k
                mask = (2 << k) - 1
                borrows |= int((a & mask) < (b & mask)) << k
            board = a | (b << 8) | (1 << 16)
            data.extend(RECORD.pack(board, a+b, carries, exactly_two, borrows))
    return data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    reference = build()
    args.output.write_bytes(reference)
    print(f"{len(reference)} bytes; SHA256 {hashlib.sha256(reference).hexdigest()}")
