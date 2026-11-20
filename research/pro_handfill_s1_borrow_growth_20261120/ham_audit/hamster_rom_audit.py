"""Task-level copy tests and data-dependent control probe for the 2026-11-20 VM."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np


SOURCE_SHA256 = "817d337614de5d2581a952640c689c885d04ebe0b269c37cf87a9f4560e3680e"
SEED = 20261120


def load_model(path):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError("Input is a different revision. See README for the exact source hash.")
    source = ast.parse(data, filename=str(path))
    # Load the unchanged construction functions. Leave out the machine-specific test harness.
    definitions = [
        node for node in source.body
        if getattr(node, "name", None) in {"Net", "build", "copy_prog"}
        or (isinstance(node, ast.Assign) and
            isinstance(node.targets[0], ast.Name) and node.targets[0].id == "OPS")
    ]
    namespace = {"np": np}
    exec(compile(ast.Module(definitions, type_ignores=[]), str(path), "exec"), namespace)
    return SimpleNamespace(**{key: namespace[key] for key in ("build", "copy_prog", "OPS")})


def encode(net, ops, cases):
    board = np.zeros((len(cases), net.NIN), dtype=np.float32)
    for row, (program, tape, head) in enumerate(cases):
        assert len(tape) == net.N and len(program) <= net.P
        board[row, net.c("H", head)] = 1
        start, width = net.POS["T"]
        board[row, start:start + width] = tape
        for line, (opcode, arg) in enumerate(program):
            for field, value in ((f"S{line}", ops[opcode]), (f"G{line}", arg)):
                start, width = net.POS[field]
                board[row, start:start + width] = [(value >> j) & 1 for j in range(width)]
    return board


def decode(net, row):
    def bits(name):
        start, width = net.POS[name]
        return row[start:start + width].astype(int).tolist()

    ovf = bits("OVF")[0]
    length = net.K if ovf else bits("OP").index(1)
    return {"done": bits("DONE")[0], "ovf": ovf, "output": bits("O")[:length]}


def run(net, ops, cases, trace=False):
    front, bias, back = (weights.astype(np.float32) for weights in net.net)
    board = encode(net, ops, cases)
    final = [None] * len(cases)
    paths = [[] for _ in cases] if trace else []
    for tick in range(1, 141):
        active = [i for i, result in enumerate(final) if result is None]
        if not active:
            break
        hidden = ((board[active] @ front.T + bias) >= 0).astype(np.float32)
        raw = hidden @ back.T
        assert ((raw == 0) | (raw == 1)).all()
        board[active] = raw[:, :-1]
        for j, i in enumerate(active):
            if trace:
                values = []
                for tag in ("PC", "H", "LT", "OP"):
                    start, width = net.POS[tag]
                    values.extend(board[i, start:start + width].astype(int))
                values.append(int(raw[j, -1]))
                paths[i].append(tuple(values))
            if raw[j, -1]:
                final[i] = {**decode(net, board[i]), "round": tick}
    if any(row is None for row in final):
        raise RuntimeError("A case failed to halt within 140 rounds.")
    return final, paths


def guarded_copy(start, end):
    # Head starts at 'start'. Both bound checks execute inside the VM.
    return [
        ("COMPARE", end), ("JUMP_IF_LT", 3), ("STOP", 0),
        ("READ_BIT", 0), ("EMIT", 0), ("COMPARE", max(0, end - 1)),
        ("JUMP_IF_LT", 8), ("STOP", 0), ("MOVE_RIGHT", 0), ("JUMP_IF_LT", 3),
    ]


def category(start, end, net):
    if end == start:
        return "empty"
    if end - start > net.K:
        return "too_long"
    if end == net.N:
        return "fits_right_boundary"
    return "fits_internal"


def grade(net, ops, compiler, inputs):
    cases = [(compiler(start, end), tape, start) for tape, start, end in inputs]
    outputs, _ = run(net, ops, cases)
    buckets = {}
    for (tape, start, end), got in zip(inputs, outputs):
        expected = tape[start:end]
        fits = len(expected) <= net.K
        matches = (got["done"] == int(fits) and got["ovf"] == int(not fits)
                   and got["output"] == expected[:net.K])
        counts = buckets.setdefault(category(start, end, net), {"passed": 0, "total": 0})
        counts["total"] += 1
        counts["passed"] += int(matches)
    return {"passed": sum(group["passed"] for group in buckets.values()),
            "total": len(cases), "categories": buckets}


def original_samples():
    rng = np.random.default_rng(SEED)
    samples = []
    for _ in range(300):
        tape = rng.integers(0, 2, 16).tolist()
        start = int(rng.integers(0, 16))
        end = int(rng.integers(start, 17))
        samples.append((tape, start, end))
    return samples


def control_test(source):
    net = source.build(4, 8, 4)
    program = [("READ_BIT", 0), ("WRITE_1", 0), ("EMIT", 0), ("MOVE_RIGHT", 0),
               ("COMPARE", 3), ("JUMP_IF_LT", 0), ("STOP", 0)]
    tapes = [[(i >> bit) & 1 for bit in range(4)] for i in range(16)]
    outputs, paths = run(net, source.OPS, [(program, t, 0) for t in tapes], trace=True)
    return {"program": program, "head": 0, "tapes": len(tapes), "network": [4, 8, 4],
            "trace_fields": ["PC", "H", "LT", "OP", "stop"], "unique_paths": len(set(map(tuple, paths))),
            "rounds": sorted({row["round"] for row in outputs}),
            "match_original_first_three_bits": sum(row["output"] == t[:3] for row, t in zip(outputs, tapes))}


def audit(source):
    net = source.build(16, 16, 8)
    alternating = [[(i + phase) % 2 for i in range(16)] for phase in (0, 1)]
    grid = [(t, s, e) for t in alternating for s in range(16) for e in range(s, 17)]
    samples = original_samples()
    report = {"source_sha256": SOURCE_SHA256, "seed": SEED, "copy_network": [16, 16, 8]}
    for name, inputs in [("published_300_inputs", samples), ("two_tape_interval_grid", grid)]:
        report[name] = {tag: grade(net, source.OPS, compiler, inputs)
                        for tag, compiler in [("published", source.copy_prog), ("guarded", guarded_copy)]}
    examples = [(14, 15), (14, 14), (15, 16)]
    cases = [(source.copy_prog(s, e), alternating[0], s) for s, e in examples]
    outputs, _ = run(net, source.OPS, cases)
    report["published_examples"] = [{"tape_from_index_zero": "0101010101010101", "interval": [s, e],
                                     "expected_output": alternating[0][s:e], **row}
                                    for (s, e), row in zip(examples, outputs)]
    report["control_test"] = control_test(source)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="November 20 hamster_vm.py")
    parser.add_argument("--output", type=Path, help="where to write the JSON result (default: stdout)")
    args = parser.parse_args()
    result = json.dumps(audit(load_model(args.source)), indent=2) + "\n"
    if args.output is None:
        print(result, end="")
    else:
        args.output.write_text(result, encoding="utf-8")


if __name__ == "__main__":
    main()
