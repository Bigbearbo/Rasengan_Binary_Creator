"""Replay interface-only probes on a local copy of the handfilled arithmetic project."""
import argparse
import ast
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import numpy as np


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_fast_runner(path):
    # Use the project's unmodified fast_run definition, which depends only on NumPy.
    tree = ast.parse(path.read_text(encoding='utf-8'))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'fast_run')
    module = ModuleType('frac_ctrl')
    module.np = np
    exec(compile(ast.Module([function], []), str(path), 'exec'), module.__dict__)
    return module


def normalize_error(call):
    try:
        return {'value': call()}
    except (AssertionError, IndexError, ValueError, TypeError) as error:
        return {'error': type(error).__name__, 'message': str(error)}


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, default=here / 'private', help='Directory containing dispatch.py, adapters.py, and both code tables')
    parser.add_argument('--runner', type=Path, help='Location of the project’s frac_ctrl.py, default under --source-dir')
    parser.add_argument('--mult-ctrl-dir', type=Path, help='Optional directory of the project’s mult_ctrl.py and dependencies, to run the original host')
    args = parser.parse_args()
    source = args.source_dir.resolve()
    fast = load_fast_runner((args.runner or source / 'frac_ctrl.py').resolve())
    sys.modules['frac_ctrl'] = fast
    if args.mult_ctrl_dir:
        sys.path.insert(0, str(args.mult_ctrl_dir.resolve()))
        import mult_ctrl as host
    else:
        host = ModuleType('mult_ctrl')
        host.run = lambda net, batch, limit: fast.fast_run(net, batch, limit, np.float32)
        sys.modules['mult_ctrl'] = host
    dispatch = load_module('dispatch', source / 'dispatch.py')
    adapters = load_module('adapters', source / 'adapters.py')
    big = adapters.Big()
    big.M = SimpleNamespace(k=4)  # The only network field read by Big.parse.
    mixed = adapters.Mixed()
    mixed.N = SimpleNamespace(NS=7)  # The source setting for the maximum prefix-expression slots.
    parsers = {big.name: big.parse, mixed.name: mixed.parse}
    good = ['加', 1, 2, '句號']
    invalid = ['加', 1, 2, '未登記控制詞', '句號']
    cases = {
        'old_single': mixed.words(('乘', 200, 1)),
        'new_single': ['乘', '黏數', 3, 8, '句號', 1, '句號'],
        'old_nested': mixed.words(('加', '乘', 200, 1, 0)),
        'new_nested': ['加', '乘', '黏數', 3, 8, '句號', 1, 0, '句號'],
        'truncated_number': ['加', 1, '黏數', '句號'],
    }
    report = {'runner': 'mult_ctrl.run' if args.mult_ctrl_dir else 'project frac_ctrl.fast_run, float32', 'tables': {}}
    for name in ('碼表_現行自訂.json', '碼表_五位草案.json'):
        network = dispatch.build(str(source / name), L=48)
        tested = {}
        for label, words in cases.items():
            routes, _, rounds = dispatch.dispatch(network, [words])
            route = routes[0]
            try:
                parsed = normalize_error(lambda: parsers[route[0]](words))
            except adapters.BadWords as error:
                parsed = {'error': 'BadWords', 'message': str(error)}
            tested[label] = {'words': words, 'route': route, 'rounds': int(rounds[0]), 'parse': parsed}
        malformed = [[head, 1, '未登記控制詞', '句號'] for head in network.heads]
        board, valid = dispatch.encode_words(network, malformed)
        out, rounds, _ = host.run(network.net, board, 4)
        start = network.c('R')
        count = out[:, start:start + len(network.RL)].sum(axis=1)
        report['tables'][name] = {
            'heads': len(network.heads), 'routes': len(network.RL), 'units': len(network.rows), 'board_bits': network.NIN,
            'good_single': normalize_error(lambda: dispatch.dispatch(network, [good])[0]),
            'bad_single': normalize_error(lambda: dispatch.dispatch(network, [invalid])[0]),
            'good_and_bad_together': normalize_error(lambda: dispatch.dispatch(network, [good, invalid])[0]),
            'unknown_tail': {'cases': len(malformed), 'encoder_marked_invalid': int((~valid).sum()), 'one_route_lit': int((count == 1).sum()), 'ended_in_two_rounds': int((rounds == 2).sum())},
            'grammar_cases': tested,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
