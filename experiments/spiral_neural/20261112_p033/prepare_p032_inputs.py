"""Combine public PR6 checkpoints and P033 trace supplement into fresh inputs."""
import argparse
import hashlib
import shutil
from pathlib import Path


def prepare(p032_evidence, p033_evidence, out):
    p032_evidence, p033_evidence = Path(p032_evidence), Path(p033_evidence)
    out = Path(out)
    if out.exists():
        raise FileExistsError('Never overwrite original evidence; choose a fresh input directory')
    files = []
    for split in ('S0', 'S1'):
        for seed in (101, 202, 303):
            for hidden in (72, 128):
                root = Path('training') / f'{split}-seed{seed}-H{hidden}'
                files.append((p032_evidence, root / 'warm-3/final-state.npz'))
                for ratio in (70, 50):
                    for name in ('final-state.npz', 'final-truth-table.json'):
                        files.append((p032_evidence, root / f'neg{ratio}' / name))
            for folder in ('warm-0', 'warm-1', 'warm-2', 'warm-3', 'neg70'):
                files.append((p033_evidence / 'p032-trace-supplement',
                              Path('training') / f'{split}-seed{seed}-H72' / folder / 'trace.json'))
    for source_root, relative in files:
        resolved = (source_root / relative).resolve(strict=True)
        resolved.relative_to(source_root.resolve(strict=True))
        if not resolved.is_file():
            raise ValueError('Missing public input: ' + str(relative))
    out.mkdir(parents=True)
    for source_root, relative in files:
        source, destination = source_root / relative, out / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(destination.read_bytes()).digest()
    return len(files)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--p032-evidence', type=Path, required=True)
    p.add_argument('--p033-evidence', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    print({'copied_files_verified': prepare(args.p032_evidence, args.p033_evidence, args.out)})
