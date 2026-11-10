#include "../src/layer_packet.hpp"
#include "../src/operator_context_router_vm.hpp"
#include "../src/pending_operator_vm.hpp"
#include "../src/pending_second_operator_vm.hpp"
#include "../src/pending_second_choice_vm.hpp"
#include "../src/pending_choice_vm.hpp"
#include "../src/pending_second_mask_update_vm.hpp"
#include "../src/pending_second_confirm_vm.hpp"
#include "../src/pending_mask_update_vm.hpp"
#include "../src/pending_confirm_vm.hpp"
#include "../src/math_questions.hpp"
#include "../src/feedback_capture_vm.hpp"
#include "../src/work_consistency_vm.hpp"
#include <cassert>
#include <iostream>

int main() {
    auto router=operator_context_router_program();
    auto first=pending_operator_program();
    auto second=pending_second_operator_program();
    auto choose_first=pending_choice_program();
    auto choose_second=pending_second_choice_program();
    auto update0=pending_second_mask_update_program(0);
    auto update1=pending_second_mask_update_program(1);
    auto confirm=pending_second_confirm_program();
    const std::vector<int> copy_fragment{0,0,14,31,14,24,4,3,0,2,14,17,9,3,14,19,3,1,15,0};
    const std::vector<int> flip_fragment{0,0,14,31,14,24,4,3,0,2,14,17,2,3,14,3,5,3,14,19,3,1,15,0};
    auto capture=feedback_capture_program();
    auto copy_check=work_bitwise_consistency_program(false);
    auto flip_check=work_bitwise_consistency_program(true);
    auto first_update0=pending_mask_update_program(0);
    auto first_update1=pending_mask_update_program(1);
    auto first_confirm=pending_confirm_program();
    HamsterParams p;p.op_order=5;p.layout.status_start=45;
    p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=160;p.stable_work_bits=40;
    const int first_at=160+int(router.size())*6;
    const int second_at=first_at+int(first.size())*6;
    const int first_choice_at=second_at+int(second.size())*6;
    const int second_choice_at=first_choice_at+int(choose_first.size())*6;
    const int update0_at=second_choice_at+int(choose_second.size())*6;
    const int update1_at=update0_at+int(update0.size())*6;
    const int confirm_at=update1_at+int(update1.size())*6;
    const int copy_at=confirm_at+int(confirm.size())*6;
    const int flip_at=copy_at+int(copy_fragment.size())*6;
    const int capture_at=flip_at+int(flip_fragment.size())*6;
    const int copy_check_at=capture_at+int(capture.size())*6;
    const int flip_check_at=copy_check_at+int(copy_check.size())*6;
    const int first_update0_at=flip_check_at+int(flip_check.size())*6;
    const int first_update1_at=first_update0_at+int(first_update0.size())*6;
    const int first_confirm_at=first_update1_at+int(first_update1.size())*6;
    const int end=first_confirm_at+int(first_confirm.size())*6;
    p.layout.total_size=end;
    Hamster h(33,p);int at=160;
    for(const auto& code:{router,first,second,choose_first,choose_second,update0,update1,confirm,
                          copy_fragment,flip_fragment,capture,copy_check,flip_check,
                          first_update0,first_update1,first_confirm})
        for(int word:code)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
    assert(at==end);
    h.memory[101]=1; // existing n=3 position context
    auto run=[&](Hamster& guest,int start,int finish,int limit) {
        guest.stop=false;guest.executed_steps=0;guest.step_limit=limit;
        guest.pro_1=start;guest.pro_2=finish-1;
        simulate_spiral_program(guest);
        assert(!guest.budget_exhausted&&!guest.work_insert_blocked);
    };
    auto ask=[&](Hamster& guest,int op) {
        Problem blank;guest.write_prob(blank);
        const auto bits=encode_layer_packet(op,3,1,3);
        for(size_t j=0;j<bits.size();++j)guest.memory[1+j]=bits[j];
        run(guest,160,first_at,80);
        assert(!guest.memory[125]);
        run(guest,first_at,second_at,120);
        run(guest,second_at,first_choice_at,120);
    };
    ask(h,3);
    assert(h.memory[127]&&!h.memory[140]);
    // A stopped write of ID 4 must not publish the second slot to children.
    h.new_his();
    auto partial=[&](int limit) {
        Hamster trial(35,p);trial.copy_hamu(h);
        Problem blank;trial.write_prob(blank);
        const auto bits=encode_layer_packet(4,3,1,3);
        for(size_t j=0;j<bits.size();++j)trial.memory[1+j]=bits[j];
        run(trial,160,first_at,80);
        run(trial,first_at,second_at,120);
        trial.stop=false;trial.executed_steps=0;trial.step_limit=limit;
        trial.pro_1=second_at;trial.pro_2=first_choice_at-1;
        simulate_spiral_program(trial);
        return trial;
    };
    int low=1,high=120;
    while(low<high) {
        const int mid=(low+high)/2;
        if(partial(mid).written[145])high=mid;
        else low=mid+1;
    }
    Hamster interrupted=partial(low);
    assert(interrupted.written[145]&&interrupted.memory[145]);
    assert(interrupted.budget_exhausted&&!interrupted.memory[140]);
    interrupted.new_his();Hamster incomplete_child(36,p);
    incomplete_child.copy_hamu(interrupted);
    assert(incomplete_child.memory[127]&&!incomplete_child.memory[140]);
    ask(h,4);
    assert(h.memory[127]&&h.memory[140]&&h.memory[141]);
    assert(h.memory[145]&&!h.memory[146]&&!h.memory[147]); // ID 4 = 100
    for(int i=0;i<3;++i)assert(h.memory[142+i]==h.memory[19+i]);
    const auto saved=h.memory;
    ask(h,3);ask(h,5);
    for(int i=127;i<=138;++i)assert(h.memory[i]==saved[i]);
    for(int i=140;i<=147;++i)assert(h.memory[i]==saved[i]);
    h.new_his();Hamster child(34,p);child.copy_hamu(h);
    for(int i=127;i<=138;++i)assert(child.memory[i]==saved[i]);
    for(int i=140;i<=147;++i)assert(child.memory[i]==saved[i]);
    child.memory[135]=1;child.memory[136]=0; // first ID 3 -> local 0
    child.memory[148]=0;child.memory[149]=1; // second ID 4 -> local 1
    auto choose=[&](int op,int first_slot,int second_slot) {
        Problem blank;child.write_prob(blank);
        const auto bits=encode_layer_packet(op,3,2,3);
        for(size_t j=0;j<bits.size();++j)child.memory[1+j]=bits[j];
        auto check=[&](int start,int finish,int expected) {
            child.written[51]=child.written[52]=child.written[53]=false;
            run(child,start,finish,120);
            assert(child.written[51]==(expected>=0));
            if(expected>=0)assert(child.written[52]&&child.written[53]&&
                                  !child.memory[51]&&child.memory[52]==bool(expected)&&
                                  !child.memory[53]);
        };
        check(first_choice_at,second_choice_at,first_slot);
        check(second_choice_at,update0_at,second_slot);
    };
    choose(3,0,-1);
    choose(4,-1,1);
    choose(5,-1,-1);
    child.memory[148]=child.memory[149]=1; // both second-slot hypotheses
    child.memory[55]=0; // result of an inconsistent candidate-0 trial
    run(child,update0_at,update1_at,50);
    assert(!child.memory[148]&&child.memory[149]);
    child.memory[55]=1; // consistent candidate-1 trial
    run(child,update1_at,confirm_at,50);
    assert(!child.memory[148]&&child.memory[149]);
    assert(child.memory[135]&&!child.memory[136]); // first slot unaffected
    choose(4,-1,1);
    child.memory[114]=0;
    run(child,confirm_at,copy_at,150);
    assert(!child.memory[150]); // unique candidate without correct grade
    child.memory[148]=1;child.memory[114]=1;
    run(child,confirm_at,copy_at,150);
    assert(!child.memory[150]); // two candidates even with correct grade
    child.memory[148]=0;
    choose(3,0,-1);child.memory[114]=1;
    run(child,confirm_at,copy_at,150);
    assert(!child.memory[150]); // unrelated word's grade cannot confirm ID 4
    choose(4,-1,1);child.memory[114]=1;
    run(child,confirm_at,copy_at,150);
    assert(child.memory[150]&&child.memory[151]); // ID 1, committed
    assert(child.memory[135]&&!child.memory[136]);
    child.new_his();Hamster confirmed_child(37,p);confirmed_child.copy_hamu(child);
    assert(confirmed_child.memory[150]&&confirmed_child.memory[151]);
    // Separate real VM trial: the teacher defines ID 4 as FLIP. The host
    // provides both executable fragments; the guest evaluates their outputs.
    Hamster real(38,p);real.copy_hamu(h);
    real.memory[148]=real.memory[149]=1;
    real.memory[103]=real.memory[104]=real.memory[105]=1;
    real.memory[106]=0; // known n=3 data-position unary record
    auto trial=[&](int candidate,int value) {
        auto q=elementary_problem(ElementaryTask::Flip,3,value);
        q.question[0]=SpiralToken(4,3,1);
        real.write_prob(q);
        const auto bits=encode_layer_packet(4,3,value,3);
        for(size_t j=0;j<bits.size();++j)real.memory[1+j]=bits[j];
        run(real,second_choice_at,update0_at,120);
        assert(real.written[52]&&real.memory[52]==bool(candidate));
        real.write_prob(q); // new trial clears selector scratch and write coverage
        for(size_t j=0;j<bits.size();++j)real.memory[1+j]=bits[j];
        run(real,candidate?flip_at:copy_at,candidate?capture_at:flip_at,90);
        const bool correct=Check_ans(real,q);
        if(correct!=bool(candidate))std::cerr<<"trial candidate="<<candidate<<" value="<<value
            <<" output="<<real.memory[51]<<real.memory[52]<<real.memory[53]<<real.memory[54]
            <<" expected="<<q.answer.bits[0]<<q.answer.bits[1]<<q.answer.bits[2]<<q.answer.bits[3]<<"\n";
        assert(correct==bool(candidate));
        real.memory[40]=correct;
        run(real,capture_at,copy_check_at,170);
        assert(real.written[114]&&real.memory[114]==correct);
        run(real,candidate?flip_check_at:copy_check_at,
            candidate?first_update0_at:flip_check_at,110);
        if(!(real.written[55]&&real.memory[55]==correct))
            std::cerr<<"consistency candidate="<<candidate<<" grade="<<correct
                     <<" observed="<<real.memory[55]<<" written="<<real.written[55]<<"\n";
        assert(real.written[55]&&real.memory[55]==correct);
        run(real,candidate?update1_at:update0_at,
            candidate?confirm_at:update1_at,50);
        run(real,confirm_at,copy_at,150);
    };
    // Learn the first recorded word, ID 3 = COPY, before teaching ID 4.
    // The host explores FLIP once, then the guest's first-slot selector
    // chooses the surviving COPY fragment. Both slots remain independent.
    real.memory[135]=real.memory[136]=1;
    auto first_trial=[&](int candidate,int value) {
        auto q=elementary_problem(ElementaryTask::Copy,3,value);
        q.question[0]=SpiralToken(3,3,1);
        const auto bits=encode_layer_packet(3,3,value,3);
        real.write_prob(q);
        for(size_t j=0;j<bits.size();++j)real.memory[1+j]=bits[j];
        if(!candidate) {
            run(real,first_choice_at,second_choice_at,120);
            assert(real.written[52]&&!real.memory[52]);
            real.write_prob(q);
            for(size_t j=0;j<bits.size();++j)real.memory[1+j]=bits[j];
        }
        run(real,candidate?flip_at:copy_at,candidate?capture_at:flip_at,90);
        const bool correct=Check_ans(real,q);
        assert(correct==!bool(candidate));
        real.memory[40]=correct;
        run(real,capture_at,copy_check_at,170);
        assert(real.written[114]&&real.memory[114]==correct);
        run(real,candidate?flip_check_at:copy_check_at,
            candidate?first_update0_at:flip_check_at,110);
        assert(real.written[55]&&real.memory[55]==correct);
        run(real,candidate?first_update1_at:first_update0_at,
            candidate?first_confirm_at:first_update1_at,50);
        run(real,first_confirm_at,end,150);
    };
    first_trial(1,5);
    assert(real.memory[135]&&!real.memory[136]&&!real.memory[137]);
    first_trial(0,6);
    assert(real.memory[135]&&!real.memory[136]&&real.memory[137]&&!real.memory[138]);
    trial(0,1);
    assert(!real.memory[148]&&real.memory[149]&&!real.memory[150]);
    trial(1,2);
    assert(!real.memory[148]&&real.memory[149]&&real.memory[150]&&real.memory[151]);
    real.new_his();Hamster learned(39,p);learned.copy_hamu(real);
    assert(learned.memory[127]&&learned.memory[140]&&learned.memory[150]&&learned.memory[151]);
    learned.memory[148]=learned.memory[149]=0; // confirmed ID is authoritative
    auto held_out=elementary_problem(ElementaryTask::Flip,3,7);
    held_out.question[0]=SpiralToken(4,3,1);
    learned.write_prob(held_out);
    const auto held_bits=encode_layer_packet(4,3,7,3);
    for(size_t j=0;j<held_bits.size();++j)learned.memory[1+j]=held_bits[j];
    run(learned,second_choice_at,update0_at,120);
    assert(learned.written[52]&&learned.memory[52]);
    learned.write_prob(held_out);
    for(size_t j=0;j<held_bits.size();++j)learned.memory[1+j]=held_bits[j];
    run(learned,flip_at,capture_at,90);
    assert(Check_ans(learned,held_out));
    real.new_his();Hamster bilingual(43,p);bilingual.copy_hamu(real);
    bilingual.memory[135]=bilingual.memory[136]=0;
    bilingual.memory[148]=bilingual.memory[149]=0;
    for(int op:{3,4})for(int value:{0,3,4,7}) {
        const auto task=op==3?ElementaryTask::Copy:ElementaryTask::Flip;
        auto q=elementary_problem(task,3,value);
        q.question[0]=SpiralToken(op,3,1);
        const auto bits=encode_layer_packet(op,3,value,3);
        bilingual.write_prob(q);
        for(size_t j=0;j<bits.size();++j)bilingual.memory[1+j]=bits[j];
        run(bilingual,op==3?first_choice_at:second_choice_at,
            op==3?second_choice_at:update0_at,120);
        assert(bilingual.written[52]&&bilingual.memory[52]==bool(op==4));
        bilingual.write_prob(q);
        for(size_t j=0;j<bits.size();++j)bilingual.memory[1+j]=bits[j];
        run(bilingual,op==3?copy_at:flip_at,op==3?flip_at:capture_at,90);
        assert(Check_ans(bilingual,q));
    }
    // An unseen third word must not borrow either confirmed meaning.
    Problem unknown;bilingual.write_prob(unknown);
    const auto unknown_bits=encode_layer_packet(5,3,4,3);
    for(size_t j=0;j<unknown_bits.size();++j)bilingual.memory[1+j]=unknown_bits[j];
    run(bilingual,first_choice_at,second_choice_at,120);
    assert(!bilingual.written[51]&&!bilingual.written[52]);
    run(bilingual,second_choice_at,update0_at,120);
    assert(!bilingual.written[51]&&!bilingual.written[52]);
    // Step-budget interruption between writing ID and the commit bit.
    Hamster ready(40,p);real.new_his();ready.copy_hamu(real);
    ready.memory[150]=0;ready.memory[151]=0;
    ready.memory[114]=1;ready.memory[148]=0;ready.memory[149]=1;
    ready.new_his();
    auto partial_confirm=[&](int limit) {
        Hamster trial_guest(41,p);trial_guest.copy_hamu(ready);
        auto q=elementary_problem(ElementaryTask::Flip,3,2);
        q.question[0]=SpiralToken(4,3,1);
        trial_guest.write_prob(q);
        const auto bits=encode_layer_packet(4,3,2,3);
        for(size_t j=0;j<bits.size();++j)trial_guest.memory[1+j]=bits[j];
        trial_guest.stop=false;trial_guest.executed_steps=0;
        trial_guest.step_limit=limit;
        trial_guest.pro_1=confirm_at;trial_guest.pro_2=copy_at-1;
        simulate_spiral_program(trial_guest);
        return trial_guest;
    };
    int first_write=1,last_write=150;
    while(first_write<last_write) {
        int mid=(first_write+last_write)/2;
        if(partial_confirm(mid).written[151])last_write=mid;
        else first_write=mid+1;
    }
    Hamster incomplete=partial_confirm(first_write);
    assert(incomplete.written[151]&&incomplete.memory[151]);
    assert(incomplete.budget_exhausted&&!incomplete.written[150]&&!incomplete.memory[150]);
    incomplete.new_his();Hamster uncommitted_child(42,p);
    uncommitted_child.copy_hamu(incomplete);
    uncommitted_child.memory[148]=uncommitted_child.memory[149]=0;
    Problem blank;uncommitted_child.write_prob(blank);
    const auto pending_bits=encode_layer_packet(4,3,2,3);
    for(size_t j=0;j<pending_bits.size();++j)uncommitted_child.memory[1+j]=pending_bits[j];
    run(uncommitted_child,second_choice_at,update0_at,120);
    assert(!uncommitted_child.written[51]);
    std::cout<<"PASS two different recorded words learned in one guest, offspring answers both, interrupted commit safety\n";
}
