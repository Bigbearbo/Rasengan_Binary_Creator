#pragma once
#include "hamu_vm_core.hpp"
#include <array>
#include <stdexcept>

// Host teacher for the fixed n=3 tree experiment, not a guest learning rule.
// The runner must execute only the candidate VM program. Clear prior output
// coverage before running it; publish a grade only for this fresh attempt.
template<class Runner>
bool run_tree_graded_trial(Hamster& h, const std::array<bool,3>& expected,
                           Runner run_candidate) {
    const auto& l=h.params.layout;
    if(l.status_start-l.input_start<=40 || l.work_start-l.output_start<3 ||
       l.program_start-l.work_start<=94)
        throw std::invalid_argument("Tree trial layout is too small");
    h.memory[l.input_start+40]=false;
    h.memory[l.work_start+34]=false;
    h.memory[l.work_start+92]=false;
    h.memory[l.work_start+93]=false;
    h.memory[l.work_start+94]=false;
    std::fill(h.memory.begin()+l.output_start,h.memory.begin()+l.work_start,false);
    std::fill(h.written.begin()+l.output_start,h.written.begin()+l.work_start,false);
    const std::vector<bool> question(h.memory.begin()+l.input_start,
                                   h.memory.begin()+l.status_start);
    h.stop=false;h.budget_exhausted=false;h.executed_steps=0;
    h.work_insert_blocked=false;
    run_candidate();
    bool valid=h.stop&&!h.budget_exhausted&&!h.work_insert_blocked;
    valid=valid&&std::equal(question.begin(),question.end(),
                                h.memory.begin()+l.input_start);
    for(int bit=0;bit<3;++bit)
        valid=valid&&h.written[l.output_start+bit];
    // This experiment emits three information bits; its fixed tail is implicit.
    for(int at=l.output_start+3;at<l.work_start;++at)
        if(h.written[at])valid=false;
    bool correct=valid;
    for(int bit=0;bit<3;++bit)
        correct=correct&&h.memory[l.output_start+bit]==expected[bit];
    // Candidate work writes cannot publish their own teacher confirmation.
    h.memory[l.work_start+34]=false;
    h.memory[l.work_start+92]=false;
    h.memory[l.work_start+94]=false;
    h.memory[l.work_start+93]=valid; // teacher-owned admissible observation
    h.memory[l.input_start+40]=correct;
    return correct;
}
