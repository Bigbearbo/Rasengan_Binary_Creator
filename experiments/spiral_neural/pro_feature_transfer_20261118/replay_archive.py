"""Verify the immutable PR132 archive, then replay independent output checks.

No experimental training is added. The verifier repeats only144 early Adam
recurrences, a diagnostic distinct from the36,864 experimental updates.
"""
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import zipfile

EXPECTED_SIZE=69558801
EXPECTED_SHA256='88afb3c9072a29b90382ab25281757c9e682ae68c37e5d71eb181c9c0a01a855'
ROOT_NAME='feature_transfer_20261118'

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('archive',type=Path)
    ap.add_argument('--receipt',type=Path)
    args=ap.parse_args()
    started=time.perf_counter()
    assert args.archive.is_file(),'Archive file required'
    assert args.archive.stat().st_size==EXPECTED_SIZE,'Wrong archive byte count'
    assert digest(args.archive)==EXPECTED_SHA256,'Wrong archive SHA256'
    if args.receipt and args.receipt.exists():
        raise FileExistsError(args.receipt)
    with tempfile.TemporaryDirectory(prefix='sle-feature-replay-') as td:
        temporary=Path(td)
        with zipfile.ZipFile(args.archive) as z:
            infos=z.infolist()
            names=[x.filename for x in infos]
            assert len(names)==len(set(names)),'Duplicate members'
            for item in infos:
                path=PurePosixPath(item.filename)
                assert not path.is_absolute() and '..' not in path.parts and '\\' not in item.filename
                assert path.parts[0]==ROOT_NAME
                assert not stat.S_ISLNK(item.external_attr>>16),'Unexpected symlink'
            assert z.testzip() is None,'CRC mismatch'
            manifest=json.loads(z.read(ROOT_NAME+'/payload_manifest.json'))
            assert manifest['run']=='pro_feature_transfer_20261118_v1'
            expected={ROOT_NAME+'/'+f['path'] for f in manifest['files']}|{ROOT_NAME+'/payload_manifest.json'}
            assert set(names)==expected,'Payload membership mismatch'
            z.extractall(temporary)
        root=temporary/ROOT_NAME
        for entry in manifest['files']:
            path=root/entry['path']
            assert path.stat().st_size==entry['size_bytes'],entry['path']
            assert digest(path)==entry['sha256'],entry['path']
            # Preserve original nanosecond timing evidence for the test barrier.
            os.utime(path,ns=(entry['mtime_ns'],entry['mtime_ns']))
        recorded=root/'receipts/result_audit.json'
        recorded_hash=digest(recorded)
        recorded.rename(root/'receipts/result_audit_recorded.json')
        env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        completed=subprocess.run([sys.executable,str(root/'verify_results.py')],cwd=root,env=env,
                                 capture_output=True,text=True,timeout=120)
        if completed.returncode:
            raise RuntimeError('Independent verifier failed:\n'+completed.stderr+'\n'+completed.stdout)
        audit=json.loads((root/'receipts/result_audit.json').read_text())
        assert audit['status']=='PASS' and audit['new_experimental_updates']==0
        assert audit['audit_recurrences']==144
        receipt={'schema':'feature-transfer-packaged-replay-v1','status':'PASS',
            'run':'pro_feature_transfer_20261118_v1','created_utc':datetime.now(timezone.utc).isoformat(),
            'archive_filename':args.archive.name,'size_bytes':EXPECTED_SIZE,'sha256':EXPECTED_SHA256,
            'zip_crc':'PASS','members':len(names),'payload_hashes_verified':len(manifest['files']),
            'recorded_audit_sha256':recorded_hash,'restored_original_mtime_ns':True,
            'new_experimental_updates':0,'verification_only_recurrences':144,
            'full_training_replays':0,'independent_audit':audit,
            'elapsed_seconds':time.perf_counter()-started}
    if args.receipt:
        args.receipt.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='independent_audit'},ensure_ascii=False))

if __name__=='__main__':
    main()
