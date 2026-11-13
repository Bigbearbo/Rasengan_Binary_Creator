"""Four controller-only checks: no synthetic or trained neural updates/forwards."""
import copy
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import numpy as np
import run_continue as r
CONTENTS = DATA = None
MOCK_EPOCHS = 0
def scores(full=True, e3=True):
    return {n:dict(questions=900,whole_correct=900 if (full or (n=="E3" and e3)) else 899) for n in r.protocol()["classes"]}
class Engineering(unittest.TestCase):
    def test_stop_reset_cap_baseline_not_streak(self):
        streak=0
        for epoch,(full,expected) in enumerate(((True,1),(False,0),(True,1),(True,2)),1):
            streak,_,reason=r.stop_update(streak,scores(full,e3=False),epoch,8)
            self.assertEqual(streak,expected)
        self.assertEqual(reason,"two_consecutive_new_epoch_all_class_passes")
        self.assertEqual(r.stop_update(0,scores(True),1,8),(1,True,None))
        self.assertEqual(r.stop_update(0,scores(True),8,8),(1,True,"epoch_cap"))
        self.assertEqual(r.stop_update(1,scores(False,e3=False),8,8),(0,False,"epoch_cap"))
    def test_first_order_then_exact_next_eight(self):
        cfg,v,_,_,rows=DATA[:5]
        for seed in cfg["seeds"]:
            first=np.load(io.BytesIO(CONTENTS[f"first-orders/seed{seed}.npy"]),allow_pickle=False)
            actual=r.courses(v,rows,first,seed,8)
            rng=np.random.default_rng(seed+666000); pool=v.target_pool(rows,cfg["classes"])
            self.assertTrue(np.array_equal(first,pool[rng.permutation(len(pool))]))
            for order in actual:
                self.assertTrue(np.array_equal(order,pool[rng.permutation(len(pool))]))
            self.assertEqual(actual.shape,(8,53100,2)); self.assertEqual(actual.dtype.str,"<u2")
            wrong=first.copy(); wrong[[0,1]]=wrong[[1,0]]
            with self.assertRaisesRegex(AssertionError,"first permutation"):
                r.courses(v,rows,wrong,seed,8)
    def test_mock_epoch_carry_first_full_reset_and_cost(self):
        global MOCK_EPOCHS
        cfg=copy.deepcopy(DATA[0]); h=DATA[2]; parent={k:v.copy() for k,v in DATA[5]["101"].items()}
        rows=[dict(question_id=i,**{"class":n},A="000000" if n!="E3" else "000000"*3) for i,n in enumerate(cfg["classes"])]
        free=dict(rows=[dict(question_id=row["question_id"],tokens=row["A"]+"S") for row in rows])
        cases=[scores(False,True),scores(True),scores(False,True),scores(True),scores(True)]
        calls=[]
        def fake_train(hh,cls,original,shared,order,part,folder,seed,arm):
            global MOCK_EPOCHS
            epoch=len(calls)+1; calls.append(int(shared["t"])); folder.mkdir()
            self.assertEqual(cfg["end_t"][str(seed)],int(parent["t"])+epoch*53100)
            saved={k:v.copy() for k,v in shared.items()}; saved["t"]=np.array(int(saved["t"])+53100)
            saved["meta_train_macs"]=np.array(int(saved["meta_train_macs"])+1118073600)
            saved["meta_inference_calls"]=np.array(int(saved["meta_inference_calls"])+17)
            saved["meta_inference_macs"]=np.array(int(saved["meta_inference_macs"])+17*10432)
            with (folder/"final-state.npz").open("xb") as stream: stream.write(h.npz_bytes(saved))
            r.write(folder/"generation.json",free); MOCK_EPOCHS+=1
            return dict(scores=cases[epoch-1]),dict(seed=seed,arm=arm,seconds_training_and_freeprobe=0.)
        fake=types.SimpleNamespace(train_arm=fake_train,churn_metrics=DATA[1].churn_metrics,canonical=DATA[1].canonical)
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory); r.write(folder/"baseline-generation.json",free)
            with patch("sys.stdout",new=io.StringIO()):
                summary,_=r.run_epochs(cfg,fake,h,None,parent,parent,[None]*8,rows,folder,101)
            self.assertEqual(summary["epochs"],5); self.assertEqual(summary["first_E3_full_epoch"],1)
            self.assertEqual(summary["first_all_five_full_epoch"],2); self.assertEqual(summary["stable_pass_epoch"],5)
            self.assertEqual(calls,[int(parent["t"])+e*53100 for e in range(5)])
            final=h.read_npz((folder/"final-state.npz").read_bytes())
            self.assertEqual(int(final["meta_inference_calls"]),int(parent["meta_inference_calls"])+5*17)
            self.assertEqual(summary["new_updates"],5*53100); self.assertEqual(summary["new_training_dense_MAC"],5*1118073600)
            for key in parent:
                if key not in ("t","meta_train_macs","meta_inference_calls","meta_inference_macs"):
                    self.assertTrue(np.array_equal(parent[key],final[key]))
    def test_baseline_nonperfect_exact_allowed_and_abort_blocks_training(self):
        cfg,v,h,cls,rows,parents=DATA[:6]
        def fake_probe(hh,net,part,names):
            result=json.loads(CONTENTS[f"historical/seed{net.seed}.json"])
            net.inference_calls+=result["inference_calls"]; net.inference_macs+=result["inference_dense_MAC"]
            return result
        with tempfile.TemporaryDirectory() as directory, patch.object(v,"probe",side_effect=fake_probe), \
             patch.object(cls,"forward",side_effect=AssertionError("NN forbidden")),patch.object(cls,"step",side_effect=AssertionError("optimizer forbidden")):
            states,records=r.all_baselines(v,h,cls,parents,CONTENTS,rows,Path(directory),cfg["seeds"])
            self.assertTrue(all(record["archived_generation_exact"] for record in records.values()))
            self.assertTrue(all(record["baseline_streak"]==0 for record in records.values()))
            self.assertTrue(all(v.learning_unchanged(h,parents[k],states[k]) for k in states))
            self.assertTrue(any(records["101"]["scores"][n]["whole_correct"]<900 for n in cfg["classes"]))
        with tempfile.TemporaryDirectory() as directory,patch.object(r,"validate_inputs",return_value=({},{},DATA)), \
             patch.object(r,"all_baselines",side_effect=AssertionError("synthetic exact mismatch")),patch.object(r,"run_epochs") as train:
            with self.assertRaisesRegex(AssertionError,"exact mismatch"):
                r.execute(None,"a"*64,"b"*40,Path(directory)/"attempt")
            train.assert_not_called()
            self.assertTrue(r.read(Path(directory)/"attempt/failure.json")["zero_new_updates_guaranteed"])
def run_checks(parent_root):
    global CONTENTS,DATA
    CONTENTS=r.collect_public(parent_root); DATA=r.inspect(CONTENTS,False)
    stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Engineering))
    return dict(status="passed" if result.wasSuccessful() else "failed",tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                test_output=stream.getvalue(),mock_epochs=MOCK_EPOCHS,mock_target_updates_not_optimizer=MOCK_EPOCHS*53100,
                synthetic_optimizer_updates=0,synthetic_forward_calls=0,trained_forward_calls=0,trained_optimizer_calls=0,external_model_calls=0)
