#!/usr/bin/env python3
"""Spiral dialogue sandbox v0.1: two scripted agents, persistent syntax trees.

NOT a neural-network learning experiment. It extends the existing tokenizer
without modifying spiral_parser.py. Word widths, roles, and message kinds are
pre-agreed bootstrap configuration, *not* autonomously discovered.

Frames (no punctuation / whitespace on wire):
  kind n=2,k=1: 0=QUERY, 1=EXAMPLE, 2=REPLY, 3=ERROR
  category n=1,k=1: 0=MATH
  operator, arg1, arg2 n=3,k=1 each
  result n=4,k=1: only EXAMPLE/REPLY
  ERROR: code n=3,k=1; field n=3,k=1; offset n=5,k=1
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from spiral_parser import tokenize

KINDS = {0: "query", 1: "example", 2: "reply", 3: "error"}
ERRORS = {0: "NEED_EXAMPLE", 1: "BAD_SUFFIX", 2: "TRUNCATED", 3: "NON_BINARY",
          4: "EXTRA_BITS", 5: "UNKNOWN_CATEGORY", 6: "INVALID_FRAME",
          7: "CONFLICTING_EXAMPLE"}
ERROR_CODES = {v: k for k, v in ERRORS.items()}
FIELDS = {0: "kind", 1: "category", 2: "operator", 3: "arg1",
          4: "arg2", 5: "result", 6: "extra"}


def word(value: int, n: int, k: int = 1) -> str:
    if not isinstance(value, int) or not 0 <= value < (1 << n):
        raise ValueError(f"value={value} exceeds {n}-bit information field")
    return f"{value:0{n}b}" + "0" * k


def encode(kind: str, op: int = 0, a: int = 0, b: int = 0,
           result: int | None = None) -> str:
    kind_value = next((code for code, name in KINDS.items() if name == kind), None)
    if kind_value is None or kind == "error":
        raise ValueError("use encode_error() for error frames")
    if (kind == "query") != (result is None):
        raise ValueError("query has no result; example/reply must have result")
    frame = word(kind_value, 2) + word(0, 1) + word(op, 3) + word(a, 3) + word(b, 3)
    if result is not None:
        frame += word(result, 4)
    return frame


def encode_error(code: str, field: int, offset: int) -> str:
    if code not in ERROR_CODES or not 0 <= field < 8 or offset < 0:
        raise ValueError("invalid error code, field or offset")
    # Offset 31 is a saturated out-of-range marker for very long messages.
    return word(3, 2) + word(ERROR_CODES[code], 3) + word(field, 3) + word(min(offset, 31), 5)


class ParseFailure(Exception):
    def __init__(self, code: str, field: int, offset: int, message: str):
        super().__init__(message)
        self.code, self.field, self.offset = code, field, offset
        self.message = message

    def as_dict(self) -> dict[str, Any]:
        return {"error": self.code, "field": FIELDS.get(self.field, "unknown"),
                "field_index": self.field, "offset": self.offset,
                "detail": self.message, "retryable": True}


def empty_state() -> dict[str, Any]:
    return {"schema": "spiral_dialogue_v1", "tree": {"math": {"operators": {}}}}


class DialogueParser:
    """Syntax-only parser with transactional persistent tree/evidence updates."""

    def __init__(self, state_path: str | Path):
        self.path = Path(state_path)
        self.state = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else empty_state()
        if self.state.get("schema") != "spiral_dialogue_v1":
            raise ValueError("state schema does not match this dialogue version")

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(self.path.name + ".tmp")
        temp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, self.path)

    def _read(self, bits: str, offset: int, n: int, index: int) -> tuple[dict[str, Any], int]:
        if offset + n + 1 > len(bits):
            raise ParseFailure("TRUNCATED", index, offset,
                               f"{FIELDS.get(index, 'error part')} needs {n + 1} bits; got {len(bits) - offset}")
        try:
            token = tokenize(bits, n, 1, offset)
        except ValueError as exc:
            raise ParseFailure("BAD_SUFFIX", index, offset,
                               f"{FIELDS.get(index, 'error part')} expects {n} information bits followed by 0; "
                               f"got {bits[offset:offset+n+1]!r}") from exc
        return token, token["end"]

    def parse(self, bits: str) -> dict[str, Any]:
        # Validate whole message before touching state. Errors are not learnt as words.
        if not bits:
            raise ParseFailure("TRUNCATED", 0, 0, "empty frame")
        for i, char in enumerate(bits):
            if char not in "01":
                raise ParseFailure("NON_BINARY", 6, i, f"invalid character {char!r} at offset {i}")
        position = 0
        kindtok, position = self._read(bits, position, 2, 0)
        kind = KINDS[kindtok["value"]]
        if kind == "error":
            code, position = self._read(bits, position, 3, 6)
            field, position = self._read(bits, position, 3, 6)
            loc, position = self._read(bits, position, 5, 6)
            if position != len(bits):
                raise ParseFailure("EXTRA_BITS", 6, position, f"{len(bits)-position} extra bits in error frame")
            if code["value"] not in ERRORS:
                raise ParseFailure("INVALID_FRAME", 6, 3, "unknown error code")
            return {"kind": kind, "code": ERRORS[code["value"]],
                    "field_index": field["value"], "field": FIELDS.get(field["value"], "unknown"),
                    "offset": loc["value"]}

        cat, position = self._read(bits, position, 1, 1)
        if cat["value"] != 0:
            raise ParseFailure("UNKNOWN_CATEGORY", 1, cat["offset"],
                               f"category={cat['value']} is not available in dialogue v1")
        op, position = self._read(bits, position, 3, 2)
        a, position = self._read(bits, position, 3, 3)
        b, position = self._read(bits, position, 3, 4)
        result = None
        if kind != "query":
            answer, position = self._read(bits, position, 4, 5)
            result = answer["value"]
        if position != len(bits):
            raise ParseFailure("EXTRA_BITS", 6, position,
                               f"{len(bits)-position} bits remain after {kind} frame")

        key = op["word"]
        current = self.state["tree"]["math"]["operators"].get(key)
        # Inconsistent repeated examples must not poison an existing node.
        if kind == "example" and current is not None:
            for existing in current["examples"]:
                if existing["a"] == a["value"] and existing["b"] == b["value"]:
                    if existing["result"] != result:
                        raise ParseFailure("CONFLICTING_EXAMPLE", 5, 17,
                                           f"{key}: ({a['value']},{b['value']}) already taught "
                                           f"as {existing['result']}, received {result}")

        new = current is None
        if new:
            current = {"value": op["value"], "status": "unknown", "meaning": None,
                       "seen": 0, "examples": [], "hypotheses": []}
            self.state["tree"]["math"]["operators"][key] = current
        current["seen"] += 1
        if kind == "example" and not any(
                x["a"] == a["value"] and x["b"] == b["value"] for x in current["examples"]):
            current["examples"].append({"a": a["value"], "b": b["value"], "result": result})
        self._save()
        return {"kind": kind, "category": "math", "operator": op["value"],
                "operator_word": key, "a": a["value"], "b": b["value"],
                "result": result, "new_node": new,
                "hint": ("new operator; meaning unknown" if new else
                         "operator seen before") + f"; path=math/operator/{op['value']}",
                "examples_known": len(current["examples"])}

    def annotate(self, operator_word: str, hypotheses: list[str]) -> None:
        """Student's inference annotation, not parser-confirmed truth."""
        node = self.state["tree"]["math"]["operators"][operator_word]
        node["hypotheses"] = list(hypotheses)
        node["status"] = "hypothesis" if len(hypotheses) == 1 else "unknown"
        node["meaning"] = hypotheses[0] if len(hypotheses) == 1 else None
        self._save()


