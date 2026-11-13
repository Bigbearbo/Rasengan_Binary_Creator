"""One bounded CPU subprocess; exclusive logs prevent accidental relaunch."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path(__file__).resolve().parent
publication = json.loads((root / 'git-prereg-receipt.json').read_text(encoding='utf-8'))
assert publication['all_actual_bytes_verified'] is True
commit = publication['preregistration_commit']
assert len(commit) == 40
assert not (root / 'science').exists()
assert not (root / 'formal-command-result.json').exists()
env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
command = [sys.executable, '-X', 'utf8', '-B', str(root.parents[1] / 'outputs/f2-stability/run_stability.py'),
           '--execute', '--manifest', str(root / 'prereg/manifest.json'), '--approved-manifest-sha',
           '1079366438d667f7bce2ac8fce983792b6c7bf935f4a200fb9eda4e9612e328c',
           '--preregistration-commit', commit, '--out', str(root / 'science')]
with (root / 'execution.stdout.log').open('xb') as out, (root / 'execution.stderr.log').open('xb') as err:
    start = time.perf_counter()
    result = subprocess.run(command, env=env, stdout=out, stderr=err, check=False)
    seconds = time.perf_counter() - start
record = {'exit_code': result.returncode, 'formal_seconds': seconds, 'command_invocations': 1, 'command': command}
with (root / 'formal-command-result.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(record), flush=True)
sys.exit(result.returncode)
