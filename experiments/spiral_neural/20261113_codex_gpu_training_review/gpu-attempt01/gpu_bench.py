"""Bounded synthetic batch1 CuPy eager/graph pilot; never loads study checkpoints."""
import os
from pathlib import Path
import sys
import time
import json
import hashlib
import statistics
import traceback

WORK = Path('D:/Codex用/work/gpu-training-review-20261113')
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['CUPY_CACHE_DIR'] = str(WORK/'cupy-cache')
sys.dont_write_bytecode = True
import numpy as np
import cupy as cp
import bench_common as common

LEDGER = {'reference_GPU_validation': 0, 'CuPy_eager_GPU': 0, 'CuPy_CUDA_Graph_GPU': 0}
CAPTURED_STEPS_NOT_EXECUTED = 0

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(value):
    path = WORK/'gpu-results.json'
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

class GPU:
    def __init__(self, fixture, state, backend):
        self.backend = backend
        self.stream = cp.cuda.Stream(non_blocking=True)
        started = time.perf_counter()
        with self.stream:
            self.X = cp.asarray(fixture['X'])
            self.Y = cp.asarray(np.eye(3, dtype=np.float64)[fixture['labels']])
            self.p = [cp.asarray(state[f'p{i}']) for i in range(4)]
            self.m = [cp.asarray(state[f'm{i}']) for i in range(4)]
            self.v = [cp.asarray(state[f'v{i}']) for i in range(4)]
            self.birth = [cp.asarray(state[f'birth{i}']) for i in range(4)]
            self.t = cp.asarray(state['t'])
            self.index = cp.asarray(np.array(0, np.int64))
        self.stream.synchronize()
        self.transfer_allocation_seconds = time.perf_counter()-started
        self.graph = None
        self.chunk = 1
        self.fixed = {k: state[k].copy() for k in ('L','H')}

    def restore(self, state):
        with self.stream:
            for label in ('p','m','v','birth'):
                for i in range(4): getattr(self,label)[i].set(state[f'{label}{i}'],stream=self.stream)
            self.t.set(state['t'],stream=self.stream)
            self.index.fill(0)
        self.stream.synchronize()

    def step(self):
        # Device index advances on each graph replay; host Python is never the counter.
        x = cp.take(self.X, self.index, axis=0, mode='wrap').reshape(1,160)
        y = cp.take(self.Y, self.index, axis=0, mode='wrap')
        h = cp.tanh(x @ self.p[0] + self.p[1])
        z = (h @ self.p[2] + self.p[3])[0]
        zz = z.astype(cp.float64)
        lse = cp.logaddexp(cp.logaddexp(zz[0],zz[1]),zz[2])
        lp = zz-lse
        d = (cp.exp(lp)-y).astype(cp.float32)[None,:]
        dz = (d @ self.p[2].T)*(1-h*h)
        grads = [x.T @ dz,dz[0],h.T @ d,d[0]]
        parts = [(g*g).sum().astype(cp.float64) for g in grads]
        total = parts[0]
        for part in parts[1:]: total = total+part
        norm = cp.sqrt(total)
        scale = cp.minimum(np.float64(1),np.float64(1)/cp.maximum(norm,np.float64(1e-12))).astype(cp.float32)
        self.t += np.int64(1)
        for i,g in enumerate(grads):
            g *= scale
            # In-place state addresses are essential for multi-launch graph continuation.
            self.m[i][...] = .9*self.m[i]+.1*g
            self.v[i][...] = .999*self.v[i]+.001*g*g
            age = self.t-self.birth[i]
            b1 = 1-cp.power(np.float64(.9),age)
            b2 = 1-cp.power(np.float64(.999),age)
            self.p[i] -= .003*(self.m[i]/b1)/(cp.sqrt(self.v[i]/b2)+1e-8)
        self.index += np.int64(1)
        self.last_z,self.last_loss = z,-(lp*y).sum()

    def snapshot(self):
        self.stream.synchronize()
        result = {f'{label}{i}':cp.asnumpy(a) for label in ('p','m','v','birth') for i,a in enumerate(getattr(self,label))}
        result.update(t=cp.asnumpy(self.t),**self.fixed)
        return result

    def warm_and_graph(self,state,chunk):
        global CAPTURED_STEPS_NOT_EXECUTED
        started = time.perf_counter()
        with self.stream: self.step()
        self.stream.synchronize()
        LEDGER[self.backend] += 1
        assert int(cp.asnumpy(self.t)) == int(state['t'])+1
        self.restore(state)
        self.chunk = chunk
        if chunk > 1:
            with self.stream:
                self.stream.begin_capture()
                for _ in range(chunk): self.step()
                self.graph = self.stream.end_capture()
            self.stream.synchronize()
            assert int(cp.asnumpy(self.t)) == int(state['t']), 'capture unexpectedly executed updates'
            CAPTURED_STEPS_NOT_EXECUTED += chunk
        return time.perf_counter()-started

    def run(self,steps):
        assert steps % self.chunk == 0
        if self.graph is not None:
            for _ in range(steps//self.chunk): self.graph.launch(stream=self.stream)
        else:
            with self.stream:
                for _ in range(steps): self.step()

def validate(fixture,backend,references):
    cases = []
    for case in common.CASES:
        state = common.initial_state(case,fixture)
        obj = GPU(fixture,state,backend)
        chunk = 16 if backend=='CuPy_CUDA_Graph_GPU' else 1
        warm = obj.warm_and_graph(state,chunk)
        logits,losses,preds,indices = [],[],[],[]
        for done in range(chunk,65,chunk):
            obj.run(chunk)
            obj.stream.synchronize()
            LEDGER[backend] += chunk
            z,loss = cp.asnumpy(obj.last_z),cp.asnumpy(obj.last_loss)
            logits.append(z);losses.append(loss);preds.append(int(z.argmax()));indices.append(done-1)
            assert int(cp.asnumpy(obj.t)) == int(state['t'])+done
            assert int(cp.asnumpy(obj.index)) == done
        final,trace = references[case]
        actual_trace = {'logits':np.asarray(logits,np.float32),'losses':np.asarray(losses,np.float64),'predictions':np.asarray(preds,np.int64)}
        expected_trace = {k:v[np.asarray(indices)] for k,v in trace.items()}
        final_check = common.measure_error(obj.snapshot(),final)
        trace_check = common.measure_error(actual_trace,expected_trace)
        cases.append({'case':case,'steps':64,'observed_trace_positions0':indices,'state':final_check,'trace':trace_check,'warm_compile_capture_seconds':warm,'passed':final_check['passed'] and trace_check['passed']})
        if not cases[-1]['passed']: return cases
    return cases

def benchmark(fixture,backend):
    trials=[]
    for trial in range(3):
        state=common.initial_state('timing',fixture)
        obj=GPU(fixture,state,backend)
        setup=obj.warm_and_graph(state,16 if backend=='CuPy_CUDA_Graph_GPU' else 1)
        begin,end=cp.cuda.Event(),cp.cuda.Event()
        begin.record(obj.stream)
        started=time.perf_counter()
        obj.run(1024)
        end.record(obj.stream);end.synchronize()
        wall=time.perf_counter()-started
        LEDGER[backend]+=1024
        assert int(cp.asnumpy(obj.t))==int(state['t'])+1024
        assert int(cp.asnumpy(obj.index))==1024
        trials.append({'trial':trial,'updates':1024,'synchronized_wall_seconds':wall,'GPU_event_seconds':cp.cuda.get_elapsed_time(begin,end)/1000,'transfer_allocation_seconds':obj.transfer_allocation_seconds,'warm_compile_capture_seconds':setup,'final_t':int(cp.asnumpy(obj.t))})
    return {'trials':trials,'median_seconds':statistics.median(t['synchronized_wall_seconds'] for t in trials),'median_updates_per_second':1024/statistics.median(t['synchronized_wall_seconds'] for t in trials)}

def main():
    out=WORK/'gpu-results.json'
    assert not out.exists(),'One-shot pilot result already exists; preserve attempts'
    fixture=common.load_fixture()
    before=sha(WORK/'fixture.npz')
    started=time.perf_counter()
    p=cp.cuda.runtime.getDeviceProperties(0)
    result={'schema':'GPU-batch1-engineering-pilot-v1','status':'running','hardware':{'name':p['name'].decode(),'compute_capability':[p['major'],p['minor']],'VRAM_bytes':p['totalGlobalMem']},'software':{'cupy':cp.__version__,'numpy':np.__version__,'CUDA_driver_API':cp.cuda.runtime.driverGetVersion(),'CUDA_runtime_API':cp.cuda.runtime.runtimeGetVersion()},'plan_sha256':sha(Path(__file__).with_name('plan.json')),'script_sha256':sha(__file__),'fixture_sha256':before,'timing_scope':'preencoded batch1 forward/backward/global-clip/Adam, no gradient averaging; device loss/logit values available, no per-step host logging/hash. Events and synchronized wall include host enqueue gaps. Compile/context/transfer/validation separate. Not full-study speedup or bitwise training replay.','backends':{},'formal_training_updates':0}
    refs={}
    for case in common.CASES:
        refs[case]=common.reference_trace(fixture,case,64)
        LEDGER['reference_GPU_validation']+=64
    for backend in ('CuPy_eager_GPU','CuPy_CUDA_Graph_GPU'):
        try:
            cases=validate(fixture,backend,refs)
            accepted=len(cases)==2 and all(c['passed'] for c in cases)
            record={'validation':cases,'accepted_engineering_parity':accepted}
            if accepted: record['benchmark']=benchmark(fixture,backend)
            result['backends'][backend]=record
        except Exception as error:
            result['backends'][backend]={'accepted_engineering_parity':False,'error_type':type(error).__name__,'error':str(error)}
            (WORK/(backend+'-failure.log')).write_text(traceback.format_exc(),encoding='utf-8')
        result['actual_synthetic_updates']=LEDGER.copy()
        result['captured_steps_not_executed']=CAPTURED_STEPS_NOT_EXECUTED
        save(result)
    assert sha(WORK/'fixture.npz')==before
    assert max(LEDGER.values())<=7000
    result.update(status='complete',actual_synthetic_updates=LEDGER.copy(),captured_steps_not_executed=CAPTURED_STEPS_NOT_EXECUTED,fixture_unchanged=True,total_seconds=time.perf_counter()-started)
    save(result)
    print(json.dumps({'status':'complete','backends':{k:{'parity':v['accepted_engineering_parity'],'median_seconds':v.get('benchmark',{}).get('median_seconds'),'error_type':v.get('error_type')} for k,v in result['backends'].items()},'actual_synthetic_updates':LEDGER,'formal_updates':0}))

if __name__=='__main__': main()
