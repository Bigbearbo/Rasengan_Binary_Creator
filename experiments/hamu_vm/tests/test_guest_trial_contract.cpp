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
static void legacy_stop_reason_gap() {
    Hamster h(9050,contract_config()); DurableRegistry d(h,9050); uint64_t rev=0;
    ReferenceTrial trial(h,d,rev);
    prepare(h,{28,1,20,15,15,0}); set_id_candidate(h,0,0);
    const auto result=trial.run(); // JUMP_LOCAL(-15) stops on invalid target
    require(result.committed && result.outcome==Outcome::Completed &&
            h.stop && (h.segment_row(1)&1u),"legacy stop reason behavior changed");
    std::cout<<"KNOWN_GAP reference: invalid jump target is indistinguishable from explicit stop; prefix commits\n";
}
int main() {
    legacy_gaps(); successful_guest(); rejected_attempts();
    wrong_answer_is_not_execution_failure(); exception_and_invalid_input();
    read_trace_outlives_rollback(); legacy_stop_reason_gap();
    std::cout<<"SCOPE host-only reference; no production routing, disk atomicity or autonomous learning\n";
    return 0;
}