# Simulated student can select among a PREWIRED finite hypothesis space.
# This is NOT autonomous language induction by a neural net.
OPERATIONS = {
    "add": lambda a, b: a + b,
    "xor": lambda a, b: a ^ b,
    "and": lambda a, b: a & b,
    "or": lambda a, b: a | b,
    "left": lambda a, b: a,
    "right": lambda a, b: b,
    "max": max,
    "min": min,
}


class ScriptedStudent:
    def __init__(self, path: Path):
        self.parser = DialogueParser(path)

    def hypotheses(self, operator_word: str) -> list[str]:
        examples = self.parser.state["tree"]["math"]["operators"][operator_word]["examples"]
        return [name for name, fn in OPERATIONS.items()
                if all(fn(x["a"], x["b"]) == x["result"] for x in examples)]

    def receive(self, bits: str) -> dict[str, Any]:
        try:
            received = self.parser.parse(bits)
        except ParseFailure as exc:
            return {"status": "syntax_error", "diagnostic": exc.as_dict(),
                    "send_bits": encode_error(exc.code, exc.field, exc.offset)}
        if received["kind"] == "example":
            hypotheses = self.hypotheses(received["operator_word"])
            self.parser.annotate(received["operator_word"], hypotheses)
            return {"status": "learned_example", "parsed": received,
                    "hypotheses": hypotheses}
        if received["kind"] == "query":
            hypotheses = self.hypotheses(received["operator_word"])
            if len(hypotheses) != 1:
                return {"status": "insufficient_evidence", "parsed": received,
                        "hypotheses": hypotheses,
                        "send_bits": encode_error("NEED_EXAMPLE", 2, 5)}
            value = OPERATIONS[hypotheses[0]](received["a"], received["b"])
            if value >= 16:
                return {"status": "out_of_range", "parsed": received}
            reply = encode("reply", received["operator"], received["a"], received["b"], value)
            return {"status": "replied", "parsed": received,
                    "selected_hypothesis": hypotheses[0], "send_bits": reply}
        return {"status": "received", "parsed": received}


