"""P035 fixed raw-input codecs and one shared semantic course; never trains.

S uses the unchanged P031 student_io grammar. H is a new compact unary-slice
hierarchy: math-branch1 | local operator ID | unsigned value. Both arms learn
the same P031 result word (information bits plus syntax-tail0), then output S.
Thus this experiment isolates the input codec, not native-output compression.
"""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import numpy as np

HERE = Path(__file__).resolve().parent
REFERENCE = HERE / 'reference'
P031_COMMIT = 'cee9fb7c331f23d9b7495f7240cc45060c19838d'
PRO_PLAN_COMMIT = '4e2ded91166a4fd9348dccf8fc71ddf01e991645'
REFERENCE_PINS = {
    'student_io.py': ('903ac64564a58852689283ef972e38bba3fda82f31a3ca25a45b1b0574770281', 'e09b40fa9f6e6cd555a2eb56b34a3b9804925eb5'),
    'teacher.py': ('b27ba59d71d3e7798170008befbef05aaadb7705fbd36f177f2070fbca36a708', '23e073d858ae543ceba7b311f36c3f8b0c23301a'),
    'reference_codec.py': ('56f337ee606f479ddf590d774235729d99d64ec54d5ac755822b87bd54b0afb4', '35217a0a0b082a09e86e39e956f61b31a31ff46a'),
    'p030_reference.py': ('db39661a7b16d13e64db7acc5dae22a81ca59dc39cf467ed4c58addbc0654013', '8b41433c6415c6d0927d69ed0aad14ff035fbe40'),
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_references():
    result = {}
    for name, (expected_sha, expected_blob) in REFERENCE_PINS.items():
        raw = (REFERENCE / name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
        if (digest, git_blob) != (expected_sha, expected_blob):
            raise ValueError('Pinned historical reference mismatch: ' + name)
        result[name] = {'sha256': digest, 'git_blob': git_blob, 'bytes': len(raw)}
    return result


# Refuse to execute an unpinned inherited codec/oracle implementation.
verify_references()
sys.path.insert(0, str(REFERENCE))
import student_io as sle
import teacher as offline_teacher
import reference_codec as legacy

CODECS = ('S', 'H')
CODEC_NAMES = {'S': 'SLE-Original', 'H': 'Flat-Hierarchical-unary-v1'}
OP_NAMES = {0: 'echo', 1: 'neg'}
NAMES_TO_OP = {name: op for op, name in OP_NAMES.items()}
SEEDS = (101, 202, 303)
COURSE_RNG_BASE = 350000


@dataclass(frozen=True)
class Stage:
    index: int
    name: str
    transition: str
    n_op: int
    n_data: int
    ops: tuple[int, ...]
    highwater: int
    train: tuple[int, ...]
    val: tuple[int, ...]
    test: tuple[int, ...]
    L: int
    H: int
    mac_cap: int

    @property
    def profile(self):
        return sle.Profile(self.name, self.n_op, self.n_data,
                           tuple(OP_NAMES[op] for op in self.ops), False,
                           layer=1, version='v0', highwater=self.highwater)

    @property
    def split(self):
        return {name: list(getattr(self, name)) for name in ('train', 'val', 'test')}

    @property
    def targets_per_lesson(self):
        return self.n_data + 2  # n_data information, one syntax tail, one STOP


STAGES = (
    Stage(0, 's0_echo_d1', 'initial_echo', 1, 1, (0,), 0, (0, 1), (), (), 8, 64, 37881000),
    Stage(1, 's1_echo_d2', 'data_width_only', 1, 2, (0,), 0, (0, 1, 2, 3), (), (), 10, 66, 50508000),
    Stage(2, 's2_echo_d3', 'data_width_only', 1, 3, (0,), 0, (0, 1, 2, 3, 5, 7), (4,), (6,), 12, 68, 63135000),
    Stage(3, 's3_op2', 'operator_width_only', 2, 3, (0,), 0, (0, 1, 2, 3, 5, 7), (4,), (6,), 13, 69, 63135000),
    Stage(4, 's4_neg', 'new_semantics_same_shape', 2, 3, (0, 1), 1, (0, 1, 2, 3, 5, 7), (4,), (6,), 13, 69, 63135000),
)
MILESTONES = (
    ('Echo_0_1', tuple((0, value) for value in range(2))),
    ('Echo_0_3', tuple((0, value) for value in range(4))),
    ('Echo_0_7', tuple((0, value) for value in range(8))),
    ('Echo_and_Neg_0_7', tuple((op, value) for op in (0, 1) for value in range(8))),
)


def get_stage(stage):
    if isinstance(stage, Stage) and stage in STAGES:
        return stage
    if type(stage) is int and 0 <= stage < len(STAGES):
        return STAGES[stage]
    if isinstance(stage, str):
        for item in STAGES:
            if item.name == stage:
                return item
    raise ValueError('Unknown fixed P035 stage/profile')


def get_codec(codec):
    if codec in CODECS:
        return codec
    matches = [key for key, name in CODEC_NAMES.items() if name == codec]
    if len(matches) == 1:
        return matches[0]
    raise ValueError('Unknown fixed P035 codec')


def validate_ast(stage, op, value):
    stage = get_stage(stage)
    if type(op) is not int or op not in stage.ops:
        raise ValueError('Inactive or unsupported operator')
    if type(value) is not int or not 0 <= value < 2 ** stage.n_data:
        raise ValueError('Operand outside declared width')
    return stage


def encode(codec, stage, op, value):
    codec = get_codec(codec)
    stage = validate_ast(stage, op, value)
    if codec == 'S':
        return sle.encode_question(sle.Question(OP_NAMES[op], (value,)), stage.profile)
    return '1' + format(op, f'0{stage.n_op}b') + format(value, f'0{stage.n_data}b')


def decode_syntax(codec, stage, raw):
    """Host-only inverse, with no answer calculation or student-side parsing."""
    codec, stage = get_codec(codec), get_stage(stage)
    sle.require_bits(raw)
    if codec == 'S':
        question = sle.parse_question(raw, stage.profile)
        op, value = NAMES_TO_OP[question.operator], question.operands[0]
    else:
        if len(raw) != 1 + stage.n_op + stage.n_data or raw[0] != '1':
            raise ValueError('Wrong compact branch/frame length')
        op, value = int(raw[1:1 + stage.n_op], 2), int(raw[1 + stage.n_op:], 2)
    validate_ast(stage, op, value)
    return op, value


def answer(stage, op, value):
    """Offline teacher label, shared by both codecs; never used by generate()."""
    stage = validate_ast(stage, op, value)
    return offline_teacher.oracle(sle.Question(OP_NAMES[op], (value,)), stage.profile)


def decode_response(stage, generated):
    stage = get_stage(stage)
    bits = sle.normalize_nn(generated)
    if len(bits) != stage.n_data + 1 or bits[-1] != '0':
        raise ValueError('Wrong common result width or syntax tail')
    return int(bits[:-1], 2)


def max_context(codec, stage):
    stage = get_stage(stage)
    return max(len(encode(codec, stage, op, value)) + len(answer(stage, op, value))
               for op in stage.ops for value in range(2 ** stage.n_data))


def tensor_prefix(raw_prefix, L):
    """Exactly the existing MLP's two-channel 01 input, with zero padding."""
    sle.require_bits(raw_prefix)
    if type(L) is not int or L <= 0 or len(raw_prefix) > L:
        raise ValueError('Binary prefix outside context')
    slots = np.zeros((L, 2), dtype=np.float32)
    for i, bit in enumerate(raw_prefix):
        slots[i, int(bit)] = 1
    return slots.reshape(1, -1)


def semantic_course(stage, seed, count):
    """Any length of the same per-stage/seed balanced pair-block stream.

    F/G may receive different prefix lengths under their respective MAC caps.
    S/H at the same strategy share every AST at the same lesson ordinal.
    This host RNG is separate from the student's initialization/growth RNG.
    """
    stage = get_stage(stage)
    if type(seed) is not int or type(count) is not int or count < 0:
        raise ValueError('Integer seed and nonnegative course count required')
    pairs = [(op, value) for op in stage.ops for value in stage.train]
    rng = np.random.default_rng(seed + COURSE_RNG_BASE + 1000 * stage.index)
    result = []
    while len(result) < count:
        result.extend(pairs[int(i)] for i in rng.permutation(len(pairs)))
    return result[:count]


def step_macs(L, H):
    if type(L) is not int or type(H) is not int or min(L, H) <= 0:
        raise ValueError('Positive integer MLP shape required')
    return H * (4 * L + 9)


def lesson_budget(stage, policy):
    stage = get_stage(stage)
    if policy not in ('F', 'G'):
        raise ValueError('Policy must be fixed-final F or stage-growth G')
    capacity = STAGES[-1] if policy == 'F' else stage
    per_lesson = step_macs(capacity.L, capacity.H) * stage.targets_per_lesson
    count = stage.mac_cap // per_lesson
    return {'lessons': count, 'target_updates': count * stage.targets_per_lesson,
            'L': capacity.L, 'H': capacity.H, 'MAC_per_target': step_macs(capacity.L, capacity.H),
            'MAC_per_lesson': per_lesson, 'MAC_cap': stage.mac_cap,
            'executed_train_MACs': count * per_lesson, 'unused_MACs': stage.mac_cap - count * per_lesson,
            'unused_MACs_carry': False}


def exposure_ledger(courses):
    """Planned or actual AST exposures, never attached to student raw inputs.

    courses is a stage-ordered sequence; missing later stages stay absent.
    Value exposure and operator-value exposure are separate. Width-sensitive
    Neg semantics additionally have a width-qualified counter.
    """
    if len(courses) > len(STAGES):
        raise ValueError('Too many stages')
    values, pairs, semantic = Counter(), Counter(), Counter()
    rows = []
    for stage, course in zip(STAGES, courses):
        current = Counter()
        for op, value in course:
            validate_ast(stage, op, value)
            if value not in stage.train:
                raise ValueError('Heldout question entered training course')
            current[(op, value)] += 1
        for op in stage.ops:
            for value in range(2 ** stage.n_data):
                task = (op, value, stage.n_data if op == 1 else None)
                subset = next(name for name in ('train', 'val', 'test') if value in getattr(stage, name))
                rows.append({'stage': stage.name, 'op': op, 'value': value, 'subset': subset,
                             'prior_value_presentations': values[value],
                             'prior_op_value_presentations': pairs[(op, value)],
                             'prior_exact_math_task_presentations': semantic[task],
                             'value_seen_before_stage': bool(values[value]),
                             'op_value_seen_before_stage': bool(pairs[(op, value)]),
                             'exact_math_task_seen_before_stage': bool(semantic[task]),
                             'current_stage_training_presentations': current[(op, value)],
                             'width_qualified_Neg_semantics': stage.n_data if op == 1 else None})
        for (op, value), count in current.items():
            values[value] += count
            pairs[(op, value)] += count
            semantic[(op, value, stage.n_data if op == 1 else None)] += count
    return rows


def milestone_score(correct):
    """Final op2/data3 exact+STOP correctness mapping keyed by (op,value)."""
    expected = {(op, value) for op in (0, 1) for value in range(8)}
    if set(correct) != expected or any(type(value) is not bool for value in correct.values()):
        raise ValueError('All sixteen final-format boolean outcomes required')
    blocks, score, continuing = [], 0, True
    for index, (name, pairs) in enumerate(MILESTONES, 1):
        whole = sum(correct[pair] for pair in pairs)
        passed = whole == len(pairs)
        continuing = continuing and passed
        if continuing:
            score = index
        blocks.append({'milestone': index, 'name': name, 'whole': whole, 'total': len(pairs), 'passed': passed})
    return {'score': score, 'maximum': 4, 'blocks': blocks,
            'format': STAGES[-1].name, 'includes_STOP': True,
            'operator_width_event_is_not_an_extra_skill': True}


def description():
    stages = []
    for stage in STAGES:
        stages.append(asdict(stage) | {'split': stage.split,
            'tree': {'math': {'operator_branch': {'highwater': stage.highwater,
                                                 'local_ids': {OP_NAMES[op]: op for op in stage.ops}}}},
            'Q_lengths': {codec: len(encode(codec, stage, 0, 0)) for codec in CODECS},
            'answer_bits': stage.n_data + 1, 'target_updates_per_lesson': stage.targets_per_lesson,
            'max_context': {codec: max_context(codec, stage) for codec in CODECS},
            'budget': {policy: lesson_budget(stage, policy) for policy in ('F', 'G')}})
    return {'schema': 'p035-codec-course/1', 'codecs': CODEC_NAMES,
            'S': 'unchanged P031 student_io layer1/v0, noEND:01|opID|0|value|0',
            'H': 'new compact unary slice:math-branch1|fixed-width local opID|fixed-width unsigned value;control branch0 reserved; no terminators; profile/version supplied to host only',
            'response': 'Both codecs share P031 result word:n_data information bits+syntax0; external STOP S. Input-codec study, not shortest native-output comparison.',
            'course': 'np.default_rng(seed+350000+1000*stage.index); shuffle entire(op,value) block; repeat, then truncate at full-lesson MAC boundary',
            'stages': stages, 'total_MAC_cap': sum(stage.mac_cap for stage in STAGES),
            'd1_d2_blind_holdouts': False, 'd3_new_blind_domain': False,
            'heldout_interpretation': 'Values4/6 absent from all training; these do not independently isolate unseen pairs whose values were seen. NewNeg transition does distinguish seen values from unseen(op,value).',
            'student_interface': 'Only each codec raw Q+current binary answer prefix; no AST/profile/length/op/answer features.',
            'references': verify_references(), 'P031_commit': P031_COMMIT, 'Pro_PR8_plan_commit': PRO_PLAN_COMMIT}


def run_checks(out):
    import p030_reference as old
    before = verify_references()
    references_unchanged = {name: sha(REFERENCE / name) for name in REFERENCE_PINS}
    for module, name in ((sle, 'student_io.py'), (offline_teacher, 'teacher.py'),
                         (legacy, 'reference_codec.py'), (old, 'p030_reference.py')):
        assert sha(Path(module.__file__)) == REFERENCE_PINS[name][0], ('loaded historical module mismatch', name)
    protocol_path = HERE / 'protocol.json'
    protocol_hash = sha(protocol_path)
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    assert protocol['codecs'] == list(CODEC_NAMES.values())
    for stage, declared in zip(STAGES, protocol['stages'], strict=True):
        assert (stage.name, stage.n_op, stage.n_data, stage.L, stage.H, stage.mac_cap) == (
            declared['id'], declared['n_op'], declared['n_data'], declared['L'], declared['H'], declared['training_MAC_cap'])
        assert list(stage.ops) == [NAMES_TO_OP[name] for name in declared['ops']]
        assert stage.split == {name: declared[name] for name in ('train', 'val', 'test')}
        assert stage.targets_per_lesson == declared['targets_per_lesson']
    out.mkdir(parents=True, exist_ok=False)
    tensors, interface, roundtrips, targets = {}, [], 0, 0
    expected_q = {'S': [6, 7, 8, 9, 9], 'H': [3, 4, 5, 6, 6]}
    expected_context = {'S': [8, 10, 12, 13, 13], 'H': [5, 7, 9, 10, 10]}
    position = sle.CurriculumPosition()
    for stage in STAGES:
        position.advance(stage.profile)
        probe = old.Model(3501, stage.L, stage.H)
        saved = probe.state()
        seen_questions = {codec: set() for codec in CODECS}
        prefix_labels = {codec: {} for codec in CODECS}
        for op in stage.ops:
            for value in range(2 ** stage.n_data):
                a = answer(stage, op, value)
                data = format(value, f'0{stage.n_data}b') + '0'
                assert a == legacy.calc(OP_NAMES[op], [data]) == old.answer(op, stage.n_data, value)
                assert decode_response(stage, a + 'S') == int(a[:-1], 2)
                actual = {}
                for codec in CODECS:
                    q = encode(codec, stage, op, value)
                    assert q not in seen_questions[codec]
                    seen_questions[codec].add(q)
                    assert len(q) == expected_q[codec][stage.index]
                    assert decode_syntax(codec, stage, q) == (op, value)
                    assert len(q) + len(a) == max_context(codec, stage) == expected_context[codec][stage.index]
                    assert len(q) + len(a) <= stage.L
                    actual[codec] = []
                    for bit, target in enumerate(a + 'S'):
                        prefix = q + a[:bit]
                        assert prefix_labels[codec].setdefault(prefix, target) == target
                        array = tensor_prefix(prefix, stage.L)
                        # Actual unchanged NN entrance, not a codec-decoded AST.
                        original_x = probe.forward(prefix)[0]
                        assert np.array_equal(array, original_x)
                        key = f'{stage.index}_{op}_{value}_{codec}_{bit}'
                        tensors[key] = original_x.copy()
                        actual[codec].append(original_x.copy())
                    roundtrips += 1
                assert all(not np.array_equal(s, h) for s, h in zip(actual['S'], actual['H']))
                targets += len(a + 'S')
                interface.append({'stage': stage.name, 'op': op, 'value': value,
                                  'raw_questions': {codec: encode(codec, stage, op, value) for codec in CODECS},
                                  'shared_targets': a + 'S', 'same_answer_and_target_order': True,
                                  'raw_NN_tensors_differ_at_every_target': True})
        assert old.equal_state(saved, probe.state()) and probe.t == 0
    negatives = 0

    def rejects(call):
        nonlocal negatives
        try:
            call()
        except ValueError:
            negatives += 1
        else:
            raise AssertionError('Invalid input accepted')

    for stage in STAGES:
        for codec in CODECS:
            q = encode(codec, stage, 0, 0)
            for malformed in (q[:-1], q + '0', q + 'S', q.replace('0', '2', 1)):
                rejects(lambda c=codec, s=stage, raw=malformed: decode_syntax(c, s, raw))
            rejects(lambda c=codec, s=stage: encode(c, s, 2, 0))
            rejects(lambda c=codec, s=stage: encode(c, s, 0, 2 ** s.n_data))
        rejects(lambda s=stage: decode_syntax('H', s, '0' + encode('H', s, 0, 0)[1:]))
        rejects(lambda s=stage: decode_response(s, answer(s, 0, 0)))
        rejects(lambda s=stage: decode_response(s, answer(s, 0, 0) + 'SS'))
    rejects(lambda: position.advance(STAGES[3].profile))
    rejects(lambda: position.advance(STAGES[2].profile))
    rejects(lambda: get_stage('unknown'))
    for codec in CODECS:
        # Adjacent width profiles reject each other's differing raw frames.
        for previous, current in zip(STAGES[:3], STAGES[1:4]):
            rejects(lambda c=codec, p=previous, s=current: decode_syntax(c, p, encode(c, s, 0, 0)))
        rejects(lambda c=codec: decode_syntax(c, STAGES[3], encode(c, STAGES[4], 1, 0)))
        # Local IDs zero-extend on operator-width growth; Echo numeric value
        # survives data widening, but no automatic NN function transfer claim.
        for value in range(8):
            assert decode_syntax(codec, STAGES[3], encode(codec, STAGES[3], 0, value)) == (0, value)
            assert encode(codec, STAGES[3], 0, value) == encode(codec, STAGES[4], 0, value)
        for previous, current in zip(STAGES[:2], STAGES[1:3]):
            for value in range(2 ** previous.n_data):
                assert int(answer(previous, 0, value)[:-1], 2) == int(answer(current, 0, value)[:-1], 2) == value
    # Legal0 has an active channel; it is never confused with padding.
    zero = tensor_prefix('0', 2).reshape(2, 2)
    assert zero.tolist() == [[1., 0.], [0., 0.]]
    course_checks, ledgers = [], {}
    for seed in SEEDS:
        for policy in ('F', 'G'):
            courses = []
            for stage in STAGES:
                budget = lesson_budget(stage, policy)
                count = budget['lessons']
                course = semantic_course(stage, seed, count)
                assert course == semantic_course(stage, seed, count + 37)[:count]
                pairs = {(op, value) for op in stage.ops for value in stage.train}
                exposure = Counter(course)
                assert set(course) == pairs and max(exposure.values()) - min(exposure.values()) <= 1
                block = len(pairs)
                for start in range(0, count - block + 1, block):
                    assert set(course[start:start + block]) == pairs
                assert budget['executed_train_MACs'] <= budget['MAC_cap']
                assert budget['unused_MACs'] < budget['MAC_per_lesson']
                assert budget['target_updates'] == len(course) * stage.targets_per_lesson
                if policy == 'F':
                    assert count == 3000
                courses.append(course)
                course_checks.append({'seed': seed, 'policy': policy, 'stage': stage.name,
                                      **budget, 'course_sha256': hashlib.sha256(canonical(course).encode('utf-8')).hexdigest(),
                                      'exposure': {f'{op}:{value}': exposure[(op, value)] for op, value in sorted(pairs)}})
            ledger = exposure_ledger(courses)
            for row in ledger:
                if row['subset'] != 'train':
                    assert not row['value_seen_before_stage'] and not row['current_stage_training_presentations']
                if row['stage'] == STAGES[-1].name and row['op'] == 1 and row['subset'] == 'train':
                    assert row['value_seen_before_stage'] and not row['op_value_seen_before_stage']
            ledgers[f'{policy}-seed{seed}'] = ledger
    wrong = {(op, value): False for op in (0, 1) for value in range(8)}
    assert milestone_score(wrong)['score'] == 0
    perfect = {key: True for key in wrong}
    assert milestone_score(perfect)['score'] == 4
    for n in range(1, 4):
        partial = wrong | {pair: True for pair in MILESTONES[n - 1][1]}
        assert milestone_score(partial)['score'] == n
    assert references_unchanged == {name: sha(REFERENCE / name) for name in REFERENCE_PINS}
    assert sha(protocol_path) == protocol_hash
    assert sum(stage.mac_cap for stage in STAGES) == 277794000
    assert [lesson_budget(stage, 'G')['lessons'] for stage in STAGES] == protocol['budget']['G_expected_lessons']
    assert sum(lesson_budget(stage, 'G')['executed_train_MACs'] for stage in STAGES) == protocol['budget']['G_expected_MAC']
    assert sum(lesson_budget(stage, 'G')['target_updates'] for stage in STAGES) == protocol['budget']['G_expected_target_updates']
    np.savez(out / 'actual-NN-interface-tensors.npz', **tensors)
    for name, value in (('codec-course-description.json', description()), ('actual-NN-interface.json', interface),
                        ('course-checks.json', course_checks), ('exposure-ledgers.json', ledgers)):
        (out / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    result = {'status': 'passed', 'scope': 'codec/course/actual-input engineering only; no gradient updates or scientific training',
              'roundtrip_AST_codec_cases': roundtrips, 'shared_target_prefixes_per_codec': targets,
              'actual_MLP_input_tensors_checked': len(tensors), 'malformed_inputs_rejected': negatives,
              'all_same_AST_targets_equal_and_inputs_different': True,
              'semantic_courses_checked': len(course_checks), 'balanced_pair_blocks_and_prefix_identity': True,
              'd1_d2_train0_and1_no_blind_holdouts': True, 'cross_stage_value_pair_semantics_ledger_checked': True,
              'monotonic_profile_and_common_context_capacity': True,
              'final_four_cumulative_milestones_checked': True, 'scientific_updates': 0,
              'source_sha256': sha(Path(__file__).resolve()), 'references': before,
              'protocol_sha256': protocol_hash,
              'reference_original_bytes_unchanged': True, 'numpy': np.__version__}
    (out / 'checks.json').write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'references'}, ensure_ascii=False))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--out', type=Path, default=HERE.parents[1] / 'work/sle-p035/codec-checks')
    args = parser.parse_args()
    if args.check:
        run_checks(args.out)
    else:
        print(json.dumps(description(), ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
