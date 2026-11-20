# Extending a frozen serial adder to track ordered subtraction borrows

Use the existing 19-unit unsigned 8-bit serial adder and its carry and exactly-two readouts. Keep its original weights fixed. Predict each successive borrow of ordered subtraction a minus b. This is a component study on the internal scratch board. No language-encoding comparison or full subtraction output is under test.

Before the new borrow experiment, record these conditions:

1. Group all 65,536 ordered inputs by their original first-round hidden vector and count the majority label in each group. This is an upper bound for any deterministic first-round head restricted to the old hidden state. We predict a collision for (1,0) and (0,1).
2. Add one threshold unit and one feedback bit. Manually specify ports for operand A bit zero, operand B bit zero and previous predicted borrow. Test both a handfilled rule and a four-parameter integer perceptron taught the eight local binary input cases. Use 16 seeds 20261120 through 20261135, a maximum of 128 shuffled epochs, and record all outcomes.
3. Roll out all eight rounds on every ordered byte pair using the network's own previous output. Score against independent masked prefix comparisons, old integer sum modulo 256, completion and the two frozen readouts. Disable the borrow feedback in a control.
4. Distinguish training the local decision from discovering its wiring. Report new capacity and recurrent scratch separately, and archive failed outcomes. Compare the entire borrow sequence, not just the final less-than bit.

A separate, post-hoc audit checks a bounded tape VM's copy example against an independent slice oracle on the author's published input generator. Its outcomes are not preregistered.