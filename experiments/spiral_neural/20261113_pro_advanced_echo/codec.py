"""AE1: bounded advanced Echo fixtures, not a neural learner or legacy parser."""

from dataclasses import dataclass
from typing import Iterable


PROFILE = "SLE-AE1-n5-v1"
HEADER = "01"
OP = "010"
END = "111100"
UP = "111110"
EXTERNAL_STOP = "S"


class CodecError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class Question:
    payload: tuple[int, ...]
    r: int


def _profile(profile: str) -> None:
    if profile != PROFILE:
        raise CodecError("PROFILE", "AE1 requires its explicitly selected profile")


def _checked_payload(payload: Iterable[int], r: int) -> tuple[int, ...]:
    try:
        values = tuple(payload)
    except TypeError as exc:
        raise CodecError("PAYLOAD", "payload must be an iterable of integer IDs") from exc
    if not 1 <= len(values) <= 4:
        raise CodecError("N_RANGE", "AE1 requires 1..4 payload words")
    if any(type(value) is not int or not 0 <= value <= 29 for value in values):
        raise CodecError("VALUE_RANGE", "ordinary payload IDs are integers 0..29")
    if type(r) is not int or not 1 <= r <= len(values):
        raise CodecError("R_RANGE", "r must be an integer in 1..N")
    return values


def _word(value: int, n: int) -> str:
    return f"{value:0{n}b}0"


def encode(payload: Iterable[int], r: int, *, profile: str) -> str:
    """Encode one complete Q; r is the number to return, not the payload length."""
    _profile(profile)
    values = _checked_payload(payload, r)
    return HEADER + OP + _word(r, 3) + "".join(_word(v, 5) for v in values) + END


def decode(bits: str, *, profile: str) -> Question:
    """Parse only aligned words in the selected AE1 profile; payload stays opaque."""
    _profile(profile)
    if not isinstance(bits, str) or not bits or any(bit not in "01" for bit in bits):
        raise CodecError("BINARY", "Q must be a nonempty 0/1 string")
    if bits[:2] != HEADER:
        raise CodecError("HEADER", "opening marker must be 01")
    if bits[2:5] != OP:
        raise CodecError("OP", "AE1 operator must be 010")
    if len(bits) < 9:
        raise CodecError("COUNT_TRUNCATED", "r needs a complete four-bit word")
    if bits[8] != "0":
        raise CodecError("COUNT_SUFFIX", "r word must end in 0")
    r = int(bits[5:8], 2)
    if not 1 <= r <= 4:
        raise CodecError("R_RANGE", "r must be in 1..4 and no greater than N")
    if (len(bits) - 9) % 6:
        raise CodecError("WORD_LENGTH", "payload and END use complete six-bit words")

    values: list[int] = []
    for offset in range(9, len(bits), 6):
        word = bits[offset:offset + 6]
        if word[-1] != "0":
            raise CodecError("WORD_SUFFIX", "each payload/control word must end in 0")
        value = int(word[:5], 2)
        if value == 30:
            if offset + 6 != len(bits):
                raise CodecError("TRAILING", "no bits may follow END")
            checked = _checked_payload(values, r)
            return Question(checked, r)
        if value == 31:
            raise CodecError("UP_IN_PAYLOAD", "UP is reserved, not an ordinary symbol")
        values.append(value)
        if len(values) > 4:
            raise CodecError("N_RANGE", "AE1 permits at most four payload words")
    raise CodecError("MISSING_END", "Q requires an aligned END word")


def answer(bits: str, *, profile: str) -> str:
    """Return only the first r opaque words; external STOP is not part of this string."""
    question = decode(bits, profile=profile)
    return "".join(_word(value, 5) for value in question.payload[:question.r])


def fixtures(*, profile: str) -> list[dict]:
    """The same four-word body at each r; these are fixtures, not a training split."""
    _profile(profile)
    values = (1, 6, 11, 17)
    rows = []
    for r in range(1, 5):
        q = encode(values, r, profile=profile)
        a = answer(q, profile=profile)
        rows.append({
            "id": f"four_words_r{r}", "profile": profile,
            "payload_ids": list(values), "N": len(values), "r": r,
            "stage": "full_echo" if r == len(values) else "prefix_echo",
            "Q": q, "A": a, "external_stop": EXTERNAL_STOP,
            "Q_bits": len(q), "A_bits": len(a),
            "generation_actions_with_stop": len(a) + 1,
        })
    return rows
