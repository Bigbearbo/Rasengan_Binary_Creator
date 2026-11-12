"""Frozen P032 input-bit interventions; prefixes are explicitly conditional."""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import p032_reference as old

ref = old.ref


def first_error(generated, target):
    return next((i for i in range(max(len(generated), len(target)))
                 if generated[i:i + 1] != target[i:i + 1]), None)


def probabilities(net, text):
    z = net.forward(text)[2].astype(np.float64)
    return z, np.exp(z - np.logaddexp.reduce(z))


def run(archive, out):
    out.mkdir()
    probes, errors, margins = [], [], []
    source_hashes, pre_cache = {}, {}
    groups = defaultdict(list)
    for path in sorted((archive / 'training').glob('*/neg*/final-state.npz')):
        root = path.parent.parent
        split_name, seed_word, hidden_word = root.name.split('-')
        seed, hidden = int(seed_word[4:]), int(hidden_word[1:])
        ratio = int(path.parent.name[3:])
        split = old.SPLITS[split_name]
        if root.name not in pre_cache:
            warm_path = root / 'warm-3/final-state.npz'
            before = old.restore(warm_path, seed)
            source_hashes[warm_path.relative_to(archive).as_posix()] = old.sha(warm_path)
            pre_cache[root.name] = before
            models = [('before', before, ref.PHASES[3])]
        else:
            before = pre_cache[root.name]
            models = []
        after = old.restore(path, seed)
        source_hashes[path.relative_to(archive).as_posix()] = old.sha(path)
        models.append(('after', after, ref.PHASES[4]))
        original_rows = json.loads((path.parent / 'final-truth-table.json').read_text('utf-8'))
        original_index = {(r['operator'], r['value']): r for r in original_rows}
        for phase, net, p in models:
            frozen = net.state()
            for op in p.ops:
                for value in range(8):
                    q, answer = ref.encode(p, op, value), ref.answer(op, p.nd, value)
                    subset = 'train' if value in split['train'] else 'val' if value in split['val'] else 'test'
                    record = old.truth_row(net, p, op, value)
                    if phase == 'after':
                        prior = original_index[(ref.NAMES[op], value)]
                        assert record['generated'] == prior['generated']
                        assert record['teacher_forcing'] == prior['teacher_forcing']
                    target, generated = answer + 'S', record['generated']
                    tf = [r['prediction'] for r in record['teacher_forcing']]
                    first = first_error(generated, target)
                    if first is not None:
                        assert first < len(target)
                        assert all(tf[i] == target[i] for i in range(first))
                        assert tf[first] != target[first]
                    free_wrong = [generated[i:i + 1] != token for i, token in enumerate(target)]
                    tf_wrong = [tf[i] != token for i, token in enumerate(target)]
                    rescued = [first is not None and i > first and free_wrong[i] and not tf_wrong[i]
                               for i in range(len(target))]
                    errors.append({'phase': phase, 'split': split_name, 'seed': seed, 'H': hidden,
                                   'new_percent': ratio if phase == 'after' else None, 'operator': ref.NAMES[op],
                                   'subset': subset, 'value': value, 'Q': q, 'target': target,
                                   'generated': generated, 'first_wrong_position': first,
                                   'teacher_forced_predictions': ''.join(tf), 'free_wrong': free_wrong,
                                   'teacher_wrong': tf_wrong, 'prefix_rescued_later_positions': rescued,
                                   'STOP_correct': record['STOP_position_correct']})
                    for input_bit in range(3):
                        bit = int(format(value, '03b')[input_bit])
                        other = value ^ (1 << (2 - input_bit))
                        q2, a2 = ref.encode(p, op, other), ref.answer(op, p.nd, other)
                        assert ref.parse(p.name, q2) == (op, other)
                        assert [i for i, (a, b) in enumerate(zip(q, q2)) if a != b] == [5 + input_bit]
                        for output_bit in range(3):
                            prefix = answer[:output_bit]
                            z, prob = probabilities(net, q + prefix)
                            z2, prob2 = probabilities(net, q2 + prefix)
                            consistent = prefix == a2[:output_bit]
                            if input_bit == output_bit:
                                assert consistent
                            delta = float((prob2[1] - prob[1]) * (1 if bit == 0 else -1))
                            row = {'phase': phase, 'split': split_name, 'seed': seed, 'H': hidden,
                                   'new_percent': ratio if phase == 'after' else None, 'operator': ref.NAMES[op],
                                   'subset': subset, 'value': value, 'counterfactual_value': other,
                                   'input_bit_msb_first': input_bit, 'output_bit': output_bit,
                                   'prefix_consistent': consistent, 'fixed_prefix': prefix,
                                   'delta_p1_input_0_to_1': delta, 'Q': q, 'counterfactual_Q': q2}
                            probes.append(row)
                            groups[(phase, hidden, ref.NAMES[op], 'train' if subset == 'train' else 'heldout',
                                    input_bit, output_bit, consistent)].append(delta)
            assert ref.equal_state(frozen, net.state())
        p = ref.PHASES[4]
        for value in range(8):
            q, a = ref.encode(p, 0, value), ref.answer(0, 3, value)
            for j, token in enumerate(a + 'S'):
                z0, _ = probabilities(before, q + a[:j])
                z1, _ = probabilities(after, q + a[:j])
                index = '01S'.index(token)
                margin0 = float(z0[index] - max(np.delete(z0, index)))
                margin1 = float(z1[index] - max(np.delete(z1, index)))
                margins.append({'split': split_name, 'seed': seed, 'H': hidden, 'new_percent': ratio,
                                'value': value, 'position': j, 'Q': q, 'target_token': token,
                                'margin_before': margin0, 'margin_after': margin1,
                                'change': margin1 - margin0})
    assert len(source_hashes) == 36
    for relative, digest in source_hashes.items():
        assert old.sha(archive / relative) == digest
    matrices = [{'phase': k[0], 'H': k[1], 'operator': k[2], 'subset': k[3], 'input_bit': k[4],
                 'output_bit': k[5], 'prefix_consistent': k[6], 'count': len(v),
                 'mean_signed_delta_p1': float(np.mean(v)), 'minimum': min(v), 'maximum': max(v)}
                for k, v in sorted(groups.items())]
    cascade = []
    for op in ('echo', 'neg'):
        selected = [r for r in errors if r['phase'] == 'after' and r['operator'] == op and r['subset'] != 'train']
        cascade.append({'operator': op, 'heldout_rows': len(selected),
                        'free_wrong_by_position': [sum(r['free_wrong'][i] for r in selected) for i in range(5)],
                        'teacher_wrong_by_position': [sum(r['teacher_wrong'][i] for r in selected) for i in range(5)],
                        'first_wrong_by_position': [sum(r['first_wrong_position'] == i for r in selected) for i in range(5)],
                        'later_errors_rescued_by_teacher_prefix': [sum(r['prefix_rescued_later_positions'][i] for r in selected) for i in range(5)]})
    old.dump(out / 'first-errors.json', errors)
    old.dump(out / 'counterfactual-probes.json', probes)
    old.dump(out / 'sensitivity-matrices.json', matrices)
    old.dump(out / 'paired-echo-margins.json', margins)
    compact = {'status': 'passed', 'checkpoints_unchanged': source_hashes, 'error_rows': len(errors),
               'counterfactual_rows': len(probes), 'all_Q_flips_single_legal_data_bit': True,
               'diagonal_prefix_consistency_checked': True, 'old_saved_truth_tables_recomputed_equal': True,
               'teacher_vs_free_cascade': cascade,
               'interpretation': 'conditional frozen-network probes, not a proof of a unique internal algorithm'}
    old.dump(out / 'compact.json', compact)
    return compact
