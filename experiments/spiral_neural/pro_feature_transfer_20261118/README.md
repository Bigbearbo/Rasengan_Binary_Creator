# Mature feature reuse for a small new MAX head

Status: preregistered design; no new training result at this commit.

The preceding PR131 study added branches that read raw inputs and combined final outputs. It did not test a new branch reading the mature network's hidden computations. This follow-up isolates that missing connection.

Three fixed feature banks feed the same 24-to-8-to-7 trainable head: a trained PR130 receiver's actual hidden activations, an untrained random receiver-shaped bank, and an information-preserving linear projection of the raw frame. Three paired seeds, 4,096 updates each, identical head initializations and minibatch streams. All nine runs finish before test features or predictions are calculated.

The new task is a fixed MAX readout. Existing ADD/XOR/AND/OR codes are nuisance variation; their meanings are not redefined. The experiment caller selects this head. This is not a learned new MAX opcode, a learned task router, or a complete SLE answer pipeline.

Fresh splits group unordered operand pairs, including both orders and every opcode. Neither orientation occurs in the source model's training, validation or test pairs. The bounded source domain still restricts a+b<128. Train/validation/test contain 8,240/2,096/3,120 frames, corresponding to 1,036/268/396 independent unordered pairs.

Each head has 263 trainable parameters. The 840-value feature bank and 25-value normalization are counted separately. The mature configuration also retains its original 450-parameter decoder, so total stored systems are not equal in size. Previous source training is inherited cost, not free computation.

The original research direction permits temporary regression and recovery during growth. Freezing the source here is a causal control for representation transfer; it does not replace that broader question with permanent freezing or a no-dip requirement.

See `protocol.json`, `source_manifest.json` and `projection_receipt.json` for the fixed experiment. Sources: [PR130](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/130), [PR131](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/131). This isolated branch does not change the primary queue, any prior checkpoint, or the Hamster VM.

Related primary work: [Progressive Neural Networks](https://arxiv.org/abs/1606.04671) studies transfer through lateral connections; [How transferable are features in deep neural networks?](https://arxiv.org/abs/1411.1792) distinguishes learned feature transfer from task specialization and co-adaptation. These motivate controls; they do not determine this experiment's result.

NVIDIA review: unavailable in this environment, actual calls 0. Independent local design/code review is used. No external worker execution is claimed.
