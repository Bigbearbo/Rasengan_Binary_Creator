"""Verify and optionally restore every exact original Git file; no neural execution."""
import argparse,hashlib,io,json,zipfile
from pathlib import Path
def sha(raw): return hashlib.sha256(raw).hexdigest()
p=argparse.ArgumentParser(); p.add_argument('--out',type=Path); p.add_argument('--verify-only',action='store_true'); a=p.parse_args()
root=Path(__file__).resolve().parent; m=json.loads((root/'TRANSFER_MANIFEST.json').read_text(encoding='utf-8')); chunks=[]
for part in m['parts']:
    assert Path(part['name']).name==part['name']; b=(root/part['name']).read_bytes(); assert (len(b),sha(b))==(part['bytes'],part['sha256']); chunks.append(b)
raw=b''.join(chunks); assert (len(raw),sha(raw))==(m['archive']['bytes'],m['archive']['sha256'])
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(m['files']) and z.testzip() is None
    for name,expected in m['files'].items():
        b=z.read(name); assert (len(b),sha(b))==(expected['bytes'],expected['sha256'])
    publication=json.loads(z.read(m['prefix']+'/publication-manifest.json')); members=0
    for name,expected in publication['archives'].items():
        b=z.read(m['prefix']+'/'+name); assert (len(b),sha(b))==(expected['bytes'],expected['sha256'])
        with zipfile.ZipFile(io.BytesIO(b)) as nested:
            assert nested.testzip() is None and set(nested.namelist())==set(expected['members'])
            for member,check in expected['members'].items():
                value=nested.read(member); assert (len(value),sha(value),f'{nested.getinfo(member).CRC:08x}')==(check['bytes'],check['sha256'],check['CRC32']); members+=1
    if not a.verify_only:
        target=(a.out or root/'recovered').resolve(); target.mkdir(parents=True,exist_ok=False)
        for name in m['files']:
            dest=(target/name).resolve(); assert dest.is_relative_to(target); dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as stream: stream.write(z.read(name))
print(json.dumps(dict(status='passed',original_git_files=len(m['files']),verified_nested_members=members,model_calls=0,optimizer_updates=0,restored=not a.verify_only)),flush=True)
