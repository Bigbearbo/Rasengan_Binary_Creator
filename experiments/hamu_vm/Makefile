CXX ?= g++
CXXFLAGS ?= -std=c++17 -O2
all: build/hamu_experiment
build:
	mkdir -p build
build/hamu_experiment: src/hamu_experiment.cpp src/hamu_vm_core.hpp | build
	$(CXX) $(CXXFLAGS) src/hamu_experiment.cpp -o $@
build/test_vm: tests/test_vm.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_vm.cpp -o $@
test: build/test_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_vm
clean:
	rm -rf build
.PHONY: all test clean
build/test_mutation: tests/test_mutation.cpp src/hamu_experiment.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 tests/test_mutation.cpp -o $@
mutation-test: build/test_mutation
	./build/test_mutation
.PHONY: mutation-test
build/branch_experiment: src/branch_experiment.cpp src/hamu_vm_core.hpp | build
	$(CXX) $(CXXFLAGS) src/branch_experiment.cpp -o $@
branch-experiment: build/branch_experiment
	./build/branch_experiment
.PHONY: branch-experiment
build/growth_experiment: src/growth_experiment.cpp src/hamu_vm_core.hpp | build
	$(CXX) $(CXXFLAGS) src/growth_experiment.cpp -o $@
growth-experiment: build/growth_experiment
	./build/growth_experiment
.PHONY: growth-experiment
build/joint_growth_experiment: src/joint_growth_experiment.cpp src/hamu_vm_core.hpp | build
	$(CXX) $(CXXFLAGS) src/joint_growth_experiment.cpp -o $@
joint-growth-experiment: build/joint_growth_experiment
	./build/joint_growth_experiment
.PHONY: joint-growth-experiment
build/test_task_upgrade: tests/test_task_upgrade.cpp src/task_upgrade.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_task_upgrade.cpp -o $@
task-upgrade-test: build/test_task_upgrade
	ASAN_OPTIONS=detect_leaks=0 ./build/test_task_upgrade
.PHONY: task-upgrade-test
build/stateful_upgrade_experiment: src/stateful_upgrade_experiment.cpp src/task_upgrade.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/stateful_upgrade_experiment.cpp -o $@
stateful-upgrade-experiment: build/stateful_upgrade_experiment
	ASAN_OPTIONS=detect_leaks=0 ./build/stateful_upgrade_experiment
.PHONY: stateful-upgrade-experiment
build/loop_reader_experiment: src/loop_reader_experiment.cpp src/task_upgrade.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/loop_reader_experiment.cpp -o $@
loop-reader-experiment: build/loop_reader_experiment
	ASAN_OPTIONS=detect_leaks=0 ./build/loop_reader_experiment
.PHONY: loop-reader-experiment
build/test_vm_unary_skip: tests/test_vm_unary_skip.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_vm_unary_skip.cpp -o $@
vm-unary-skip-test: build/test_vm_unary_skip
	ASAN_OPTIONS=detect_leaks=0 ./build/test_vm_unary_skip
.PHONY: vm-unary-skip-test
build/test_vm_unary_copy: tests/test_vm_unary_copy.cpp src/task_upgrade.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_vm_unary_copy.cpp -o $@
vm-unary-copy-test: build/test_vm_unary_copy
	ASAN_OPTIONS=detect_leaks=0 ./build/test_vm_unary_copy
.PHONY: vm-unary-copy-test
build/test_vm_growth_loop: tests/test_vm_growth_loop.cpp src/task_upgrade.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_vm_growth_loop.cpp -o $@
vm-growth-loop-test: build/test_vm_growth_loop
	ASAN_OPTIONS=detect_leaks=0 ./build/test_vm_growth_loop
.PHONY: vm-growth-loop-test
build/test_vm_full_growth: tests/test_vm_full_growth.cpp src/task_upgrade.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_vm_full_growth.cpp -o $@
vm-full-growth-test: build/test_vm_full_growth
	ASAN_OPTIONS=detect_leaks=0 ./build/test_vm_full_growth
.PHONY: vm-full-growth-test
build/test_math_baseline: tests/test_math_baseline.cpp src/math_questions.hpp src/loop_vm_program.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_math_baseline.cpp -o $@
math-baseline-test: build/test_math_baseline
	ASAN_OPTIONS=detect_leaks=0 ./build/test_math_baseline
.PHONY: math-baseline-test
build/test_flip_vm: tests/test_flip_vm.cpp src/math_questions.hpp src/flip_vm_program.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_flip_vm.cpp -o $@
flip-vm-test: build/test_flip_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_flip_vm
.PHONY: flip-vm-test
build/operator_mutation_experiment: src/operator_mutation_experiment.cpp src/splice_operator.hpp src/flip_vm_program.hpp src/loop_vm_program.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/operator_mutation_experiment.cpp -o $@
operator-mutation-experiment: build/operator_mutation_experiment
	ASAN_OPTIONS=detect_leaks=0 ./build/operator_mutation_experiment
.PHONY: operator-mutation-experiment
build/test_splice_operator: tests/test_splice_operator.cpp src/splice_operator.hpp src/flip_vm_program.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_splice_operator.cpp -o $@
splice-operator-test: build/test_splice_operator
	ASAN_OPTIONS=detect_leaks=0 ./build/test_splice_operator
.PHONY: splice-operator-test
build/random_insertion_experiment: src/random_insertion_experiment.cpp src/loop_vm_program.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/random_insertion_experiment.cpp -o $@
random-insertion-experiment: build/random_insertion_experiment
	ASAN_OPTIONS=detect_leaks=0 ./build/random_insertion_experiment
