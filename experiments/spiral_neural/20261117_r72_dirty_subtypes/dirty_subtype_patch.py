"""R72 public, source-independent patch algorithm from frozen comparison.
Full exact runner, Fable compiler, weights, checkpoints and raw bits are in the authorized private ZIP.
This file does not implement standalone student training.
"""
import numpy as np

DIRTY_ROWS=(60,61)
DIRTY_BOARD=slice(44,84)  # Fable151 fixed n=1 q=32, q+12:q+52

def patch_dirty_rows(hand, original_x, original_y, original_mask, zero_based_step, dedicated_rng):
    """Change only dirty board subtype on odd minibatches, preserving all other raw bits.

    hand.draft and hand.build must come from the SHA-locked original hand.py
    166ef00fce69386f89a1f832785a77e2fb465b3831c5d78854ac85083deceed8.
    Original minibatches must first be generated unmodified by the R71 runner,
    keeping its RNG stream unchanged. dedicated_rng must be seeded at 772000+seed.
    """
    x=original_x.copy()
    if zero_based_step%2:
        for i,index in enumerate(DIRTY_ROWS):
            original=x[index].copy()
            value=int(''.join(str(int(b)) for b in original[24:31]),2)
            newboard=np.array(hand.draft(value,2+i,dedicated_rng),float)
            candidate, gold, mask=hand.build(0,np.array([[value]]),newboard.reshape(1,40))
            assert np.array_equal(original_y[index],gold[0])
            assert np.array_equal(original_mask[index],mask[0])
            assert np.array_equal(original[:44],candidate[0,:44])
            assert np.array_equal(original[84:],candidate[0,84:])
            x[index]=candidate[0]
    keep=np.ones(len(x),bool);keep[list(DIRTY_ROWS)]=False
    assert np.array_equal(x[keep],original_x[keep])
    if zero_based_step%2==0:assert np.array_equal(x,original_x)
    return x,original_y.copy(),original_mask.copy()
