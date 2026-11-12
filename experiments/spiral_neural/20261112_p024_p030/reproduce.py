"""Explicit offline validation or full research rerun; never overwrite evidence."""
import sys
sys.dont_write_bytecode=True
import argparse,os,subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
EXPERIMENTS={'P024':'echo_serial_stop.py','P025-RNN':'echo_prefix_separator.py','P025-MLP':'echo_prefix_direct.py',
             'P026':'echo_bit_feedback.py','P027':'echo_teaching_comparison.py','P028':'echo_learning_time.py',
             'P029':'echo_monotonic_curriculum.py','P030':'p030_binary_continual.py'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['validate','run'])
    p.add_argument('--experiment',choices=EXPERIMENTS)
    p.add_argument('--work',type=Path,help='Required for training: separate output root, outside archived evidence/src.')
    args=p.parse_args()
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONIOENCODING']='utf-8'
    if args.action=='validate':
        return subprocess.call([sys.executable,'-B',str(HERE/'validate_archive.py')],env=env)
    if not args.experiment or args.work is None:p.error('run requires --experiment and --work')
    work=args.work.resolve()
    if work==HERE or work.is_relative_to(HERE):p.error('Training output must be outside this immutable archive')
    work.mkdir(parents=True,exist_ok=True);env['SLE_RESEARCH_WORK']=str(work)
    return subprocess.call([sys.executable,'-B',str(HERE/'src'/EXPERIMENTS[args.experiment])],env=env)

if __name__=='__main__':raise SystemExit(main())