.PHONY: random-insertion-experiment
build/seeded_operator_search: src/seeded_operator_search.cpp src/splice_operator.hpp src/flip_vm_program.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/seeded_operator_search.cpp -o $@
seeded-operator-search: build/seeded_operator_search
	ASAN_OPTIONS=detect_leaks=0 ./build/seeded_operator_search
.PHONY: seeded-operator-search
build/test_operator_width_context: tests/test_operator_width_context.cpp src/math_questions.hpp src/flip_vm_program.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_operator_width_context.cpp -o $@
operator-width-test: build/test_operator_width_context
	ASAN_OPTIONS=detect_leaks=0 ./build/test_operator_width_context
.PHONY: operator-width-test
build/test_operator_promotion_vm: tests/test_operator_promotion_vm.cpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_operator_promotion_vm.cpp -o $@
operator-promotion-test: build/test_operator_promotion_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_operator_promotion_vm
.PHONY: operator-promotion-test
build/test_integrated_operator_promotion: tests/test_integrated_operator_promotion.cpp src/promoting_flip_program.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_integrated_operator_promotion.cpp -o $@
integrated-operator-promotion-test: build/test_integrated_operator_promotion
	ASAN_OPTIONS=detect_leaks=0 ./build/test_integrated_operator_promotion
.PHONY: integrated-operator-promotion-test
build/test_two_position_growth: tests/test_two_position_growth.cpp src/promoting_flip_program.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_two_position_growth.cpp -o $@
two-position-growth-test: build/test_two_position_growth
	ASAN_OPTIONS=detect_leaks=0 ./build/test_two_position_growth
.PHONY: two-position-growth-test
build/test_reverse_growth: tests/test_reverse_growth.cpp src/promoting_flip_program.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_reverse_growth.cpp -o $@
reverse-growth-test: build/test_reverse_growth
	ASAN_OPTIONS=detect_leaks=0 ./build/test_reverse_growth
.PHONY: reverse-growth-test
build/test_simultaneous_growth: tests/test_simultaneous_growth.cpp src/promoting_flip_program.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_simultaneous_growth.cpp -o $@
simultaneous-growth-test: build/test_simultaneous_growth
	ASAN_OPTIONS=detect_leaks=0 ./build/test_simultaneous_growth
.PHONY: simultaneous-growth-test
build/test_work_insert_capacity: tests/test_work_insert_capacity.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_work_insert_capacity.cpp -o $@
work-insert-capacity-test: build/test_work_insert_capacity
	ASAN_OPTIONS=detect_leaks=0 ./build/test_work_insert_capacity
.PHONY: work-insert-capacity-test
build/test_growth_transaction: tests/test_growth_transaction.cpp src/promoting_flip_program.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_growth_transaction.cpp -o $@
growth-transaction-test: build/test_growth_transaction
	ASAN_OPTIONS=detect_leaks=0 ./build/test_growth_transaction
.PHONY: growth-transaction-test
build/test_layer_packet: tests/test_layer_packet.cpp src/layer_packet.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_layer_packet.cpp -o $@
layer-packet-test: build/test_layer_packet
	ASAN_OPTIONS=detect_leaks=0 ./build/test_layer_packet
.PHONY: layer-packet-test
build/test_layer_prefix_vm: tests/test_layer_prefix_vm.cpp src/layer_packet.hpp src/promoting_flip_program.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_layer_prefix_vm.cpp -o $@
layer-prefix-vm-test: build/test_layer_prefix_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_layer_prefix_vm
.PHONY: layer-prefix-vm-test
build/test_layer_end_vm: tests/test_layer_end_vm.cpp src/layer_packet.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_layer_end_vm.cpp -o $@
layer-end-vm-test: build/test_layer_end_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_layer_end_vm
.PHONY: layer-end-vm-test
build/test_layered_answer_vm: tests/test_layered_answer_vm.cpp src/layered_vm_program.hpp src/layer_packet.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_layered_answer_vm.cpp -o $@
layered-answer-vm-test: build/test_layered_answer_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_layered_answer_vm
.PHONY: layered-answer-vm-test
build/test_layer_end_to_end: tests/test_layer_end_to_end.cpp src/layered_vm_program.hpp src/layer_packet.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_layer_end_to_end.cpp -o $@
layer-end-to-end-test: build/test_layer_end_to_end
	ASAN_OPTIONS=detect_leaks=0 ./build/test_layer_end_to_end
.PHONY: layer-end-to-end-test
build/test_dynamic_period: tests/test_dynamic_period.cpp src/layered_vm_program.hpp src/layer_packet.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_dynamic_period.cpp -o $@
dynamic-period-test: build/test_dynamic_period
	ASAN_OPTIONS=detect_leaks=0 ./build/test_dynamic_period
.PHONY: dynamic-period-test
build/test_layered_growth: tests/test_layered_growth.cpp src/layered_vm_program.hpp src/layer_packet.hpp src/math_questions.hpp src/feedback_capture_vm.hpp src/work_consistency_vm.hpp src/direct_mask_update_vm.hpp src/context_choice_vm.hpp src/context_feedback_choice_vm.hpp src/operator_context_router_vm.hpp src/routed_context_choice_vm.hpp src/pending_operator_vm.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_layered_growth.cpp -o $@
layered-growth-test: build/test_layered_growth
	ASAN_OPTIONS=detect_leaks=0 ./build/test_layered_growth
.PHONY: layered-growth-test

