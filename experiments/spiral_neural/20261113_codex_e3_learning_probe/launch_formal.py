"""Run the frozen six-arm CPU probe once; exclusive logs prevent relaunch."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path(__file__).resolve().parent
receipt = json.loads((root / 'git-prereg-receipt.json').read_text(encoding='utf-8'))
assert receipt['all_actual_bytes_verified'] is True
assert len(receipt['preregistration_commit']) == 40
assert len(receipt['manifest_sha256']) == 64
assert not (root / 'science').exists()
assert not (root / 'formal-command-result.json').exists()
env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
command = [sys.executable, '-X', 'utf8', '-B', str(root.parents[1] / 'outputs/e3-learning-probe/run_probe.py'),
           '--execute', '--manifest', str(root / 'prereg/manifest.json'),
           '--approved-manifest-sha', receipt['manifest_sha256'],
           '--preregistration-commit', receipt['preregistration_commit'], '--out', str(root / 'science')]
with (root / 'execution.stdout.log').open('xb') as out, (root / 'execution.stderr.log').open('xb') as err:
    started = time.perf_counter()
    result = subprocess.run(command, env=env, stdout=out, stderr=err, check=False)
    seconds = time.perf_counter() - started
summary = {'exit_code': result.returncode, 'formal_seconds': seconds, 'command_invocations': 1, 'command': command}
with (root / 'formal-command-result.json').open('x', encoding='utf-8') as stream:
    json.dump(summary, stream, indent=2)
    stream.write('\n')
print(json.dumps(summary), flush=True)
sys.exit(result.returncode)
