"""Run from any directory: python run_borrow.py [--out FILE]. Requires NumPy and SciPy."""

import argparse
import ast
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import scipy
from scipy.sparse import csr_matrix


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'serial_adder.py'
CARRY = ROOT / 'RESEARCH026-READOUT-RESULT.json'
TWO = ROOT / 'RESEARCH026-EXACT-TWO-RESULT.json'
PLAN = ROOT / 'borrow_prereg.md'
BITS = 8
PAIRS = 256 * 256
FIXED = (-1, 1, 1, -1)  # A0, B0, borrow_in, bias


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_s1():
    """Compile verbatim original S1 definitions, omitting Windows imports and unused drivers."""
    tree = ast.parse(SOURCE.read_bytes(), filename=str(SOURCE))
    required = {'Net', 'full_add_bit', 'build_S1', 'board_of', 'val'}
    definitions = [node for node in tree.body if getattr(node, 'name', None) in required]
    constants = [node for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'M' for t in node.targets)]
    assert len(constants) == 1 and {node.name for node in definitions} == required
    tree.body = constants + definitions
    env = {'np': np}
    exec(compile(tree, str(SOURCE), 'exec'), env)
    return env['build_S1']()


def old_port(path, width):
    record = json.loads(path.read_text())
    delta = record['changes']['rounded_delta']
    assert record['status'] == 'accepted_execution_integer_readout_all_correct'
    assert delta[:4] == [0] * 4 and len(delta) == 4 + width
    return np.array(delta[4:], dtype=np.int16), record['result_commit']


class Network:
    def __init__(self, incoming, bias, outgoing):
        # This bound covers any binary board or hidden vector. Int16 multiply/add is exact here.
        assert np.max(np.abs(incoming).sum(axis=1) + np.abs(bias)) < 32767
        assert np.max(np.abs(outgoing).sum(axis=1)) < 32767
        self.incoming = csr_matrix(incoming, dtype=np.int16)
        self.bias = bias.astype(np.int16)
        self.outgoing = csr_matrix(outgoing, dtype=np.int16)

    def step(self, board):
        scores = (self.incoming @ board.T).T + self.bias
        hidden = (scores >= 0).astype(np.int16)
        output = (self.outgoing @ hidden.T).T
        return hidden, output


def extend(net, dimensions, ports, params):
    """Append an actual hidden row and board coordinate; keep stop at the last core output."""
    w1, b1, w2 = net
    width, cells = w1.shape
    a0, b0 = dimensions
    next_w1 = np.zeros((width + 1, cells + 1), dtype=np.int64)
    next_w1[:width, :cells] = w1
    next_w1[-1, [a0, b0, cells]] = params[:3]
    next_b1 = np.append(b1, params[3])
    # Board[old], borrow, stop, learned carry port, learned exactly-two port.
    next_w2 = np.zeros((cells + 4, width + 1), dtype=np.int64)
    next_w2[:cells, :width] = w2[:cells]
    next_w2[cells, -1] = 1
    next_w2[cells + 1, :width] = w2[cells]
    next_w2[cells + 2:, :width] = ports
    return Network(next_w1, next_b1, next_w2)


def train(seed, triples):
    rng = np.random.default_rng(seed)
    weights = np.zeros(4, dtype=np.int64)
    rounds, updates = 0, 0
    # The final coordinate 1 is the bias. The eight targets are local supervision only.
    cases = np.column_stack([triples, np.ones(len(triples), dtype=np.int64)])
    targets = triples[:, 0] < triples[:, 1] + triples[:, 2]
    for rounds in range(1, 129):
        for index in rng.permutation(len(cases)):
            pred = int(cases[index] @ weights >= 0)
            error = int(targets[index]) - pred
            if error:
                weights += error * cases[index]
                updates += 1
        if np.array_equal(cases @ weights >= 0, targets):
            break
    return {'seed': seed, 'params': weights.tolist(), 'epochs': rounds, 'updates': updates,
            'local_correct_of_8': int(np.sum((cases @ weights >= 0) == targets))}


def old_reference(arrays, board):
    model = Network(*arrays)
    result = []
    for _ in range(BITS):
        hidden, output = model.step(board)
        result.append((hidden, output))
        board = output[:, :-1]
    return result


def first_limit(first_hidden, a, b):
    # Binary encoding maps all 19-bit vectors to distinct integers, without hashing collisions.
    keys = first_hidden.astype(np.int32) @ (1 << np.arange(first_hidden.shape[1], dtype=np.int32))
    gold = (a & 1) < (b & 1)
    size = 1 << first_hidden.shape[1]
    zero = np.bincount(keys[~gold], minlength=size)
    one = np.bincount(keys[gold], minlength=size)
    count = int(np.maximum(zero, one).sum())
    return {'pairs': len(a), 'different_hidden_vectors': int(np.count_nonzero(zero + one)),
            'vectors_with_conflicting_labels': int(np.sum((zero > 0) & (one > 0))),
            'pairs_in_conflicting_vectors': int((zero + one)[(zero > 0) & (one > 0)].sum()),
            'best_possible_correct_given_only_19_activations': count,
            'always_predict_no_borrow_correct': int((~gold).sum()),
            'witness': [{'a': x, 'b': y, 'feature_code': int(keys[256*x + y]),
                         'label': int(gold[256*x+y])} for x, y in [(0, 1), (1, 0)]]}


