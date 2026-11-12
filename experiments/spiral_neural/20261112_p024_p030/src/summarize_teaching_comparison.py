"""Read only completed P027 evidence; produce compact resource/metric tables."""
from _archive_paths import ARCHIVE_ROOT, REPO_ROOT, SRC_DIR, RUNS_ROOT, PLOTS_ROOT
import json
from pathlib import Path

ROOT=RUNS_ROOT/'echo-teaching-comparison-20261112'

def main():
    source=json.loads((ROOT/'compact.json').read_text(encoding='utf-8'))
    assert len(source['runs'])==9
    table=[];episodes=updates=0
    for r in source['runs']:
        trace=json.loads((ROOT/f"{r['arm']}-{r['seed']}"/'trace.json').read_text())
        assert len(trace)==r['question_presentations']==20000
        costs=[10 if r['arm']=='ce_shuffle' else len(row[2]) for row in trace]
        assert sum(costs)==r['token_updates']
        cumulative=0
        for i,cost in enumerate(costs):
            if cumulative+cost>=100000:break
            cumulative+=cost
        anchor={'updates':100000,'question_presentations_including_partial':i+1,
                'tokens_of_last_question_used':100000-cumulative,
                'unique_presented':len({row[0] for row in trace[:i+1]})}
        held=r['probes']['heldout'];equal=r['at_equal_100000_updates']['heldout']
        table.append({'arm':r['arm'],'seed':r['seed'],'presentations':len(trace),
                      'updates':r['token_updates'],'training_seconds':r['training_seconds'],
                      'unique_presented':r['unique_presented'],
                      'train_whole':r['probes']['train']['whole_correct'],
                      'heldout_whole':held['whole_correct'],'heldout_total':held['total'],
                      'heldout_bit_accuracy':held['bit_accuracy'],
                      'heldout_bit_correct_by_position':held['bit_correct_by_position'],
                      'heldout_stop_at_correct_position':held['stop_at_correct_position'],
                      'equal_update_anchor':anchor,'equal_update_heldout_whole':equal['whole_correct'],
                      'full_replay':r['all_trajectory_optimizer_and_anchor_replay_equal']})
        episodes+=len(trace);updates+=r['token_updates']
    compact={'total_presentations':episodes,'total_updates':updates,'replay_updates':updates,'table':table}
    (ROOT/'summary-table.json').write_text(json.dumps(compact,indent=2))
    print(json.dumps(compact))

if __name__=='__main__':main()