build/test_operator_context_router_vm: tests/test_operator_context_router_vm.cpp src/operator_context_router_vm.hpp src/routed_context_choice_vm.hpp src/pending_operator_vm.hpp src/pending_choice_vm.hpp src/context_choice_vm.hpp src/layer_packet.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_operator_context_router_vm.cpp -o $@
operator-context-router-test: build/test_operator_context_router_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_operator_context_router_vm
.PHONY: operator-context-router-test

build/test_pending_feedback_cycle: tests/test_pending_feedback_cycle.cpp src/fragment_transaction.hpp src/layer_packet.hpp src/math_questions.hpp src/operator_context_router_vm.hpp src/pending_operator_vm.hpp src/pending_choice_vm.hpp src/feedback_capture_vm.hpp src/work_consistency_vm.hpp src/pending_mask_update_vm.hpp src/pending_confirm_vm.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_pending_feedback_cycle.cpp -o $@
pending-feedback-cycle-test: build/test_pending_feedback_cycle
	ASAN_OPTIONS=detect_leaks=0 ./build/test_pending_feedback_cycle
.PHONY: pending-feedback-cycle-test

build/test_growth_pending_bridge: tests/test_growth_pending_bridge.cpp src/integrated_zero_program.hpp src/layer_packet.hpp src/operator_context_router_vm.hpp src/pending_operator_vm.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_growth_pending_bridge.cpp -o $@
growth-pending-bridge-test: build/test_growth_pending_bridge
	ASAN_OPTIONS=detect_leaks=0 ./build/test_growth_pending_bridge
.PHONY: growth-pending-bridge-test

build/test_growth_feedback_cycle: tests/test_growth_feedback_cycle.cpp src/integrated_zero_program.hpp src/fragment_transaction.hpp src/layer_packet.hpp src/pending_operator_vm.hpp src/pending_choice_vm.hpp src/pending_confirm_vm.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_growth_feedback_cycle.cpp -o $@
growth-feedback-cycle-test: build/test_growth_feedback_cycle
	ASAN_OPTIONS=detect_leaks=0 ./build/test_growth_feedback_cycle
.PHONY: growth-feedback-cycle-test

build/test_pending_two_slots: tests/test_pending_two_slots.cpp src/pending_operator_vm.hpp src/pending_second_operator_vm.hpp src/pending_choice_vm.hpp src/pending_second_choice_vm.hpp src/pending_second_mask_update_vm.hpp src/pending_second_confirm_vm.hpp src/feedback_capture_vm.hpp src/work_consistency_vm.hpp src/operator_context_router_vm.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_pending_two_slots.cpp -o $@
pending-two-slots-test: build/test_pending_two_slots
	ASAN_OPTIONS=detect_leaks=0 ./build/test_pending_two_slots
.PHONY: pending-two-slots-test
build/test_successor_baseline: tests/test_successor_baseline.cpp src/layered_vm_program.hpp src/layer_packet.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_successor_baseline.cpp -o $@
successor-baseline-test: build/test_successor_baseline
	ASAN_OPTIONS=detect_leaks=0 ./build/test_successor_baseline
.PHONY: successor-baseline-test
build/test_next_two_bit_vm: tests/test_next_two_bit_vm.cpp src/next_two_bit_program.hpp src/layer_packet.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_next_two_bit_vm.cpp -o $@
next-two-bit-vm-test: build/test_next_two_bit_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_next_two_bit_vm
.PHONY: next-two-bit-vm-test
build/test_next_carry_vm: tests/test_next_carry_vm.cpp src/next_carry_program.hpp src/layer_packet.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_next_carry_vm.cpp -o $@
next-carry-vm-test: build/test_next_carry_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_next_carry_vm
.PHONY: next-carry-vm-test
build/test_layered_next_vm: tests/test_layered_next_vm.cpp src/layered_next_program.hpp src/layer_packet.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_layered_next_vm.cpp -o $@
layered-next-vm-test: build/test_layered_next_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_layered_next_vm
.PHONY: layered-next-vm-test
build/test_layered_next_three: tests/test_layered_next_three.cpp src/layered_next_program.hpp src/layer_packet.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_layered_next_three.cpp -o $@
layered-next-three-test: build/test_layered_next_three
	ASAN_OPTIONS=detect_leaks=0 ./build/test_layered_next_three
.PHONY: layered-next-three-test
build/test_layered_next_growth: tests/test_layered_next_growth.cpp src/layered_next_both.hpp src/layer_packet.hpp src/math_questions.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_layered_next_growth.cpp -o $@
layered-next-growth-test: build/test_layered_next_growth
	ASAN_OPTIONS=detect_leaks=0 ./build/test_layered_next_growth
.PHONY: layered-next-growth-test
build/test_layered_next_operator_growth: tests/test_layered_next_operator_growth.cpp src/layered_next_operator_growth.hpp src/layered_next_both.hpp src/next_carry_program.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_layered_next_operator_growth.cpp -o $@
layered-next-operator-growth-test: build/test_layered_next_operator_growth
	ASAN_OPTIONS=detect_leaks=0 ./build/test_layered_next_operator_growth
.PHONY: layered-next-operator-growth-test
build/test_operator_first_growth: tests/test_operator_first_growth.cpp src/layered_next_operator_growth.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_operator_first_growth.cpp -o $@
operator-first-growth-test: build/test_operator_first_growth
	ASAN_OPTIONS=detect_leaks=0 ./build/test_operator_first_growth
.PHONY: operator-first-growth-test
build/test_growth_genome: tests/test_growth_genome.cpp src/growth_genome.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_growth_genome.cpp -o $@
growth-genome-test: build/test_growth_genome
	ASAN_OPTIONS=detect_leaks=0 ./build/test_growth_genome
