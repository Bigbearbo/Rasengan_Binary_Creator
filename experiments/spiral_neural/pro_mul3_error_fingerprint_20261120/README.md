# Can seven-bit multiplication mistakes be identified from final answers?

This static experiment enumerates all 128 unsigned seven-bit inputs for multiplication by three. It compares seven concrete output functions. It has no model dependency. Python 3.8+ and the standard library are sufficient.

## Replay

From this directory, run:

```sh
python3 research.py --out reproduced
python3 score_answers.py --self-test
```

Compare the three files under `reproduced/` to the shipped counterparts in `results/`, byte for byte. `PROTOCOL.md` specifies the rules and panel selection. `results/census.csv` contains the 128 input rows. `results/pair_distances.csv` gives all 21 pairwise disagreements. `results/summary.json` records the panels and the one-error verification. The experimental output concerns decoded integers, not the SLE codec, submission policy, or a neural model's hidden states.

## Main result

Three distinct output rules have exactly the same correctness flags on all 128 inputs. XOR, OR, and a single parallel carry step each get the same 34 correct; on each of the other 94 inputs, all three return different numeric answers. For x=3, the correct answer is 9; double, XOR, OR, and a single carry return 6, 5, 7, and 1 respectively.

Let p=x XOR 2x and g=x AND 2x. The product is p+2g. XOR returns p, OR returns p+g, and the single carry rule returns p XOR 2g. If g=0 they all agree. If g>0, consider the highest set bit h of g: input bits h-1 and h equal 1, but bit h+1 is 0. Bit h+1 is thus set in both p and 2g. A second carry is needed there; the single carry rule also falls short. All of these disagreements are visible in the complete census.

The exact numeric answers to inputs 43 and 86 distinguish all seven fixed functions. No single example suffices. The true product and its eight-bit truncation differ only at x>=86; the seven- and eight-bit truncations differ only at x from 43 to 85. Six probes, inputs 43,44,45,86,87,88, give distance at least three between every pair of functions, tolerating one arbitrary erroneous answer if the source otherwise follows one fixed function. At least three probes from each of these disjoint intervals are required to correct one error. This is a finite candidate identification result; a model can switch strategy or implement an unlisted function. The proposals can be applied offline to stored answers or to a separately identified diagnostic run. They do not form an unbiased estimate of seven-bit accuracy and should not be added to the training set as new evidence.

## Using separately available answers

Run `python3 score_answers.py answers.csv`. The required header is `arm,x,status,answer`. Use `valid` only for submitted answers successfully decoded by the source codec. For `invalid` or `unsubmitted` leave the answer blank; omit genuinely unobserved rows. The program reports all matching rules, including ties and out-of-family answers. Among the rows with a valid answer, each rule pair is compared only on inputs where the two functions disagree. A matching output does not identify the model's internal computation.

The two training-arm aggregate excerpts in the protocol were known beforehand and are used only for a conditional correctness comparison. No individual student answers are embedded here. The figures in the static census derive from the seven specified formulae.
