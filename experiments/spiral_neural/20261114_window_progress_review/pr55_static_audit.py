"""Read-only corpus/architecture audit of PR55, no model inference or training.

Extracts only pure generator definitions from pinned public sources with AST;
does not import training runners, torch, optimizers, or checkpoints.
"""
import argparse
import ast
import collections
import hashlib
import json
import itertools
from pathlib import Path
from types import SimpleNamespace

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo',type=Path,required=True,
                    help='Read-only repository checkout containing the pinned PR55 sources')
parser.add_argument('--output',type=Path,required=True,
                    help='New JSON evidence file; refuses to overwrite any existing file')
args=parser.parse_args()
ROOT=args.repo.resolve()
OUTPUT=args.output.resolve()
if OUTPUT.exists():
 parser.error(f'output already exists: {OUTPUT}')
if not OUTPUT.parent.is_dir():
 parser.error(f'output parent directory does not exist: {OUTPUT.parent}')
EXP=ROOT/'experiments/spiral_neural'
SHA='e745264ba8da233486b4632e69b093ac2833d7fb'

def selected(path,names,env):
    tree=ast.parse(path.read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),env)
    return env

source_paths={
 'pr36': EXP/'20261113_scheduled_role_swap_pilot/run.py',
 'pr39': EXP/'20261113_scheduled_input_target_exposure/run.py',
 'pr40': EXP/'20261113_scheduled_high_r_mixed/run.py',
 'pr55': EXP/'20261114_scheduled_weight_tying/run.py',
}
hashes={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in source_paths.items()}
assert hashes=={
 'pr36':'05e2d730eecefcb50fa92392697556ffde313f5ecb59c2f4e583aad52e321303',
 'pr39':'bf97b897c89f97a40d9e34247990112e4319513054eb873d02329e8b27dc9ffc',
 'pr40':'79dc4dca3c8e03f3889258a33532b639f5db11c0d3a6cf12dcba79443c826193',
 'pr55':'79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a',
}
e36=selected(source_paths['pr36'],['base_split','base_rows'],{})
e39=selected(source_paths['pr39'],['low_items','base_items'],{'parent':SimpleNamespace(**e36)})
e40=selected(source_paths['pr40'],['train_rows'],{'previous':SimpleNamespace(**e39)})
parent=e40['train_rows']()
assert len(parent)==120 and len(set(parent))==96
e55=selected(source_paths['pr55'],['word','question','answer','inject','course','eval_rows'],
             {'parent':lambda:parent,'HIGH':(16,17,18,19),'LOW':(0,1,2,3),'B':(18,19,22,23)})
course=e55['course']()
assert len(course)==136 and len(set(course))==112
word=e55['word'];answer=e55['answer'];question=e55['question']
cases=list(e55['eval_rows']())
assert len(cases)==len({question(v['r'],v['a'],v['b'],v['c'],v['d']) for v in cases})==156

rows=[answer(r,a,b) for r,a,b,c,d in course]
assert sum(map(len,rows))==1408
hist={str(i):dict(collections.Counter(s[i] for s in rows if len(s)>i)) for i in range(13)}
assert hist['1']=={'0':136}
assert hist['7']=={'0':74,'1':2}
by_position={k:sorted({v[i] for v in course}) for i,k in enumerate(('r','a','b','c','d'))}
assert by_position['a']==list(range(6))+list(range(16,20))
assert not set(range(6,15)).intersection(set.union(*(set(t[1:]) for t in course)))
new_first=[v for v in cases if v['split']=='test_new_first']
first_word_bit8_positive=sum(word(v['a'])[1]=='1' for v in new_first)
assert first_word_bit8_positive==20
seen_baseline=[v for v in cases if v['split']=='seen_baseline']
exact_seen_members=sum((v['r'],v['a'],v['b'],v['c'],v['d']) in course for v in seen_baseline)
bit_weights=(16,8,4,2,1)
def bit_counts(vals):
 return {str(w):{'zero':sum(not(v&w) for v in vals),'one':sum(bool(v&w) for v in vals)} for w in bit_weights}
role_counts={}
for r_filter in ('all',1,2):
 subset=[t for t in course if r_filter=='all' or t[0]==r_filter]
 role_counts[str(r_filter)]={
  role:bit_counts([t[i] for t in subset]) for i,role in enumerate(('r','a','b','c','d')) if i>0
 }
answer_role_counts={
 'first':bit_counts([t[1] for t in course]),
 'second':bit_counts([t[2] for t in course if t[0]==2]),
}
pair_coverage={}
for role,vals in [('first',[t[1] for t in course]),('second',[t[2] for t in course if t[0]==2])]:
 pair_coverage[role]={}
 for w1,w2 in itertools.combinations(bit_weights,2):
  count=collections.Counter(f'{int(bool(v&w1))}{int(bool(v&w2))}' for v in vals)
  pair_coverage[role][f'{w1},{w2}']={key:count[key] for key in ('00','01','10','11')}