.PHONY: growth-genome-test
build/tail_gene_search: src/tail_gene_search.cpp src/growth_genome.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/tail_gene_search.cpp -o $@
tail-gene-search: build/tail_gene_search
	ASAN_OPTIONS=detect_leaks=0 ./build/tail_gene_search
.PHONY: tail-gene-search
build/integrated_zero_search: src/integrated_zero_search.cpp src/integrated_zero_program.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/integrated_zero_search.cpp -o $@
integrated-zero-search: build/integrated_zero_search
	ASAN_OPTIONS=detect_leaks=0 ./build/integrated_zero_search
.PHONY: integrated-zero-search
build/two_gene_zero_search: src/two_gene_zero_search.cpp src/integrated_zero_search.cpp src/integrated_zero_program.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/two_gene_zero_search.cpp -o $@
two-gene-zero-search: build/two_gene_zero_search
	ASAN_OPTIONS=detect_leaks=0 ./build/two_gene_zero_search
.PHONY: two-gene-zero-search
build/fragment_trial: src/fragment_trial.cpp src/fragment_transaction.hpp src/integrated_zero_search.cpp src/integrated_zero_program.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/fragment_trial.cpp -o $@
fragment-trial: build/fragment_trial
	ASAN_OPTIONS=detect_leaks=0 ./build/fragment_trial
.PHONY: fragment-trial
build/guest_fragment_trial: src/guest_fragment_trial.cpp src/guest_fragment_request.hpp src/fragment_transaction.hpp src/integrated_zero_search.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/guest_fragment_trial.cpp -o $@
guest-fragment-trial: build/guest_fragment_trial
	ASAN_OPTIONS=detect_leaks=0 ./build/guest_fragment_trial
.PHONY: guest-fragment-trial
build/resident_fragment_trial: src/resident_fragment_trial.cpp src/guest_fragment_request.hpp src/fragment_transaction.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/resident_fragment_trial.cpp -o $@
resident-fragment-trial: build/resident_fragment_trial
	ASAN_OPTIONS=detect_leaks=0 ./build/resident_fragment_trial
.PHONY: resident-fragment-trial
build/resident_growth_trial: src/resident_growth_trial.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/resident_growth_trial.cpp -o $@
resident-growth-trial: build/resident_growth_trial
	ASAN_OPTIONS=detect_leaks=0 ./build/resident_growth_trial
build/test_stable_work: tests/test_stable_work.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_stable_work.cpp -o $@
stable-work-test: build/test_stable_work
	ASAN_OPTIONS=detect_leaks=0 ./build/test_stable_work
.PHONY: resident-growth-trial stable-work-test
build/single_entry_trial: src/single_entry_trial.cpp src/single_entry_program.hpp src/guest_fragment_request.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/single_entry_trial.cpp -o $@
single-entry-trial: build/single_entry_trial
	ASAN_OPTIONS=detect_leaks=0 ./build/single_entry_trial
.PHONY: single-entry-trial
build/choice_gene_trial: src/choice_gene_trial.cpp src/single_entry_program.hpp src/guest_fragment_request.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/choice_gene_trial.cpp -o $@
choice-gene-trial: build/choice_gene_trial
	ASAN_OPTIONS=detect_leaks=0 ./build/choice_gene_trial
build/test_choice_policy: tests/test_choice_policy.cpp src/guest_fragment_request.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_choice_policy.cpp -o $@
choice-policy-test: build/test_choice_policy
	ASAN_OPTIONS=detect_leaks=0 ./build/test_choice_policy
.PHONY: choice-gene-trial choice-policy-test
build/sequential_fragment_trial: src/sequential_fragment_trial.cpp src/guest_trial_checkpoint.hpp src/single_entry_program.hpp src/guest_fragment_request.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/sequential_fragment_trial.cpp -o $@
sequential-fragment-trial: build/sequential_fragment_trial
	ASAN_OPTIONS=detect_leaks=0 ./build/sequential_fragment_trial
trial-budget-test: build/sequential_fragment_trial
	ASAN_OPTIONS=detect_leaks=0 ./build/sequential_fragment_trial 2
first-candidate-trial: build/sequential_fragment_trial
	ASAN_OPTIONS=detect_leaks=0 ./build/sequential_fragment_trial 4 0
all-fail-trial: build/sequential_fragment_trial
	ASAN_OPTIONS=detect_leaks=0 ./build/sequential_fragment_trial 4 -1
.PHONY: sequential-fragment-trial trial-budget-test first-candidate-trial all-fail-trial
build/test_work_trial_checkpoint: tests/test_work_trial_checkpoint.cpp src/work_trial_checkpoint.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_work_trial_checkpoint.cpp -o $@
work-trial-checkpoint-test: build/test_work_trial_checkpoint
	ASAN_OPTIONS=detect_leaks=0 ./build/test_work_trial_checkpoint
.PHONY: work-trial-checkpoint-test
build/test_guest_trial_checkpoint: tests/test_guest_trial_checkpoint.cpp src/guest_trial_checkpoint.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_guest_trial_checkpoint.cpp -o $@
guest-trial-checkpoint-test: build/test_guest_trial_checkpoint
	ASAN_OPTIONS=detect_leaks=0 ./build/test_guest_trial_checkpoint
