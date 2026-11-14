#pragma once
#include "tree_candidate_choice_vm.hpp"
#include "hamu_vm_core.hpp"
#include <optional>

struct TreeGuestSelection { int slot; int candidate; };

// The host only schedules the same guest selector for each slot and reads its
// declared output. The selector itself checks the question and pending memory.
template<class Runner>
std::optional<TreeGuestSelection> run_tree_guest_selection(Hamster& h,Runner run){
    const int out=h.params.layout.output_start;
    if(out+26>=h.params.layout.work_start)
        throw std::invalid_argument("Tree selection output layout is too small");
    for(int slot:{57,70}){
        for(int pos=out+25;pos<=out+26;++pos){
            h.memory[pos]=false;h.written[pos]=false;
        }
        h.stop=false;h.budget_exhausted=false;
        run(tree_candidate_choice_program(slot));
        if(h.budget_exhausted)continue;
        if(h.stop&&h.written[out+25]&&h.written[out+26]&&h.memory[out+25])
            return TreeGuestSelection{slot,int(h.memory[out+26])};
    }
    return std::nullopt;
}
