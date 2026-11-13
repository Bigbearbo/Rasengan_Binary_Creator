"""Standalone stdlib preflight for SLE-AE1 equal-distinct role study.
Read the companion ZIP's parent_course.json and cases.jsonl; no Torch needed.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

P = Path(__file__).resolve().parent
H = range(16, 20)
LOW = range(4)
B = (18, 19, 22, 23)
ARMS = ('first_high', 'second_high')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def word(v):
    assert isinstance(v, int) and 0 <= v <= 29
    return f'{v:05b}0'


def qbits(r, a, b, c, d):
    assert r in (1, 2)
    return '01' + '010' + f'{r:03b}0' + ''.join(map(word, (a,b,c,d))) + '111100'


def abits(r, a, b):
    return word(a) + (word(b) if r == 2 else '') + 'S'


def inject(arm):
    return [(2,h,low,0,1) if arm == 'first_high' else (2,low,h,0,1)
            for low in LOW for h in H]


def eval_cases(arm):
    cases = []
    def add(split, r, a, b, c, d):
        cases.append({'split':split,'r':r,'a':a,'b':b,'c':c,'d':d,
                      'Q':qbits(r,a,b,c,d),'expected':abits(r,a,b)})
    for r in (1,2):
        for a in range(6):
            for b in B: add('known_baseline',r,a,b,0,0)
    for r,a,b,c,d in inject(arm): add('exact_injection',r,a,b,c,d)
    for name,vals,d in [('val_first_role',range(20,24),1),
                        ('test_unseen_value',range(24,30),1),
                        ('test_context_d0',range(24,30),0)]:
        for a in vals:
            for b in B: add(name,2,a,b,0,d)
    return cases


def main():
    frozen = json.loads((P/'prereg.json').read_text())
    expected = {
        'parent_course.json':frozen['parent_course_sha256'],
        'run.py':frozen['runner_sha256'],
        'cases.jsonl':frozen['case_manifest_sha256'],
    }
    for name,digest in expected.items():
        assert sha(P/name)==digest,(name,sha(P/name),digest)
    parent = [tuple(x) for x in json.loads((P/'parent_course.json').read_text())]
    assert len(parent)==120 and len(set(parent))==96
    assert all(x[4] == 0 for x in parent)
    courses = [parent + inject(arm) for arm in ARMS]
    for course in courses:
        assert len(course)==136 and len(set(course))==112
        assert all(t[0] in (1,2) and all(0<=v<=29 for v in t[1:]) for t in course)
    def label_hist(course):
        return Counter(''.join(abits(r,a,b) for r,a,b,_,_ in course))
    assert label_hist(courses[0]) == label_hist(courses[1])
    assert sum(len(abits(r,a,b)) for r,a,b,_,_ in courses[0])==1408
    manifest = [json.loads(x) for x in (P/'cases.jsonl').read_text().splitlines()]
    correct = [v for arm in ARMS for v in eval_cases(arm)]
    assert manifest == correct and len(manifest) == 256
    for arm in ARMS:
        cases = eval_cases(arm)
        assert len(cases)==len({c['Q'] for c in cases})==128
        assert set(c['a'] for c in cases if c['split']=='test_unseen_value')==set(range(24,30))
    for arm in ARMS:
        for sample in parent + inject(arm):
            assert not ({24,25,26,27,28,29} & set(sample[1:]))
    print('PASS: frozen hashes, 136/112 distinct in each arm, label histogram, 256 native Q39 and student-heldout values')


if __name__=='__main__':main()