.PHONY: guest-trial-checkpoint-test
build/test_tree_vm: tests/test_tree_vm.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_vm.cpp -o $@
tree-vm-test: build/test_tree_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_vm
.PHONY: tree-vm-test
build/test_tree_route_vm: tests/test_tree_route_vm.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_route_vm.cpp -o $@
tree-route-vm-test: build/test_tree_route_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_route_vm
.PHONY: tree-route-vm-test
build/test_tree_context_vm: tests/test_tree_context_vm.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_context_vm.cpp -o $@
tree-context-vm-test: build/test_tree_context_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_context_vm
.PHONY: tree-context-vm-test
build/test_tree_confirm_bridge: tests/test_tree_confirm_bridge.cpp src/tree_confirm_bridge.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_confirm_bridge.cpp -o $@
tree-confirm-bridge-test: build/test_tree_confirm_bridge
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_confirm_bridge
.PHONY: tree-confirm-bridge-test
build/test_tree_context_confirm: tests/test_tree_context_confirm.cpp src/tree_category_capture_vm.hpp src/tree_context_confirm_bridge.hpp src/tree_confirm_bridge.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_context_confirm.cpp -o $@
tree-context-confirm-test: build/test_tree_context_confirm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_context_confirm
.PHONY: tree-context-confirm-test

build/test_tree_pending_context: tests/test_tree_pending_context.cpp src/tree_pending_context_vm.hpp src/tree_grade_snapshot_vm.hpp src/tree_context_grade_confirm_vm.hpp src/tree_context_confirm_bridge.hpp src/tree_confirm_bridge.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_pending_context.cpp -o $@
tree-pending-context-test: build/test_tree_pending_context
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_pending_context
.PHONY: tree-pending-context-test
build/test_sequential_policy: tests/test_sequential_policy.cpp src/guest_fragment_request.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_sequential_policy.cpp -o $@
sequential-policy-test: build/test_sequential_policy
	ASAN_OPTIONS=detect_leaks=0 ./build/test_sequential_policy
.PHONY: sequential-policy-test
build/test_math_profile: tests/test_math_profile.cpp src/math_profile.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_math_profile.cpp -o $@
math-profile-test: build/test_math_profile
	ASAN_OPTIONS=detect_leaks=0 ./build/test_math_profile
.PHONY: math-profile-test
build/math_profile_cli: src/math_profile_cli.cpp src/math_profile.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/math_profile_cli.cpp -o $@
math-fixture-test: build/math_profile_cli fixtures/math_v0_1.jsonl tests/check_math_fixture.py
	ASAN_OPTIONS=detect_leaks=0 python3 tests/check_math_fixture.py
.PHONY: math-fixture-test
build/test_position_lexicon: tests/test_position_lexicon.cpp src/position_lexicon.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_position_lexicon.cpp -o $@
position-lexicon-test: build/test_position_lexicon
	ASAN_OPTIONS=detect_leaks=0 ./build/test_position_lexicon
.PHONY: position-lexicon-test
build/test_feedback_learner: tests/test_feedback_learner.cpp src/feedback_learner.hpp src/position_lexicon.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_feedback_learner.cpp -o $@
feedback-learner-test: build/test_feedback_learner
	ASAN_OPTIONS=detect_leaks=0 ./build/test_feedback_learner
.PHONY: feedback-learner-test
build/test_word_feedback_session: tests/test_word_feedback_session.cpp src/word_feedback_session.hpp src/feedback_learner.hpp src/position_lexicon.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_word_feedback_session.cpp -o $@
word-feedback-test: build/test_word_feedback_session
	ASAN_OPTIONS=detect_leaks=0 ./build/test_word_feedback_session
.PHONY: word-feedback-test
build/semantic_fragment_trial: src/semantic_fragment_trial.cpp src/feedback_learner.hpp src/fragment_transaction.hpp src/layer_packet.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer src/semantic_fragment_trial.cpp -o $@
semantic-fragment-trial: build/semantic_fragment_trial
	ASAN_OPTIONS=detect_leaks=0 ./build/semantic_fragment_trial
.PHONY: semantic-fragment-trial
build/test_hypothesis_mask_vm: tests/test_hypothesis_mask_vm.cpp src/hypothesis_mask_vm.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_hypothesis_mask_vm.cpp -o $@
hypothesis-mask-test: build/test_hypothesis_mask_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_hypothesis_mask_vm
.PHONY: hypothesis-mask-test
build/test_mask_choice_vm: tests/test_mask_choice_vm.cpp src/mask_choice_vm.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_mask_choice_vm.cpp -o $@
mask-choice-test: build/test_mask_choice_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_mask_choice_vm
.PHONY: mask-choice-test
build/test_feedback_choice_vm: tests/test_feedback_choice_vm.cpp src/feedback_choice_vm.hpp src/mask_choice_vm.hpp src/hypothesis_mask_vm.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_feedback_choice_vm.cpp -o $@
feedback-choice-test: build/test_feedback_choice_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_feedback_choice_vm
.PHONY: feedback-choice-test
build/test_feedback_fragment_cycle: tests/test_feedback_fragment_cycle.cpp src/feedback_choice_vm.hpp src/zero_consistency_vm.hpp src/one_consistency_vm.hpp src/copy_consistency_vm.hpp src/flip_consistency_vm.hpp src/feedback_capture_vm.hpp src/work_consistency_vm.hpp src/fragment_transaction.hpp src/layer_packet.hpp src/feedback_learner.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_feedback_fragment_cycle.cpp -o $@
feedback-fragment-cycle-test: build/test_feedback_fragment_cycle
	ASAN_OPTIONS=detect_leaks=0 ./build/test_feedback_fragment_cycle