assert pair_coverage['first']['4,2']['11']==0
assert pair_coverage['second']['4,2']['11']>0
manifest=[{**v,'Q':question(v['r'],v['a'],v['b'],v['c'],v['d']),'expected':answer(v['r'],v['a'],v['b'])} for v in cases]
manifest_bytes=(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in manifest)).encode()
manifest_hash=hashlib.sha256(manifest_bytes).hexdigest()
assert manifest_hash=='97749bd4c921a5eff34668e8a39776bc3704a4fb49a50f2456600915f1c68b74'

parent_formats=[]
for indent in (None,2,4):
 for separators in (None,(',',':')):
  for newline in ('','\n'):
   b=(json.dumps(parent,indent=indent,separators=separators)+newline).encode()
   if hashlib.sha256(b).hexdigest()=='e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a':
    parent_formats.append({'indent':indent,'separators':separators,'newline':newline})
assert parent_formats

result={
 'audit':'PR55 public source and deterministic teaching/eval corpus; no checkpoint replay',
 'source_head':SHA,'source_file_sha256':hashes,
 'optimizer_updates':0,'neural_forward_calls':0,
 'initial_review_history':[
  {'status':'reviewer_assertion_corrected',
   'detail':'The initial static audit expected 20 second-role bit8 positive presentations. Its assertion failed before neural work; reconstruction showed 2, and the audit assertion was corrected. This was a reviewer-script error, not an upstream experiment bug.',
   'neural_forward_calls':0,'optimizer_updates':0}
 ],
 'course_presentations':len(course),'course_distinct_Q':len(set(course)),
 'teacher_targets_per_epoch':sum(map(len,rows)),
 'output_target_histogram_by_zero_based_position':hist,
 'teaching_values_by_position':by_position,
 'first_answer_bit8_training_positive_count':0,
 'first_answer_bit8_training_total':hist['1']['0'],
 'second_answer_bit8_training_positive_count':hist['7']['1'],
 'second_answer_bit8_training_total':sum(hist['7'].values()),
 'primary_new_first_rows':len(new_first),
 'primary_new_first_bit8_positive_rows':first_word_bit8_positive,
 'manifest_rows':len(manifest),'manifest_sha256':manifest_hash,
 'parent_reconstruction_matches_frozen_sha':bool(parent_formats),
 'seen_baseline_rows':len(seen_baseline),
 'seen_baseline_exact_training_Q_count':exact_seen_members,
 'teaching_input_bit_counts_by_r_and_role':role_counts,
 'teaching_output_bit_counts_by_role':answer_role_counts,
 'teaching_output_bit_pair_coverage_by_role':pair_coverage,
 'b15_input_presentations':sum(t[2]==15 for t in course),
 'b15_answer_presentations':sum(t[2]==15 and t[0]==2 for t in course),
 'tied_parameters':12*16+16+105*94+94+94*3+3,
 'untied_parameters':4*(12*16+16)+105*94+94+94*3+3,
 'forward_dense_MAC':4*12*16+105*94+94*3,
 'interpretation':[
  'First-slot bit8 receives only zero labels: encoder sharing cannot by itself supply positive first-slot labels. This is a legitimate zero-shot role-transfer test, but failure does not isolate encoder weakness.',
  'Twenty of 28 primary new-first examples require a positive bit8 at first-output index1. The other eight examples (a6,7) fail too in the prior reported result, so absent bit8 positives alone cannot explain all 0/28 outcomes.',
  'All eight primary cases a6,7 require a first-word (bit4,bit2)=(1,1) conjunction absent in first-role training, though it appears in second-role training. Primary OOV therefore combines unobserved first-slot bit values and unobserved within-word combinations.',
  'WordStudent receives deterministic word slices, r header, and a position onehot; it discards generated prefix contents and constant framing. It does not learn word boundaries or r syntax from unrestricted raw bits.',
  'The tied/untied within-study contrast has equal initial function by construction and equal forward MAC, but not equal parameters; historical raw-MLP comparisons also differ in frontend, initialization/continuation, epochs and budget.',
  'Public Git has enough source to reconstruct corpus manifest exactly, but lacks final weights/raw/results JSON/prereg; prior 936/936 replay remains prior reported evidence until companion archive recovered.'
 ]
}
assert result['tied_parameters']==10457 and result['untied_parameters']==11081 and result['forward_dense_MAC']==10920
assert hashes=={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in source_paths.items()}
with OUTPUT.open('x',encoding='utf-8') as f:
 f.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
