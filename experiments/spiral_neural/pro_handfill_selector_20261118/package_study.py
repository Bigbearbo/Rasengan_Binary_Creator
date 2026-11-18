"""Create one immutable research archive and retain exact file timing evidence."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'sle_handfill_selector_20261118_v1.zip'
if OUT.exists():
    raise FileExistsError(OUT)
manifest_path=ROOT/'payload_manifest.json'
if manifest_path.exists():
    raise FileExistsError(manifest_path)
files=sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
assert all(not p.is_symlink() for p in files)
entries=[]
for p in files:
    raw=p.read_bytes()
    entries.append({'path':str(p.relative_to(ROOT)),'size_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'mtime_ns':p.stat().st_mtime_ns})
manifest={'schema':'handfill-selector-immutable-payload-v1','run':'pro_handfill_selector_20261118_v1','root':ROOT.name,'created_utc':datetime.now(timezone.utc).isoformat(),'files':entries,'git':json.loads((ROOT/'git_results_receipt.json').read_text()),'note':'Manifest excludes its own hash; complete ZIP size/SHA are pinned externally.'}
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
with zipfile.ZipFile(OUT,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files+[manifest_path]:
        z.write(p,arcname=str(Path(ROOT.name)/p.relative_to(ROOT)))
with zipfile.ZipFile(OUT) as z:
    bad=z.testzip()
    assert bad is None,bad
    member_count=len(z.infolist())
receipt={'run':'pro_handfill_selector_20261118_v1','filename':OUT.name,'local_path':str(OUT),'size_bytes':OUT.stat().st_size,'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'zip_crc':'PASS','members':member_count,'hashed_payload_files':len(entries),'source_pull_request':'https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/133','results_git_commit':manifest['git']['results_git_commit']}
(ROOT.parent/'handfill_selector_archive_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