.PHONY: feedback-fragment-cycle-test
build/test_context_choice_vm: tests/test_context_choice_vm.cpp src/context_choice_vm.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_context_choice_vm.cpp -o $@
context-choice-test: build/test_context_choice_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_context_choice_vm
.PHONY: context-choice-test
build/test_context_feedback_choice_vm: tests/test_context_feedback_choice_vm.cpp src/context_feedback_choice_vm.hpp src/context_choice_vm.hpp src/direct_mask_update_vm.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_context_feedback_choice_vm.cpp -o $@
context-feedback-choice-test: build/test_context_feedback_choice_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_context_feedback_choice_vm
.PHONY: context-feedback-choice-test

build/test_tree_trial_grade: tests/test_tree_trial_grade.cpp src/tree_trial_grade.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_trial_grade.cpp -o $@
tree-trial-grade-test: build/test_tree_trial_grade
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_trial_grade
.PHONY: tree-trial-grade-test
build/test_tree_pending_context: src/tree_trial_grade.hpp

build/test_tree_feedback_cycle: tests/test_tree_feedback_cycle.cpp src/tree_feedback_cycle_vm.hpp src/tree_feedback_mask_vm.hpp src/tree_grade_guard_vm.hpp src/tree_trial_grade.hpp src/tree_pending_context_vm.hpp src/tree_context_grade_confirm_vm.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_feedback_cycle.cpp -o $@
tree-feedback-cycle-test: build/test_tree_feedback_cycle
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_feedback_cycle
.PHONY: tree-feedback-cycle-test
build/test_tree_pending_context: src/tree_grade_guard_vm.hpp
build/test_tree_feedback_cycle: src/tree_candidate_choice_vm.hpp

build/test_tree_feedback_cycle: src/tree_guest_selection.hpp

build/test_tree_feedback_cycle: src/tree_learning_turn.hpp

build/test_tree_dynamic_scaffold: tests/test_tree_dynamic_scaffold.cpp src/tree_scaffold_vm.hpp src/tree_pending_context_vm.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_dynamic_scaffold.cpp -o $@
tree-dynamic-scaffold-test: build/test_tree_dynamic_scaffold
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_dynamic_scaffold
.PHONY: tree-dynamic-scaffold-test

build/test_tree_width_scaffold: tests/test_tree_width_scaffold.cpp src/tree_width_scaffold_vm.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_width_scaffold.cpp -o $@
tree-width-scaffold-test: build/test_tree_width_scaffold
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_width_scaffold
.PHONY: tree-width-scaffold-test

build/test_tree_width_route: tests/test_tree_width_route.cpp src/tree_width_route_vm.hpp src/tree_width_scaffold_vm.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_width_route.cpp -o $@
tree-width-route-test: build/test_tree_width_route
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_width_route
.PHONY: tree-width-route-test

build/test_tree_width_trial: tests/test_tree_width_trial.cpp src/tree_width_trial_vm.hpp src/tree_width_scaffold_vm.hpp src/tree_trial_grade.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_width_trial.cpp -o $@
tree-width-trial-test: build/test_tree_width_trial
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_width_trial
.PHONY: tree-width-trial-test

build/test_tree_width_pending: tests/test_tree_width_pending.cpp src/tree_width_pending_vm.hpp src/tree_width_choice_vm.hpp src/tree_width_scaffold_vm.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_width_pending.cpp -o $@
tree-width-pending-test: build/test_tree_width_pending
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_width_pending
.PHONY: tree-width-pending-test

build/test_tree_width_grade: tests/test_tree_width_grade.cpp src/tree_width_grade_vm.hpp src/tree_width_feedback_vm.hpp src/tree_width_pending_vm.hpp src/tree_width_trial_vm.hpp src/tree_trial_grade.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_width_grade.cpp -o $@
tree-width-grade-test: build/test_tree_width_grade
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_width_grade
.PHONY: tree-width-grade-test

build/test_tree_width_learning_turn: tests/test_tree_width_learning_turn.cpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_width_learning_turn.cpp -o $@
tree-width-learning-test: build/test_tree_width_learning_turn
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_width_learning_turn
.PHONY: tree-width-learning-test

build/test_tree_width_reuse: tests/test_tree_width_reuse.cpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_width_reuse.cpp -o $@
tree-width-reuse-test: build/test_tree_width_reuse
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_width_reuse
.PHONY: tree-width-reuse-test

build/test_tree_four_learning: tests/test_tree_four_learning.cpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_four_learning.cpp -o $@
tree-four-learning-test: build/test_tree_four_learning
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_four_learning
.PHONY: tree-four-learning-test

build/test_tree_observed_learner: tests/test_tree_observed_learner.cpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_observed_learner.cpp -o $@
tree-observed-learner-test: build/test_tree_observed_learner
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_observed_learner

build/benchmark_tree_observed_cost: tests/benchmark_tree_observed_cost.cpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) $(CXXFLAGS) tests/benchmark_tree_observed_cost.cpp -o $@
tree-observed-cost-benchmark: build/benchmark_tree_observed_cost
	./build/benchmark_tree_observed_cost
.PHONY: tree-observed-learner-test

build/test_vm_decode_snapshot: tests/test_vm_decode_snapshot.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O2 tests/test_vm_decode_snapshot.cpp -o $@
vm-decode-snapshot-test: build/test_vm_decode_snapshot
	./build/test_vm_decode_snapshot
.PHONY: vm-decode-snapshot-test

build/bench_vm_decode: tests/bench_vm_decode.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O2 tests/bench_vm_decode.cpp -o $@
vm-decode-bench: build/bench_vm_decode
	./build/bench_vm_decode
.PHONY: vm-decode-bench

