// Keep the old envelope unchanged so its gaps remain reproducible.
#include "tree_generation_registry_fixture.hpp"
#define main legacy_full_state_envelope_main
#include "test_tree_guest_full_state_transaction.cpp"
#undef main
#include "../prototypes/guest_trial_contract_ref.hpp"
#include <cmath>

using guest_trial_ref::Outcome;
using ReferenceTrial = guest_trial_ref::Trial<Hamster, DurableRegistry>;

static void prepare(Hamster& h, std::initializer_list<int> words, int limit=100) {
    int at=h.params.layout.program_start;
    for (int word:words)
        for (bool bit:SpiralToken(word,h.params.op_order,h.params.op_lvl).bits)
            h.memory.at(at++)=bit;
    h.pro_1=h.params.layout.program_start;
    h.pro_2=at-1;
    h.stop=false;
    h.budget_exhausted=h.work_insert_blocked=h.tree_capacity_blocked=false;
    h.executed_steps=0;
    h.step_limit=limit;
}
static void cost_is(const Hamster& h, float before, const guest_trial_ref::Result& r) {
    require(r.attempted_steps>0 && r.charged_hp>0,"executed attempt was free");
    require(std::fabs(h.hp-(before-r.charged_hp))<0.0001f,"cost lost or charged twice");
}
static HamsterParams contract_config(int capacity=3) {
    auto p=cfg(true,capacity);
    p.tree_confirm_three_bits_enabled=true;
    p.unit_cost_per=4;
    return p;
}

