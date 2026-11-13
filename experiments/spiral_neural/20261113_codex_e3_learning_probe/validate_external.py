import json
from pathlib import Path

root = Path(__file__).resolve().parent
raw = (root.parents[1] / 'work/agent-team/attempts/nvidia/E3-LR-METHOD-001/candidate.json').read_bytes()
candidate = json.loads(raw)
claim = json.loads(candidate['findings'][0]['claim'])
expected = {
    'total_updates': 3 * 2 * (900 * (7 + 13 + 7 + 13 + 19)),
    'total_training_dense_MAC': 3 * 2 * 53100 * 21056,
    'E3_fixture_output': ''.join(format(v, '05b') + '0' for v in [1, 6, 23]) + 'S',
    'rate_superiority_established_by_feasibility_gate': False,
}
checks = {key: type(claim.get(key)) is type(value) and claim[key] == value for key, value in expected.items()}
result = {'schema': 'e3-external-field-checks-v1', 'task_id': 'E3-LR-METHOD-001',
          'expected': expected, 'observed': {key: claim.get(key) for key in expected}, 'checks': checks,
          'semantic_status': 'candidate_rejected' if not all(checks.values()) else 'verified_fields_only',
          'reason': 'Wrong update and total MAC arithmetic. Encoding and feasibility distinction verified independently; no model research claim imported.',
          'research_claims_adopted': 0, 'NN_calls': 0, 'optimizer_calls': 0, 'retries': 0}
with (root / 'external-method-checks.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
with (root / 'external-candidate.json').open('xb') as stream:
    stream.write(raw)
print(json.dumps(result))