build/test_tree_observed_transient: tests/test_tree_observed_transient.cpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_observed_transient.cpp -o $@
tree-observed-transient-test: build/test_tree_observed_transient
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_observed_transient
.PHONY: tree-observed-transient-test

build/test_tree_observed_policy: tests/test_tree_observed_policy.cpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_observed_policy.cpp -o $@
tree-observed-policy-test: build/test_tree_observed_policy
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_observed_policy
.PHONY: tree-observed-policy-test

build/test_tree_observed_resources: tests/test_tree_observed_resources.cpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_observed_resources.cpp -o $@
tree-observed-resources-test: build/test_tree_observed_resources
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_observed_resources
.PHONY: tree-observed-resources-test

build/test_tree_resource_birth: tests/test_tree_resource_birth.cpp tests/tree_resource_fixture.hpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_resource_birth.cpp -o $@
tree-resource-birth-test: build/test_tree_resource_birth
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_resource_birth
.PHONY: tree-resource-birth-test

build/tree_resource_population: src/tree_resource_population.cpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) $(CXXFLAGS) src/tree_resource_population.cpp -o $@
tree-resource-population: build/tree_resource_population
	./build/tree_resource_population
build/test_tree_resource_population: tests/test_tree_resource_population.cpp src/tree_resource_population.cpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_resource_population.cpp -o $@
tree-resource-population-test: build/test_tree_resource_population
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_resource_population
.PHONY: tree-resource-population tree-resource-population-test

build/test_tree_question_bank: tests/test_tree_question_bank.cpp src/tree_question_bank.hpp src/tree_question_experiment.hpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_question_bank.cpp -o $@
tree-question-bank-test: build/test_tree_question_bank
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_question_bank
.PHONY: tree-question-bank-test

build/tree_question_population: src/tree_question_population.cpp src/tree_resource_population.cpp src/tree_question_bank.hpp src/tree_question_experiment.hpp $(wildcard src/tree*.hpp) | build
	$(CXX) $(CXXFLAGS) src/tree_question_population.cpp -o $@
tree-question-population: build/tree_question_population
	./build/tree_question_population
build/test_tree_question_population: tests/test_tree_question_population.cpp src/tree_resource_population.cpp src/tree_question_bank.hpp src/tree_question_experiment.hpp $(wildcard src/tree*.hpp) | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_question_population.cpp -o $@
tree-question-population-test: build/test_tree_question_population
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_question_population
.PHONY: tree-question-population tree-question-population-test

build/tree_question_schedule_comparison: src/tree_question_schedule_comparison.cpp src/tree_resource_population.cpp src/tree_question_bank.hpp src/tree_question_experiment.hpp $(wildcard src/tree*.hpp) | build
	$(CXX) $(CXXFLAGS) src/tree_question_schedule_comparison.cpp -o $@
tree-question-schedules: build/tree_question_schedule_comparison
	./build/tree_question_schedule_comparison
build/test_tree_question_schedule: tests/test_tree_question_schedule.cpp src/tree_resource_population.cpp $(wildcard src/tree*.hpp) | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_question_schedule.cpp -o $@
tree-question-schedules-test: build/test_tree_question_schedule
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_question_schedule
.PHONY: tree-question-schedules tree-question-schedules-test

build/tree_question_order_experiment: src/tree_question_order_experiment.cpp src/tree_resource_population.cpp src/tree_question_bank.hpp $(wildcard src/tree*.hpp) | build
	$(CXX) $(CXXFLAGS) src/tree_question_order_experiment.cpp -o $@
tree-question-orders: build/tree_question_order_experiment
	./build/tree_question_order_experiment
build/test_tree_question_order: tests/test_tree_question_order.cpp src/tree_resource_population.cpp src/tree_question_bank.hpp $(wildcard src/tree*.hpp) | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_question_order.cpp -o $@
tree-question-orders-test: build/test_tree_question_order
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_question_order
.PHONY: tree-question-orders tree-question-orders-test

build/tree_question_trace: src/tree_question_trace.cpp src/tree_resource_population.cpp $(wildcard src/tree*.hpp) | build
	$(CXX) $(CXXFLAGS) src/tree_question_trace.cpp -o $@
tree-question-trace: build/tree_question_trace
	./build/tree_question_trace
build/test_tree_question_trace: tests/test_tree_question_trace.cpp src/tree_resource_population.cpp $(wildcard src/tree*.hpp) | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_question_trace.cpp -o $@
tree-question-trace-test: build/test_tree_question_trace
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_question_trace
.PHONY: tree-question-trace tree-question-trace-test

build/tree_question_review: src/tree_question_review.cpp src/tree_resource_population.cpp $(wildcard src/tree*.hpp) | build
	$(CXX) $(CXXFLAGS) src/tree_question_review.cpp -o $@
tree-question-review: build/tree_question_review
	./build/tree_question_review
build/test_tree_question_review: tests/test_tree_question_review.cpp src/tree_resource_population.cpp $(wildcard src/tree*.hpp) | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_question_review.cpp -o $@
tree-question-review-test: build/test_tree_question_review
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_question_review
.PHONY: tree-question-review tree-question-review-test

build/test_tree_error_trial: tests/test_tree_error_trial.cpp src/tree_error_trial.hpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_error_trial.cpp -o $@
tree-error-trial-test: build/test_tree_error_trial
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_error_trial
.PHONY: tree-error-trial-test

build/tree_error_world: src/tree_error_world.cpp src/tree_error_trial.hpp $(wildcard src/tree*.hpp) | build
	$(CXX) $(CXXFLAGS) src/tree_error_world.cpp -o $@