static void legacy_gaps() {
    Hamster h(9000,contract_config()); DurableRegistry d(h,9000); RevisionRegistry r(d);
    FullStateEnvelope old{h,d,r};
    prepare(h,{0,3,15,0}); // SET_AREA work: changes only ptr and diagnostics
    require(old.run([&]{simulate_spiral_program(h);return true;}),"old pointer trial");
    require(h.ptr==h.params.layout.work_start && r.revision==0,"pointer gap changed");
    prepare(h,{28,1,28,2,15,0},1);
    set_id_candidate(h,0,0);
    require(old.run([&]{simulate_spiral_program(h);return true;}),"old budget trial");
    require(h.budget_exhausted && (h.segment_row(1)&1u) && r.revision==1,
            "expected old partial budget commit");
    std::cout<<"KNOWN_GAP legacy envelope: ptr-only change unversioned; budget exhaustion can commit prefix\n";
}
static void successful_guest() {
    Hamster h(9001,contract_config()); DurableRegistry d(h,9001); uint64_t rev=0;
    ReferenceTrial trial(h,d,rev);
    prepare(h,{28,1,15,0}); set_id_candidate(h,0,0); float hp=h.hp;
    auto result=trial.run();
    require(result.committed && rev==1 && (h.segment_row(1)&1u),"guest TREE_ADD commit");
    cost_is(h,hp,result);
    prepare(h,{0,3,15,0}); hp=h.hp; result=trial.run();
    require(result.committed && rev==2 && h.ptr==h.params.layout.work_start,"ptr-only version");
    cost_is(h,hp,result);
    prepare(h,{15,0}); hp=h.hp; result=trial.run();
    require(result.committed && !result.versioned_change && rev==2,"STOP-only changed version");
    cost_is(h,hp,result);
    prepare(h,{0,3,2,1,15,0}); result=trial.run();
    require(result.committed && rev==3 && h.memory[h.params.layout.work_start],"work-only commit");
    std::cout<<"PASS guest TREE_ADD, cursor-only, work-only, no-op and separate HP settlement\n";
}
static void rejected_attempts() {
    for (int kind=0;kind<4;++kind) {
        Hamster h(9010+kind,contract_config(2)); DurableRegistry d(h,9010+kind); uint64_t rev=0;
        ReferenceTrial trial(h,d,rev);
        if(kind==0) prepare(h,{28,1,28,2,15,0},1); // actual partial add then budget failure
        if(kind==1) prepare(h,{28,1,28,2,28,3,15,0}); // actual tree capacity failure
        if(kind==2) {
            h.memory[h.params.layout.program_start-1]=true;
            prepare(h,{28,1,0,3,10,1,15,0}); // tree insertion then strict work INSERT failure
        }
        if(kind==3) prepare(h,{28,1,15,0});
        set_id_candidate(h,0,0);
        if(kind==3) rev=UINT64_MAX;
        const Hamster before=h; const auto bytes=d.snapshot(); const auto before_rev=rev;
        const auto result=trial.run();
        const Outcome expected[]={Outcome::BudgetExhausted,Outcome::TreeCapacity,Outcome::WorkCapacity,Outcome::RevisionOverflow};
        require(!result.committed && result.outcome==expected[kind],"wrong rejection outcome");
        require(h.memory==before.memory && h.val_reg==before.val_reg &&
                h.ptr==before.ptr && h.written==before.written && h.read_seen==before.read_seen &&
                h.segment_pages==before.segment_pages && h.segment_used==before.segment_used &&
                h.stop==before.stop && h.executed_steps==before.executed_steps &&
                h.budget_exhausted==before.budget_exhausted &&
                h.work_insert_blocked==before.work_insert_blocked &&
                h.tree_capacity_blocked==before.tree_capacity_blocked &&
                h.stop_reason==before.stop_reason &&
                d.snapshot()==bytes && rev==before_rev,"rejected guest leaked state");
        cost_is(h,before.hp,result);
        if(kind==0) {const float hp=h.hp; const auto retry=trial.run(); cost_is(h,hp,retry);
            require(!retry.committed && rev==before_rev,"retry committed unexpectedly");}
    }
    std::cout<<"PASS budget/tree/work capacity and revision-overflow rollback; retries still cost HP\n";
}
static void wrong_answer_is_not_execution_failure() {
    Hamster h(9020,contract_config()); DurableRegistry d(h,9020); uint64_t rev=0;
    ReferenceTrial trial(h,d,rev);
    prepare(h,{28,1,0,2,2,1,15,0}); set_id_candidate(h,0,0);
    auto attempt=trial.run();
    require(attempt.committed && h.memory[h.params.layout.output_start],"wrong output not committed");
    // HOST teacher compares the designated output bit to the expected false.
    // This is a controlled one-bit task, not autonomous grading or learning.
    const bool correct=h.memory[h.params.layout.output_start]==false;
    require(!correct,"fixture should be a wrong answer");
    const auto answer_revision=rev;
    prepare(h,{30,3,15,0}); set_id_candidate(h,1,5);
    auto feedback=trial.run(); // guest TREE_ACTION marks the host-supplied candidate
    require(feedback.committed && rev==answer_revision+1,"feedback not separate commit");
    require(((h.segment_row(1)>>28)&1u)!=0,"wrong candidate not remembered");
    const auto remembered=h.segment_pages;
    prepare(h,{30,3,28,2,15,0},1); set_id_candidate(h,1,6);
    const auto rejected=trial.run();
    require(!rejected.committed && h.segment_pages==remembered,"failed feedback leaked or erased old lesson");
    prepare(h,{30,2,15,0}); set_id_candidate(h,1,5);
    const auto read=trial.run();
    require(read.committed && h.val_reg[16] && h.val_reg[20],"guest forgot previous wrong answer");
    h.new_his(); Hamster child(9021,h.params); child.copy_hamu(h);
    require(child.segment_pages==h.segment_pages,"inherited rejection mask lost");
    std::cout<<"PASS wrong answer commits; separate guest feedback survives failed later feedback and inheritance\n";
}
static void exception_and_invalid_input() {
    Hamster h(9030,contract_config()); DurableRegistry d(h,9030); uint64_t rev=0;
    ReferenceTrial trial(h,d,rev);
    prepare(h,{28,1,15,0});set_id_candidate(h,0,0);require(trial.run().committed,"setup failed");
    const auto handle=d.acquire(1);
    prepare(h,{0,3,2,1,15,0}); const auto bytes=d.snapshot(); const auto before=h; const auto old_rev=rev;
    const auto fault=trial.run_with_host_fault_for_test([&]{
        require(d.erase(handle),"host fault setup erase failed"); h.hp-=7;
        throw std::runtime_error("injected after real guest write");
    });
    require(fault.outcome==Outcome::Exception && !fault.committed && !fault.error.empty(),"exception not reported");
    require(d.snapshot()==bytes && d.valid(handle) && rev==old_rev && h.memory==before.memory,
            "exception leaked work/generation");
    cost_is(h,before.hp,fault);
    prepare(h,{15,0});h.pro_1++; const auto invalid_before=h;
    const auto invalid=trial.run();
    require(invalid.outcome==Outcome::InvalidInput && invalid.attempted_steps==0 &&
            invalid.charged_hp==0 && h.hp==invalid_before.hp && h.memory==invalid_before.memory,
            "invalid window charged or mutated");
    std::cout<<"PASS host-injected exception restores generation/HP mutation; invalid window is free and inert\n";
}
static void read_trace_outlives_rollback() {
    Hamster h(9040,contract_config()); DurableRegistry d(h,9040); uint64_t rev=0;
    ReferenceTrial trial(h,d,rev);
    h.memory[h.params.layout.input_start]=true;
    prepare(h,{4,1,28,1,15,0},1); // READ succeeds, then budget expires
    const auto before=h;
    const auto result=trial.run();
    require(result.outcome==Outcome::BudgetExhausted && !result.committed,"read budget outcome");
    require(result.read_trace[h.params.layout.input_start],"attempt diagnostics lost read");
    require(h.read_seen==before.read_seen && h.val_reg==before.val_reg && rev==0,
            "read trace or registers leaked into rejected state");
    std::cout<<"PASS attempted read trace survives in result, not rolled-back guest state\n";
}
static void invalid_jump_rolls_back() {
    Hamster h(9050,contract_config()); DurableRegistry d(h,9050); uint64_t rev=0;
    ReferenceTrial trial(h,d,rev);
    prepare(h,{28,1,20,15,15,0}); set_id_candidate(h,0,0);
    const auto before=h; const auto bytes=d.snapshot();
    const auto result=trial.run(); // JUMP_LOCAL(-15) stops on invalid target
    require(!result.committed && result.outcome==Outcome::InvalidJumpTarget &&
            result.stop_reason==VmStopReason::InvalidJumpTarget && result.observed_stop,
            "invalid jump target was accepted or lost reason");
    require(d.snapshot()==bytes && h.memory==before.memory &&
            h.val_reg==before.val_reg && h.stop==before.stop &&
            h.stop_reason==before.stop_reason && rev==0,"invalid jump leaked prefix state");
    require(result.attempted_steps==2,"invalid jump cost does not include attempted jump");
    cost_is(h,before.hp,result);
    const float retry_hp=h.hp;
    const auto retry=trial.run();
    require(!retry.committed && retry.stop_reason==VmStopReason::InvalidJumpTarget &&
            d.snapshot()==bytes && rev==0,"invalid jump retry leaked prefix");
    cost_is(h,retry_hp,retry);
    std::cout<<"PASS invalid jump rolls back guest prefix; reason survives rollback and retry costs HP\n";
}
static void normal_stop_reasons_commit() {
    const std::initializer_list<int> programs[]={{28,1,15,0},{28,1,0,7},{28,1}};
    const VmStopReason expected[]={VmStopReason::OutArea,VmStopReason::SetAreaStop,VmStopReason::WindowEnd};
    for(int i=0;i<3;++i) {
        Hamster h(9060+i,contract_config());DurableRegistry d(h,9060+i);uint64_t rev=0;
        ReferenceTrial trial(h,d,rev);
        prepare(h,programs[i]);set_id_candidate(h,0,0);const float hp=h.hp;
        const auto result=trial.run();
        require(result.committed && result.outcome==Outcome::Completed &&
                result.stop_reason==expected[i] && h.stop_reason==expected[i],"normal reason not committed");
        require((h.segment_row(1)&1u) && rev==1,"normal stop lost tree prefix");
        require(result.observed_stop==(i!=2),"legacy stop bool compatibility changed");
        cost_is(h,hp,result);
    }
    std::cout<<"PASS OUT_AREA, SET_AREA(7), window end commit with distinct normal reasons\n";
}
static void switched_invalid_windows_roll_back() {
    const std::initializer_list<int> programs[]={
        {0,2,2,1,12,22,13,5,2,1}, // output prefix, then deferred window start>end
        {0,2,2,1,16,1,13,3,12,26,2,1} // prefix, then immediate window start>end
    };
    for(int i=0;i<2;++i) {
        Hamster h(9070+i,contract_config());DurableRegistry d(h,9070+i);uint64_t rev=0;
        ReferenceTrial trial(h,d,rev);
        prepare(h,programs[i]);const auto before=h;
        const auto result=trial.run();
        require(!result.committed && result.outcome==Outcome::InvalidInput &&
                result.stop_reason==VmStopReason::InvalidWindow,"invalid switched window accepted");
        require(h.memory==before.memory && h.ptr==before.ptr && h.pro_1==before.pro_1 &&
                h.pro_2==before.pro_2 && h.stop_reason==before.stop_reason && rev==0,
                "invalid switched window leaked output or cursor");
        cost_is(h,before.hp,result);
    }
    std::cout<<"PASS invalid deferred/immediate window switch rolls back prior output and cursors\n";
}
int main() {
    legacy_gaps(); successful_guest(); rejected_attempts();
    wrong_answer_is_not_execution_failure(); exception_and_invalid_input();
    read_trace_outlives_rollback(); invalid_jump_rolls_back();normal_stop_reasons_commit();
    switched_invalid_windows_roll_back();
    std::cout<<"SCOPE host-only reference; no production routing, disk atomicity or autonomous learning\n";
    return 0;
}
