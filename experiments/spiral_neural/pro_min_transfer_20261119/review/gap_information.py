"""Post-hoc information ceiling. No fitting, task labels, or data from the MIN study are changed."""
import json
from fractions import Fraction
from itertools import product

def summarize(pairs):
    # Matches the handfilled comparator's sign; equal pairs deliberately omitted upstream.
    cells = {(larger_left, near): 0 for larger_left in (False, True) for near in (False, True)}
    for a,b in pairs:
        cells[a > b, abs(a-b) <= 3] += 1
    n = sum(cells.values())
    positive = sum(cells[k,True] for k in (False, True))
    negative = n-positive
    policies = []
    for outputs in product((False, True), repeat=2):
        tp = sum(cells[s,True] for s in (False,True) if outputs[s])
        tn = sum(cells[s,False] for s in (False,True) if not outputs[s])
        balanced = (Fraction(tp,positive)+Fraction(tn,negative))/2
        policies.append({"output_if_left_smaller_then_if_left_larger":list(outputs),
                         "correct":tp+tn,"sensitivity":str(Fraction(tp,positive)),
                         "specificity":str(Fraction(tn,negative)),"balanced_accuracy":str(balanced)})
    assert all(cells[False,near] == cells[True,near] for near in (False, True))
    assert all(p["balanced_accuracy"]=="1/2" for p in policies)
    comparison_bit = lambda a,b: int(a>b)
    assert comparison_bit(8,9) == comparison_bit(8,15)
    return {"n_unequal":n,"near":positive,"not_near":negative,"each_possible_readout":policies,
            "best_raw_accuracy":max(p["correct"] for p in policies)/n,"best_balanced_accuracy":0.5}
if __name__=="__main__":
    both = [(a,b) for a in range(128) for b in range(128) if a!=b]
    print(json.dumps({"kind":"exploratory_static_ceiling_no_training","target":"1 <= abs(a-b) <= 3",
                      "reader_input":"single exact comparator bit only; no access to operands",
                      "all_unequal":summarize(both),
                      "legal_sum_below_128_unequal":summarize([(a,b) for a,b in both if a+b<128])},indent=2))
