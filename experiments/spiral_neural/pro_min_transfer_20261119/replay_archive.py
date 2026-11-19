"""Verify the delivered archive, unpack it into a fresh directory, then replay both registered studies."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent

def digest(data):
    return hashlib.sha256(data).hexdigest()

def replay(archive,receipt_path):
    receipt=json.loads(receipt_path.read_text())
    assert archive.stat().st_size==receipt['size_bytes']
    assert digest(archive.read_bytes())==receipt['sha256']
    with tempfile.TemporaryDirectory() as tmp:
        extract=Path(tmp)
        with ZipFile(archive) as z:
            names=z.namelist()
            assert len(names)==len(set(names))==receipt['members']
            assert z.testzip() is None
            assert all(not PurePosixPath(k).is_absolute() and '..' not in PurePosixPath(k).parts for k in names)
            expected={k:v for v,k in [line.split('  ',1) for line in z.read('SHA256SUMS').decode().splitlines()]}
            assert set(expected)==set(names)-{'SHA256SUMS'}
            assert all(digest(z.read(k))==v for k,v in expected.items())
            z.extractall(extract)
        env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
        commands={
            'main':['min_transfer_20261119/replay.py'],
            'independent':['review/independent_replay.py','min_transfer_20261119'],
            'staged':['min_stage_1119/verify_staged.py'],
            'census':['min_census_1119/census.py','--verify'],
        }
        summaries={}
        for label,args in commands.items():
            out=subprocess.run([sys.executable,*args],env=env,cwd=extract,text=True,capture_output=True)
            if out.returncode:
                raise RuntimeError(label+' failed: '+out.stderr)
            results=json.loads(out.stdout)
            assert results['status']=='PASS',label
            summaries[label]={k:v for k,v in results.items() if isinstance(v,(int,float)) or k=='status'}
        return dict(status='PASS',archive=archive.name,sha256=receipt['sha256'],size_bytes=receipt['size_bytes'],
                    zip_members=len(names),verified_payload_hashes=len(expected),independent_extraction=True,
                    replay=summaries)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('archive',type=Path)
    ap.add_argument('--receipt',type=Path,default=HERE/'archive_delivery.json')
    opts=ap.parse_args()
    print(json.dumps(replay(opts.archive,opts.receipt),indent=2))