def evaluate(model, board, decoder, core, a, b, carry_col, reference):
    cells = board.shape[1]
    board = np.column_stack([board, np.zeros(len(board), dtype=np.int16)])
    names = ['borrow', 'old_hidden', 'old_board', 'old_stop_versus_baseline',
             'original_carry', 'learned_carry_readout', 'learned_exactly_two', 'stop_schedule']
    matches = {key: np.ones(len(board), dtype=bool) for key in names}
    by_round = {key: [] for key in names}
    for i, (base_hidden, base_output) in enumerate(reference):
        h, out = model.step(board)
        mask = (1 << (i+1)) - 1
        low_a, low_b = a & mask, b & mask
        lower_mask = (1 << i) - 1
        add_cin = ((a & lower_mask) + (b & lower_mask)) >> i
        total = ((a >> i) & 1) + ((b >> i) & 1) + add_cin
        carry_gold = (low_a + low_b) >> (i+1)
        tests = {'borrow': out[:, cells] == (low_a < low_b),
                 'old_hidden': np.all(h[:, :-1] == base_hidden, axis=1),
                 'old_board': np.all(out[:, :cells] == base_output[:, :cells], axis=1),
                 'old_stop_versus_baseline': out[:, cells+1] == base_output[:, -1],
                 'original_carry': out[:, carry_col] == carry_gold,
                 'learned_carry_readout': out[:, cells+2] == carry_gold,
                 'learned_exactly_two': out[:, cells+3] == (total == 2),
                 'stop_schedule': out[:, cells+1] == int(i == BITS - 1)}
        for name, correct in tests.items():
            matches[name] &= correct
            by_round[name].append(int(correct.sum()))
        board = out[:, :cells+1]
    sum_correct = decoder(board[:, :core.nin]) == a+b
    return {'pairs': len(a), 'per_round_correct': by_round,
            'all_8_rounds_correct': {name: int(ok.sum()) for name, ok in matches.items()},
            'final_sum_correct': int(sum_correct.sum()), 'final_borrow_correct': by_round['borrow'][-1]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'borrow_result.json')
    args = parser.parse_args()
    core, encode, decode = load_s1()
    matrices = core.mats()
    width, cells = matrices[0].shape
    assert (width, cells) == (19, 18)
    carry, carry_commit = old_port(CARRY, width)
    two, two_commit = old_port(TWO, width)
    numbers = np.arange(256, dtype=np.int32)
    a, b = np.repeat(numbers, 256), np.tile(numbers, 256)
    first_board = encode(a, b).astype(np.int16)
    baseline = old_reference(matrices, first_board)
    collision = first_limit(baseline[0][0], a, b)
    triples = np.array(list(itertools.product([0, 1], repeat=3)), dtype=np.int64)
    training = [train(seed, triples) for seed in range(20261120, 20261136)]
    control = (FIXED[0], FIXED[1], 0, FIXED[3])
    configs = [FIXED, control, *(tuple(row['params']) for row in training)]
    results = {}
    for params in dict.fromkeys(configs):
        key = ','.join(map(str, params))
        model = extend(matrices, (core.c('A'), core.c('B')), np.stack([carry, two]), params)
        results[key] = evaluate(model, first_board, decode, core, a, b, core.c('C'), baseline)
    result = {'protocol': 'S1 side-branch borrow, 8-bit ordered pairs, 8 self-fed rounds',
              'versions': {'numpy': np.__version__, 'scipy': scipy.__version__},
              'sha256': {p.name: sha(p) for p in [SOURCE, CARRY, TWO, PLAN, Path(__file__)]},
              'original': {'units': width, 'board_width': cells,
                           'carry_checkpoint': carry_commit, 'carry_vector': carry.tolist(),
                           'exact_two_checkpoint': two_commit, 'exact_two_vector': two.tolist()},
              'new': {'units': width+1, 'board_width': cells+1,
                      'parameter_order': ['A0', 'B0', 'own_last_borrow', 'bias'],
                      'extra_nonzero_edges_handfilled_excluding_bias': 4,
                      'handfilled': list(FIXED), 'handfilled_no_readback': list(control),
                      'extra_old_to_new_input_edges': ['A0', 'B0'],
                      'new_to_old_edges': 0},
              'first_step_old_hidden_bound': collision,
              'training': training, 'exhaustive_by_parameter_tuple': results}
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'file': str(args.out), 'trained': len(training), 'different_nets': len(results),
                      'frozen_ceiling': collision['best_possible_correct_given_only_19_activations'],
                      'borrow_all8': {k: v['all_8_rounds_correct']['borrow'] for k, v in results.items()},
                      'updates': [record['updates'] for record in training]}))


if __name__ == '__main__':
    main()
