#include "../src/fragment_transaction.hpp"
#include "../src/layer_packet.hpp"
#include "../src/math_questions.hpp"
#include "../src/operator_context_router_vm.hpp"
#include "../src/pending_operator_vm.hpp"
#include "../src/pending_choice_vm.hpp"
#include "../src/feedback_capture_vm.hpp"
#include "../src/work_consistency_vm.hpp"
#include "../src/pending_mask_update_vm.hpp"
#include "../src/pending_confirm_vm.hpp"
#include <array>
#include <cassert>
#include <iostream>

int main() {
    auto genome=integrated_zero_program(15);
    const auto original=genome.words;
    const auto route=operator_context_router_program();
    const auto pending=pending_operator_program();
    const auto choose=pending_choice_program();
    const auto capture=feedback_capture_program();
    const auto copy_check=work_bitwise_consistency_program(false);
    const auto flip_check=work_bitwise_consistency_program(true);
    const auto update0=pending_mask_update_program(0);
    const auto update1=pending_mask_update_program(1);
    const auto confirm=pending_confirm_program();
    int end=140+int(genome.words.size())*6;
    const int route_start=end;end+=int(route.size())*6;
    const int pending_start=end;end+=int(pending.size())*6;
    const int choose_start=end;end+=int(choose.size())*6;
    const int capture_start=end;end+=int(capture.size())*6;
    const int copy_start=end;end+=int(copy_check.size())*6;
    const int flip_start=end;end+=int(flip_check.size())*6;
    const int update0_start=end;end+=int(update0.size())*6;
    const int update1_start=end;end+=int(update1.size())*6;
    const int confirm_start=end;end+=int(confirm.size())*6;
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;p.stable_work_bits=20;
    p.layout.total_size=end;
    Hamster h(22,p);int at=140;
    auto append=[&](const std::vector<int>& words) {
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
    };
    for(const auto& program:{genome.words,route,pending,choose,capture,
                             copy_check,flip_check,update0,update1,confirm})append(program);
    assert(at==end);
    for(int i=80;i<98;++i)h.memory[i]=1;
    h.memory[98]=0;
    h.memory[99]=h.memory[100]=1;h.memory[101]=0; // operator n=2
    h.memory[102]=h.memory[103]=h.memory[104]=1;h.memory[105]=0; // data n=3
    for(int i=0;i<4;++i)h.memory[120+i]=(i%2==0); // old contexts sentinel
    h.memory[135]=h.memory[136]=1; // two preinstalled hypotheses for new word

    auto problem=[&](int data) {
        auto q=elementary_problem(ElementaryTask::Flip,3,data);
        q.question[0]=SpiralToken(3,3,1); // human test dictionary: ID 3 means FLIP
        return q;
    };
    auto put_question=[&](Hamster& guest,int op,int data) {
        auto q=problem(data);guest.write_prob(q);
        const auto bits=encode_layer_packet(op,3,data,3);
        for(size_t j=0;j<bits.size();++j)guest.memory[1+j]=bits[j];
        return q;
    };
    auto run=[&](Hamster& guest,int start,int finish,int limit) {
        guest.stop=false;guest.executed_steps=0;
        guest.pro_1=start;guest.pro_2=finish-1;guest.step_limit=limit;
        simulate_spiral_program(guest);
        assert(!guest.budget_exhausted&&!guest.work_insert_blocked);
    };
    auto select=[&](Hamster& guest,int op,int data) {
        put_question(guest,op,data);
        guest.written[51]=guest.written[52]=guest.written[53]=false;
        run(guest,choose_start,capture_start,120);
        if(!guest.written[51])return -1;
        if(!(guest.written[52]&&guest.written[53]&&!guest.memory[51]&&!guest.memory[53]))
            std::cerr<<"choice invalid op="<<op<<" data="<<data
                     <<" committed="<<guest.memory[137]<<" id="<<guest.memory[138]
                     <<" bits="<<guest.written[51]<<guest.written[52]<<guest.written[53]
                     <<" values="<<guest.memory[51]<<guest.memory[52]<<guest.memory[53]<<"\n";
        assert(guest.written[52]&&guest.written[53]&&!guest.memory[51]&&!guest.memory[53]);
        return int(guest.memory[52]);
    };
    auto known_flip=[&](int op_n,int data) {
        auto q=elementary_problem_with_operator_order(ElementaryTask::Flip,op_n,3,data);
        h.write_prob(q);
        const auto bits=encode_layer_packet(1,op_n,data,3);
        for(size_t j=0;j<bits.size();++j)h.memory[1+j]=bits[j];
        run(h,140,route_start,900);
        assert(Check_ans(h,q));
    };
    known_flip(2,1);
    assert(!h.memory[101]);
    known_flip(3,2); // first n=3 operator has 1 at the old tail position
    assert(h.memory[101]&&!h.memory[127]); // guest grew before encountering ID 3
    put_question(h,3,1);
    run(h,route_start,pending_start,80);
    assert(!h.memory[125]);
    run(h,pending_start,choose_start,120);
    assert(h.memory[127]&&h.memory[128]&&!h.memory[132]&&h.memory[133]&&h.memory[134]);
    h.memory[114]=1; // even a positive grade is insufficient while both survive
    run(h,confirm_start,end,140);
    assert(!h.memory[137]);
    h.memory[135]=0;h.memory[114]=0; // one survivor without a correct grade
    run(h,confirm_start,end,140);
    assert(!h.memory[137]);
    h.memory[135]=1;
    const std::array<std::vector<int>,2> fragments{{
        {0,0,14,31,14,24,4,3,0,2,14,17,9,3,14,19,3,1,15,0},
        {0,0,14,31,14,24,4,3,0,2,14,17,2,3,14,3,5,3,14,19,3,1,15,0}
    }};
    const std::array<int,2> data{{1,2}};
    for(int round=0;round<2;++round) {
        const int candidate=select(h,3,data[round]);
        assert(candidate==round);
        bool correct=false;
        {
            FragmentTransaction trial(genome,fragments[candidate]);
            int location=140+genome.reserve_start*12;
            for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
                for(bool bit:SpiralToken(genome.words[i],5,1).bits)h.memory.at(location++)=bit;
            const auto q=put_question(h,3,data[round]);
            run(h,140,route_start,900);
            correct=Check_ans(h,q);
            assert(correct==bool(round));
            h.memory[40]=correct; // one-bit teacher grade
            run(h,capture_start,copy_start,170);
            assert(h.written[114]&&h.memory[114]==correct);
            run(h,candidate?flip_start:copy_start,
                candidate?update0_start:flip_start,110);
            assert(h.written[55]&&h.memory[55]==bool(round));
            // Wrong COPY is eliminated; correct FLIP remains compatible.
        }
        // Undo the host's provisional executable fragment before the next trial.
        assert(genome.words==original);
        int location=140+genome.reserve_start*12;
        for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
            for(bool bit:SpiralToken(genome.words[i],5,1).bits)h.memory.at(location++)=bit;
        run(h,candidate?update1_start:update0_start,candidate?confirm_start:update1_start,50);
        assert(!h.memory[135]&&h.memory[136]);
        run(h,confirm_start,end,140);
        assert(h.memory[137]==bool(round));
        if(round==1)assert(h.memory[138]); // confirmed candidate ID 1
        if(round==0) {
            put_question(h,0,1); // a correct grade for a different word
            h.memory[114]=1;
            run(h,confirm_start,end,140);
            assert(!h.memory[137]);
        }
        for(int i=0;i<4;++i)assert(h.memory[120+i]==(i%2==0));
    }
    for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip}) {
        const int op=task==ElementaryTask::Copy?0:1;
        const int data=task==ElementaryTask::Copy?5:3;
        auto old=elementary_problem_with_operator_order(task,3,3,data);
        h.write_prob(old);
        const auto bits=encode_layer_packet(op,3,data,3);
        for(size_t j=0;j<bits.size();++j)h.memory[1+j]=bits[j];
        run(h,140,route_start,900);
        assert(Check_ans(h,old)); // executable reserve was rolled back
        run(h,route_start,pending_start,80);
        assert(h.memory[125]);
        run(h,pending_start,choose_start,120);
        assert(h.memory[127]&&h.memory[136]&&!h.memory[135]);
        assert(!h.memory[132]&&h.memory[133]&&h.memory[134]); // pending ID 3
        for(int i=0;i<4;++i)assert(h.memory[120+i]==(i%2==0));
    }
    assert(select(h,3,7)==1);
    {
        FragmentTransaction held_out(genome,fragments[1]);
        int location=140+genome.reserve_start*12;
        for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
            for(bool bit:SpiralToken(genome.words[i],5,1).bits)h.memory.at(location++)=bit;
        const auto q=put_question(h,3,7);
        run(h,140,route_start,900);
        assert(Check_ans(h,q)); // held-out input, not used to choose FLIP
    }
    assert(genome.words==original);
    int restored=140+genome.reserve_start*12;
    for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
        for(bool bit:SpiralToken(genome.words[i],5,1).bits)h.memory.at(restored++)=bit;
    assert(select(h,2,7)==-1);
    h.new_his();Hamster child(23,p);child.copy_hamu(h);
    assert(child.memory[127]&&!child.memory[135]&&child.memory[136]&&child.memory[137]);
    assert(child.memory[138]);
    assert(select(child,3,0)==1);
    child.memory[135]=child.memory[136]=0; // the committed ID is authoritative
    assert(select(child,3,4)==1);
    assert(select(child,2,4)==-1); // no cross-word borrowing

    // An independent dictionary may teach the same unseen word as COPY.
    // The guest must commit local candidate ID 0 when it alone survives.
    Hamster copy_learner(24,p);copy_learner.copy_hamu(h);
    copy_learner.memory[135]=copy_learner.memory[136]=1;
    copy_learner.memory[137]=0;copy_learner.memory[138]=1;
    assert(select(copy_learner,3,6)==0);
    auto copy_trial=[&](int candidate,int value) {
        auto q=elementary_problem(ElementaryTask::Copy,3,value);
        q.question[0]=SpiralToken(3,3,1);
        {
            FragmentTransaction trial(genome,fragments[candidate]);
            int location=140+genome.reserve_start*12;
            for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
                for(bool bit:SpiralToken(genome.words[i],5,1).bits)
                    copy_learner.memory.at(location++)=bit;
            copy_learner.write_prob(q);
            const auto bits=encode_layer_packet(3,3,value,3);
            for(size_t j=0;j<bits.size();++j)copy_learner.memory[1+j]=bits[j];
            run(copy_learner,140,route_start,900);
            const bool correct=Check_ans(copy_learner,q);
            assert(correct==!candidate);
            copy_learner.memory[40]=correct;
            run(copy_learner,capture_start,copy_start,170);
            run(copy_learner,candidate?flip_start:copy_start,
                candidate?update0_start:flip_start,110);
            assert(copy_learner.written[55]&&copy_learner.memory[55]==correct);
        }
        assert(genome.words==original);
        int restore=140+genome.reserve_start*12;
        for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
            for(bool bit:SpiralToken(genome.words[i],5,1).bits)
                copy_learner.memory.at(restore++)=bit;
        run(copy_learner,candidate?update1_start:update0_start,
            candidate?confirm_start:update1_start,50);
        run(copy_learner,confirm_start,end,140);
    };
    copy_trial(0,6); // correct, but both candidates still survive
    assert(!copy_learner.memory[137]&&copy_learner.memory[135]&&copy_learner.memory[136]);
    copy_trial(1,5); // wrong FLIP removes candidate 1
    assert(!copy_learner.memory[137]);
    assert(copy_learner.memory[135]&&!copy_learner.memory[136]);
    copy_trial(0,2); // correct grade belongs to this exact word
    assert(copy_learner.memory[137]&&!copy_learner.memory[138]);
    copy_learner.new_his();Hamster copy_child(25,p);copy_child.copy_hamu(copy_learner);
    assert(copy_child.memory[137]&&!copy_child.memory[138]);
    assert(select(copy_child,3,4)==0);
    copy_child.memory[135]=copy_child.memory[136]=0;
    assert(select(copy_child,3,7)==0);
    assert(select(copy_child,2,7)==-1);
    auto answer_from_memory=[&](Hamster& guest,ElementaryTask meaning,int value,int expected) {
        const int candidate=select(guest,3,value); // guest's stored ID chooses the fragment
        assert(candidate==expected);
        auto q=elementary_problem(meaning,3,value);
        q.question[0]=SpiralToken(3,3,1);
        {
            FragmentTransaction trial(genome,fragments.at(candidate));
            int location=140+genome.reserve_start*12;
            for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
                for(bool bit:SpiralToken(genome.words[i],5,1).bits)
                    guest.memory.at(location++)=bit;
            guest.write_prob(q);
            const auto bits=encode_layer_packet(3,3,value,3);
            for(size_t j=0;j<bits.size();++j)guest.memory[1+j]=bits[j];
            run(guest,140,route_start,900);
            assert(Check_ans(guest,q)); // real VM execution on unseen data
        }
        assert(genome.words==original);
        int restore=140+genome.reserve_start*12;
        for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
            for(bool bit:SpiralToken(genome.words[i],5,1).bits)
                guest.memory.at(restore++)=bit;
    };
    answer_from_memory(child,ElementaryTask::Flip,4,1);
    answer_from_memory(copy_child,ElementaryTask::Copy,7,0);
    auto interrupted_commit=[&](Hamster& source,ElementaryTask meaning,int id) {
        Hamster ready(26+id,p);ready.copy_hamu(source);
        auto q=elementary_problem(meaning,3,1);
        q.question[0]=SpiralToken(3,3,1);
        ready.write_prob(q);
        const auto bits=encode_layer_packet(3,3,1,3);
        for(size_t j=0;j<bits.size();++j)ready.memory[1+j]=bits[j];
        ready.memory[114]=1; // matching positive teacher grade
        ready.memory[135]=!id;ready.memory[136]=id;
        ready.memory[137]=0;ready.memory[138]=!id; // distinguish a fresh write
        ready.new_his();
        auto interrupted_at=[&](int limit) {
            Hamster interrupted(28+id,p);interrupted.copy_hamu(ready);
            interrupted.write_prob(q);
            for(size_t j=0;j<bits.size();++j)interrupted.memory[1+j]=bits[j];
            interrupted.pro_1=confirm_start;interrupted.pro_2=end-1;
            interrupted.step_limit=limit;interrupted.executed_steps=0;
            interrupted.stop=false;
            simulate_spiral_program(interrupted);
            return interrupted;
        };
        int low=1,high=140;
        while(low<high) {
            const int mid=(low+high)/2;
            if(interrupted_at(mid).written[138])high=mid;
            else low=mid+1;
        }
        Hamster interrupted=interrupted_at(low);
        assert(interrupted.written[138]&&interrupted.memory[138]==bool(id));
        assert(interrupted.budget_exhausted&&!interrupted.written[137]&&!interrupted.memory[137]);
        interrupted.new_his();Hamster descendant(30+id,p);
        descendant.copy_hamu(interrupted);
        assert(!descendant.memory[137]);
        descendant.memory[135]=descendant.memory[136]=0;
        assert(select(descendant,3,1)==-1); // uncommitted ID cannot route
    };
    interrupted_commit(child,ElementaryTask::Flip,1);
    interrupted_commit(copy_child,ElementaryTask::Copy,0);
    auto same_number_other_width=[&](Hamster& donor,ElementaryTask meaning) {
        Hamster guest(32,p);donor.new_his();guest.copy_hamu(donor);
        auto q=elementary_problem(meaning,3,5);
        q.question[0]=SpiralToken(3,2,1); // same numeric ID, shorter word
        guest.write_prob(q);
        const auto bits=encode_layer_packet(3,2,5,3);
        for(size_t j=0;j<bits.size();++j)guest.memory[1+j]=bits[j];
        guest.memory[101]=0; // supplied n=2 context; no downgrade learner here
        run(guest,route_start,pending_start,80);
        run(guest,pending_start,choose_start,120);
        guest.written[51]=guest.written[52]=guest.written[53]=false;
        run(guest,choose_start,capture_start,120);
        assert(!guest.written[51]&&!guest.written[52]&&!guest.written[53]);
        assert(guest.memory[127]&&guest.memory[137]); // saved n=3 word unchanged
    };
    same_number_other_width(child,ElementaryTask::Flip);
    same_number_other_width(copy_child,ElementaryTask::Copy);
    std::cout<<"PASS pending ID 3: inherited answer, interrupted commit, width isolation\n";
}