class ScriptedTeacher:
    def __init__(self, path: Path):
        self.parser = DialogueParser(path)
        self.true_operations = {5: OPERATIONS["add"], 6: OPERATIONS["xor"]}

    def example(self, op: int, a: int, b: int) -> str:
        return encode("example", op, a, b, self.true_operations[op](a, b))

    def query(self, op: int, a: int, b: int) -> str:
        return encode("query", op, a, b)

    def receive(self, bits: str, expected: int | None = None) -> dict[str, Any]:
        try:
            parsed = self.parser.parse(bits)
        except ParseFailure as exc:
            return {"status": "error", "diagnostic": exc.as_dict()}
        if parsed["kind"] == "error":
            return {"status": "repair_requested", "report": parsed}
        if expected is None or parsed["kind"] != "reply":
            return {"status": "received", "parsed": parsed}
        return {"status": "graded", "correct": parsed["result"] == expected,
                "received": parsed["result"], "expected": expected, "parsed": parsed}


def run_scenario(directory: Path) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    teacher = ScriptedTeacher(directory / "teacher_tree.json")
    student = ScriptedStudent(directory / "student_tree.json")
    events: list[dict[str, Any]] = []

    def send(step: str, bits: str, expected: int | None = None) -> dict[str, Any]:
        student_result = student.receive(bits)
        event: dict[str, Any] = {"step": step, "teacher_to_student": bits, "student": student_result}
        if "send_bits" in student_result:
            reply = student_result["send_bits"]
            event["student_to_teacher"] = reply
            event["teacher"] = teacher.receive(reply, expected)
        events.append(event)
        return event

    first = send("teach_add_1", teacher.example(5, 1, 2))
    request = send("query_before_enough_examples", teacher.query(5, 3, 2))
    assert request["student"]["status"] == "insufficient_evidence"
    assert request["teacher"]["report"]["code"] == "NEED_EXAMPLE"
    # Two words have same value in multiple hypothesis operations: add/xor/or.
    second_bits = teacher.example(5, 2, 3)
    # Corrupt operator tail '0' at fixed offset 5 + 3 = 8, making it '1'.
    corrupt = second_bits[:8] + "1" + second_bits[9:]
    failure = send("corrupt_operator_tail", corrupt)
    assert failure["student"]["status"] == "syntax_error"
    assert failure["teacher"]["status"] == "repair_requested"
    assert failure["teacher"]["report"]["field"] == "operator"
    send("repair_and_reteach_add", second_bits)
    add_test = send("ask_add_unseen", teacher.query(5, 3, 2), 5)

    send("teach_xor", teacher.example(6, 5, 3))
    xor_test = send("ask_xor_unseen", teacher.query(6, 5, 6), 3)
    # Semantic error: same arguments but different answer: reject, don't corrupt.
    bad_semantic = send("contradictory_example", encode("example", 5, 1, 2, 7))
    assert bad_semantic["student"]["status"] == "syntax_error"
    assert bad_semantic["teacher"]["report"]["code"] == "CONFLICTING_EXAMPLE"
    send("repair_example", teacher.example(5, 1, 2))
    old_test = send("retest_old_add", teacher.query(5, 4, 2), 6)

    summary = {
        "kind": "scripted simulation; not a trained neural network",
        "steps": len(events),
        "syntax_error_repaired": failure["teacher"]["report"]["code"] == "BAD_SUFFIX",
        "student_requested_more_examples": request["teacher"]["report"]["code"] == "NEED_EXAMPLE",
        "semantic_error_rejected": bad_semantic["teacher"]["report"]["code"] == "CONFLICTING_EXAMPLE",
        "query_correct": [add_test["teacher"]["correct"], xor_test["teacher"]["correct"],
                          old_test["teacher"]["correct"]],
        "operator_count": len(student.parser.state["tree"]["math"]["operators"]),
        "student_tree_path": str(directory / "student_tree.json"),
    }
    (directory / "trace.json").write_text(json.dumps({"summary": summary, "events": events},
                                                     ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    cli = argparse.ArgumentParser(description="Reproducible teacher/student Spiral dialogue sandbox")
    cli.add_argument("--out", default="spiral_demo_run", help="output folder (must be empty/new for a fresh run)")
    args = cli.parse_args()
    out = Path(args.out)
    if any(out.glob("*.json")):
        cli.error("output already contains JSON; specify a fresh directory for deterministic replay")
    print(json.dumps(run_scenario(out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()