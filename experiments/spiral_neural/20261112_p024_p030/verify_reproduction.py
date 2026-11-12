"""Compare a fresh portable P030 run with archived trace hashes and arrays."""
import sys
sys.dont_write_bytecode=True
import argparse,ast,hashlib,json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent

class FilesystemOnly(ast.NodeTransformer):
    def visit_ImportFrom(self,node):return None if node.module=='_archive_paths' else node
    def visit_Assign(self,node):
        names=[t.id if isinstance(t,ast.Name) else t.attr if isinstance(t,ast.Attribute) else None for t in node.targets]
        return None if any(n in {'ROOT','OUT','WORK','SOURCE','CHECKOUT'} for n in names) else self.generic_visit(node)
    def visit_Expr(self,node):
        c=node.value
        if isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute):
            v=c.func.value
            if c.func.attr=='insert' and isinstance(v,ast.Attribute) and isinstance(v.value,ast.Name) and v.value.id=='sys' and v.attr=='path':return None
            if c.func.attr=='mkdir' and isinstance(v,ast.Name) and v.id=='OUT':return None
        return self.generic_visit(node)

def without_times(value):
    if isinstance(value,dict):return {k:without_times(v) for k,v in value.items() if k!='seconds_training_and_probes'}
    if isinstance(value,list):return [without_times(v) for v in value]
    return value

def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);args=p.parse_args()
    fresh=args.work.resolve()/'p030-binary-continual-20261112';original=HERE/'evidence/p030-binary-continual-20261112'
    ast_checks=0
    for src in (HERE/'src').glob('*.py'):
        snapshot=HERE/'source_snapshot'/src.name
        if not snapshot.exists():continue
        a=FilesystemOnly().visit(ast.parse(snapshot.read_text(encoding='utf-8-sig')))
        b=FilesystemOnly().visit(ast.parse(src.read_text(encoding='utf-8-sig')))
        assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False),src.name;ast_checks+=1
    traces=0
    for row in json.loads((HERE/'omitted-traces.json').read_text(encoding='utf-8')):
        if row['run']!='p030-binary-continual-20261112':continue
        assert hashlib.sha256((fresh/row['path']).read_bytes()).hexdigest()==row['sha256'],row['path'];traces+=1
    arrays=0
    for old in original.rglob('*.npz'):
        new=fresh/old.relative_to(original)
        with np.load(old,allow_pickle=False) as a,np.load(new,allow_pickle=False) as b:
            assert set(a.files)==set(b.files) and all(np.array_equal(a[k],b[k]) for k in a.files),str(old.relative_to(original))
        arrays+=1
    a=json.loads((original/'compact.json').read_text());b=json.loads((fresh/'compact.json').read_text())
    for key in ['runs','scratch_controls','checks']:assert without_times(a[key])==without_times(b[key]),key
    print(json.dumps({'status':'passed','learning_AST_checks':ast_checks,'exact_trace_hashes':traces,
                      'exact_checkpoint_array_sets':arrays,'scientific_metrics_equal':True,'numpy':np.__version__}))

if __name__=='__main__':main()