tree-error-world: build/tree_error_world
	./build/tree_error_world
build/test_tree_error_world: tests/test_tree_error_world.cpp src/tree_error_world.cpp src/tree_error_trial.hpp $(wildcard src/tree*.hpp) | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_error_world.cpp -o $@
tree-error-world-test: build/test_tree_error_world
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_error_world
.PHONY: tree-error-world tree-error-world-test

build/test_tree_compact_reference: tests/test_tree_compact_reference.cpp src/tree_compact_reference.hpp src/tree_error_trial.hpp $(wildcard src/tree*.hpp) | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_compact_reference.cpp -o $@
tree-compact-reference-test: build/test_tree_compact_reference
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_compact_reference
.PHONY: tree-compact-reference-test

.PHONY: tree-compact-world-test
tree-compact-world-test:
	mkdir -p build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_compact_world.cpp -o build/test_tree_compact_world
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_compact_world

build/test_tree_compact_differential_cost: tests/test_tree_compact_differential_cost.cpp src/tree_compact_reference.hpp src/tree_error_trial.hpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_compact_differential_cost.cpp -o $@
tree-compact-differential-cost-test: build/test_tree_compact_differential_cost
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_compact_differential_cost
.PHONY: tree-compact-differential-cost-test

build/test_tree_compact_optimized_cost: tests/test_tree_compact_optimized_cost.cpp src/tree_compact_reference.hpp src/tree_error_trial.hpp $(wildcard src/tree*.hpp) src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_compact_optimized_cost.cpp -o $@
tree-compact-optimized-cost-test: build/test_tree_compact_optimized_cost
	ASAN_OPTIONS=detect_leaks=0:quarantine_size_mb=16 ./build/test_tree_compact_optimized_cost
.PHONY: tree-compact-optimized-cost-test

# Growth-first regression: visible VM steps plus native TREE scan cost.
build/test_tree_compact_growth: tests/test_tree_compact_growth.cpp src/tree_compact_reference.hpp src/hamu_vm_core.hpp $(wildcard src/tree*.hpp) | build
	$(CXX) $(CXXFLAGS) tests/test_tree_compact_growth.cpp -o $@
tree-compact-growth-test: build/test_tree_compact_growth
	./build/test_tree_compact_growth
.PHONY: tree-compact-growth-test

# Non-VM reference only; demonstrates an extensible handle contract.
build/test_segmented_tree_growth_ref: tests/test_segmented_tree_growth_ref.cpp prototypes/segmented_tree_growth_ref.hpp | build
	$(CXX) $(CXXFLAGS) tests/test_segmented_tree_growth_ref.cpp -o $@
segmented-tree-growth-prototype-test: build/test_segmented_tree_growth_ref
	./build/test_segmented_tree_growth_ref
.PHONY: segmented-tree-growth-prototype-test

# Opt-in VM tree handle widening and host-authorized capacity growth.
build/test_tree_wide_vm_growth: tests/test_tree_wide_vm_growth.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_wide_vm_growth.cpp -o $@
wide-tree-growth-test: build/test_tree_wide_vm_growth
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_wide_vm_growth
.PHONY: wide-tree-growth-test

# Growth-first wide-tree index: packed host-internal cache vs exact linear semantics.
build/test_tree_wide_index: tests/test_tree_wide_index.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_wide_index.cpp -o $@
wide-tree-index-test: build/test_tree_wide_index
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_wide_index
.PHONY: wide-tree-index-test

# Experimental opt-in VM page-backed tree, fixed 31-row pages and stable ID.
build/test_tree_segmented_vm: tests/test_tree_segmented_vm.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_segmented_vm.cpp -o $@
segmented-vm-growth-test: build/test_tree_segmented_vm
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_segmented_vm
segmented-vm-growth-stress:
	mkdir -p build
	$(CXX) -std=c++17 -O2 tests/test_tree_segmented_vm.cpp -o build/test_tree_segmented_vm_stress
	./build/test_tree_segmented_vm_stress --stress-10000
.PHONY: segmented-vm-growth-test segmented-vm-growth-stress

# Explicit semantic migration (tree rows only) and sparse-ID reuse contract.
build/test_tree_wide_segment_migration: tests/test_tree_wide_segment_migration.cpp src/tree_wide_segment_migration.hpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_wide_segment_migration.cpp -o $@
wide-segment-migration-test: build/test_tree_wide_segment_migration
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_wide_segment_migration
.PHONY: wide-segment-migration-test

# Opt-in segmented-tree eight-candidate failed-answer mask, guest accessible.
build/test_tree_reject_mask: tests/test_tree_reject_mask.cpp src/hamu_vm_core.hpp | build
	$(CXX) -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_reject_mask.cpp -o $@
segmented-reject-mask-test: build/test_tree_reject_mask
	ASAN_OPTIONS=detect_leaks=0 ./build/test_tree_reject_mask
.PHONY: segmented-reject-mask-test

# Host-only guest execution contract reference; not production VM routing.
build/test_guest_trial_contract: tests/test_guest_trial_contract.cpp tests/test_tree_guest_full_state_transaction.cpp tests/tree_generation_registry_fixture.hpp tests/test_tree_reject_mask.cpp prototypes/guest_trial_contract_ref.hpp src/hamu_vm_core.hpp src/tree_wide_segment_migration.hpp | build
	$(CXX) -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_guest_trial_contract.cpp -o $@
guest-trial-contract-test: build/test_guest_trial_contract
	ASAN_OPTIONS=detect_leaks=0 ./build/test_guest_trial_contract
.PHONY: guest-trial-contract-test
