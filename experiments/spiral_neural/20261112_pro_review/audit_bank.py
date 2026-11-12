"""Enumerate P031's exact teaching split; does not train or change the source bank."""
import argparse
import collections
import hashlib
import importlib
import json
import pathlib
import sys

EXPECTED_SHA256 = {
    'teacher.py': 'b27ba59d71d3e7798170008befbef05aaadb7705fbd36f177f2070fbca36a708',
    'reference_codec.py': '56f337ee606f479ddf590d774235729d99d64ec54d5ac755822b87bd54b0afb4',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bank-code', type=pathlib.Path, required=True)
    parser.add_argument('--out', type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Use a new output file')
    source_bytes = {name: (args.bank_code / name).read_bytes() for name in EXPECTED_SHA256}
    source_sha256 = {name: hashlib.sha256(data).hexdigest() for name, data in source_bytes.items()}
    if source_sha256 != EXPECTED_SHA256:
        raise ValueError('P031 source differs from reviewed commit cee9fb7')
    sys.path.insert(0, str(args.bank_code.resolve()))
    teacher = importlib.import_module('teacher')
    records = list(teacher.generate())
    groups = collections.defaultdict(lambda: {s: [] for s in ('train', 'val', 'test')})
    for task, raw in records:
        groups[(task.profile_id, task.operator)][task.split].append(list(task.operands))
    result = {
        'repo': 'Bigbearbo/Rasengan_Binary_Creator',
        'expected_source_commit': 'cee9fb7c331f23d9b7495f7240cc45060c19838d',
        'verified_source_sha256': source_sha256,
        'method': 'Enumeration of teacher.generate(); no training',
        'cases': len(records),
        'semantic_groups': len({task.semantic_group for task, _ in records}),
        'groups': [dict(profile=p, operator=o, counts={s: len(v) for s, v in subsets.items()}, operands=subsets)
                   for (p, o), subsets in groups.items()],
        'missing_splits': [dict(profile=p, operator=o, absent=[s for s, v in subsets.items() if not v])
                           for (p, o), subsets in groups.items() if any(not v for v in subsets.values())],
        'scope': 'P031 transport corpus, not the P032 training data. Unequal split sizes are documented. This audit evaluates readiness for an initial teaching curriculum.',
    }
    assert len(records) == 1342 and result['semantic_groups'] == 288
    for name, data in source_bytes.items():
        assert (args.bank_code / name).read_bytes() == data
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('cases', 'semantic_groups', 'missing_splits')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
