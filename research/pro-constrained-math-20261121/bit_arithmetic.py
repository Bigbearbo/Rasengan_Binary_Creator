"""Two arithmetic gates over one-bit registers. Return the sum and less-than."""
import json
from itertools import product
from pathlib import Path

HERE = Path(__file__).resolve().parent


def step(a, b, carry, borrow, add, multiply):
    different = add(a, b)
    sum_bit = add(different, carry)
    carry_switch = multiply(different, add(b, carry))
    new_carry = add(b, carry_switch)
    borrow_switch = multiply(different, add(b, borrow))
    new_borrow = add(borrow, borrow_switch)
    return sum_bit, new_carry, new_borrow


class Arithmetic:
    def __init__(self):
        self.adds = self.multiplies = 0

    def add(self, a, b):
        self.adds += 1
        return (a + b) % 2

    def multiply(self, a, b):
        self.multiplies += 1
        return a * b


def measure():
    gates = Arithmetic()
    for a, b, carry, borrow in product(range(2), repeat=4):
        out = step(a, b, carry, borrow, gates.add, gates.multiply)
        assert out == ((a+b+carry) % 2, (a+b+carry)//2, int(a-b-borrow < 0))
    assert gates.adds == 16*6 and gates.multiplies == 16*2
    for a, b in product(range(256), repeat=2):
        carry = borrow = acc = 0
        for bit in range(8):  # fixed wiring for each bit, unrollable at build time
            z, carry, borrow = step((a >> bit) & 1, (b >> bit) & 1, carry, borrow,
                                    gates.add, gates.multiply)
            acc |= z << bit
        assert (acc + (carry << 8), borrow) == (a+b, int(a < b))
    rounds = 16 + 8*65536
    assert (gates.adds, gates.multiplies) == (6*rounds, 2*rounds)
    return {"local_contexts":16, "ordered_8bit_pairs":65536, "mismatches":0,
            "bit_rounds_per_pair":8, "per_bit":{"add_mod_2":6, "multiply_bits":2},
            "per_pair":{"add_mod_2":48, "multiply_bits":16},
            "local_logic_depth_unlimited_parallel_gates":3,
            "boundary":"Bit lanes presented low-to-high. Fixed wire selection and output packing are not charged. No instruction fetch. One-bit truncated addition and full one-bit multiplication."}


if __name__ == "__main__":
    print(json.dumps(measure(), indent=2))
