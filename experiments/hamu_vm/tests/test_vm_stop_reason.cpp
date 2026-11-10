#include "../src/hamu_vm_core.hpp"
#include <initializer_list>
#include <iostream>
#include <stdexcept>

static void require_reason(bool condition,const char* message) {
    if(!condition)throw std::runtime_error(message);
}
static HamsterParams reason_config(int capacity=2) {
    HamsterParams p;
    p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=350;p.layout.total_size=1374;p.layout.val_reg_size=21;
    p.tree_segmented_enabled=true;p.tree_reject_mask_enabled=true;
    p.tree_id_bits=16;p.tree_capacity=capacity;p.tree_index_enabled=true;
    return p;
}
static void reason_load(Hamster& h,std::initializer_list<int> words,int limit=100) {
    int at=h.params.layout.program_start;
    for(int word:words)
        for(bool bit:SpiralToken(word,h.params.op_order,h.params.op_lvl).bits)
            h.memory.at(at++)=bit;
    h.pro_1=h.params.layout.program_start;h.pro_2=at-1;
    h.stop=false;h.executed_steps=0;h.step_limit=limit;
    h.budget_exhausted=h.work_insert_blocked=h.tree_capacity_blocked=false;
}
static void normal_and_reentry() {
    Hamster h(9100,reason_config());
    reason_load(h,{15,0});simulate_spiral_program(h);
    require_reason(h.stop && h.stop_reason==VmStopReason::OutArea && h.executed_steps==1,
                   "OUT_AREA reason/compatibility");
    simulate_spiral_program(h);
    require_reason(h.stop_reason==VmStopReason::OutArea && h.executed_steps==1,
                   "stopped reentry must preserve existing reason and cost");
    reason_load(h,{0,7});simulate_spiral_program(h);
    require_reason(h.stop && h.stop_reason==VmStopReason::SetAreaStop,"SET_AREA(7) reason");
    reason_load(h,{0,3});simulate_spiral_program(h);
    require_reason(!h.stop && h.stop_reason==VmStopReason::WindowEnd &&
                   h.ptr==h.params.layout.work_start,"window-end reason changed legacy stop flag");
    const int first_window_steps=h.executed_steps;
    h.ptr=0;simulate_spiral_program(h);
    require_reason(!h.stop && h.stop_reason==VmStopReason::WindowEnd &&
                   h.executed_steps==first_window_steps+1 && h.ptr==h.params.layout.work_start,
                   "WindowEnd prevented the legacy repeated-window execution");
    h.stop=true;simulate_spiral_program(h);
    require_reason(h.stop_reason==VmStopReason::AlreadyStopped,"host-stopped window end needs AlreadyStopped");
    reason_load(h,{0,3});h.stop_reason=VmStopReason::InvalidJumpTarget;
    simulate_spiral_program(h);
    require_reason(h.stop_reason==VmStopReason::WindowEnd,"active invocation retained stale reason");
    h.stop=true;h.stop_reason=VmStopReason::None;const int steps=h.executed_steps;
    simulate_spiral_program(h);
    require_reason(h.stop_reason==VmStopReason::AlreadyStopped && h.executed_steps==steps,
                   "unclassified host stop executes or loses reason");
    h.stop_reason=VmStopReason::InvalidJumpTarget;
    h.budget_exhausted=h.work_insert_blocked=h.tree_capacity_blocked=true;
    h.write_prob(Problem{});
    require_reason(h.stop_reason==VmStopReason::None && !h.stop && h.executed_steps==0 &&
                   !h.budget_exhausted && !h.work_insert_blocked && !h.tree_capacity_blocked,
                   "new question retained stop reason or attempt flags");
    std::cout<<"PASS raw normal exits, legacy stop bool, stale reason reset and stopped reentry\n";
}
static void invalid_windows_and_targets() {
    Hamster h(9110,reason_config());
    reason_load(h,{15,0});h.pro_1=h.params.layout.program_start-1;
    simulate_spiral_program(h);
    require_reason(h.stop && h.stop_reason==VmStopReason::InvalidWindow && h.executed_steps==0,
                   "invalid initial window not classified");
    for(int opcode:{12,13,20}) {
        reason_load(h,{opcode,15,15,0});simulate_spiral_program(h);
        require_reason(h.stop && h.stop_reason==VmStopReason::InvalidJumpTarget && h.executed_steps==1,
                       "invalid SET_PTR/JUMP target not classified");
    }
    reason_load(h,{12,18,13,5,2,1});simulate_spiral_program(h);
    require_reason(h.stop && h.stop_reason==VmStopReason::InvalidWindow && h.executed_steps==3,
                   "invalid deferred window switch not classified");
    reason_load(h,{16,1,13,3,12,22,2,1});simulate_spiral_program(h);
    require_reason(h.stop && h.stop_reason==VmStopReason::InvalidWindow && h.executed_steps==3,
                   "invalid immediate window switch not classified");
    // SET_PTR2 may prepare a next window which is never selected. No postflight rejection.
    reason_load(h,{13,1,15,0});simulate_spiral_program(h);
    require_reason(h.stop_reason==VmStopReason::OutArea,"unselected deferred window changed successful exit");
    // Raw VM retains the historical floor-to-complete-token initial-window rule.
    reason_load(h,{0,3});--h.pro_2;simulate_spiral_program(h);
    require_reason(!h.stop && h.stop_reason==VmStopReason::WindowEnd,"raw partial-token compatibility changed");
    std::cout<<"PASS raw invalid initial/window switches and jump targets; deferred/partial-token compatibility\n";
}
static void resource_reasons() {
    Hamster h(9120,reason_config());
    reason_load(h,{0,3,2,1,15,0},1);simulate_spiral_program(h);
    require_reason(h.stop && h.budget_exhausted && h.stop_reason==VmStopReason::BudgetExhausted,
                   "budget reason diverged from legacy flag");
    reason_load(h,{0,3,10,1,15,0});h.memory[h.params.layout.program_start-1]=true;
    simulate_spiral_program(h);
    require_reason(h.stop && h.work_insert_blocked && h.stop_reason==VmStopReason::WorkCapacity,
                   "work-capacity reason diverged from legacy flag");
    reason_load(h,{28,1,28,2,28,3,15,0});
    std::fill(h.val_reg.begin(),h.val_reg.end(),false);simulate_spiral_program(h);
    require_reason(h.stop && h.tree_capacity_blocked && h.stop_reason==VmStopReason::TreeCapacity,
                   "tree-capacity reason diverged from legacy flag");
    std::cout<<"PASS budget, strict INSERT and TREE capacity reasons preserve existing flags\n";
}
int main() {
    normal_and_reentry();invalid_windows_and_targets();resource_reasons();
    return 0;
}
