#include "../src/feedback_choice_vm.hpp"
#include "../src/fragment_transaction.hpp"
#include "../src/layer_packet.hpp"
#include "../src/math_questions.hpp"
#include "../src/feedback_learner.hpp"
#include "../src/zero_consistency_vm.hpp"
#include "../src/one_consistency_vm.hpp"
#include "../src/copy_consistency_vm.hpp"
#include "../src/flip_consistency_vm.hpp"
#include "../src/feedback_capture_vm.hpp"
#include "../src/work_consistency_vm.hpp"
#include <array>
#include <cassert>
#include <iostream>

int main() {
    auto genome=integrated_zero_program(15);
    const auto original_words=genome.words;
    const auto controller=feedback_choice_program();
    const int controller_start=140+int(genome.words.size())*6;
    const auto consistency=work_constant_consistency_program(false);
    const int consistency_start=controller_start+int(controller.size())*6;
    const auto one_consistency=work_constant_consistency_program(true);
    const int one_start=consistency_start+int(consistency.size())*6;
    const auto copy_consistency=work_bitwise_consistency_program(false);
    const int copy_start=one_start+int(one_consistency.size())*6;
    const auto flip_consistency=work_bitwise_consistency_program(true);
    const int flip_start=copy_start+int(copy_consistency.size())*6;
    const auto capture=feedback_capture_program();
    const int capture_start=flip_start+int(flip_consistency.size())*6;
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;p.stable_work_bits=20;
    p.layout.total_size=capture_start+int(capture.size())*6;
    Hamster h(94,p);
    auto write_word=[&](int& at,int word) {
        for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
    };
    int at=140;
    for(int word:genome.words)write_word(at,word);
    assert(at==controller_start);
    for(int word:controller)write_word(at,word);
    for(int word:consistency)write_word(at,word);
    for(int word:one_consistency)write_word(at,word);
    for(int word:copy_consistency)write_word(at,word);
    for(int word:flip_consistency)write_word(at,word);
    for(int word:capture)write_word(at,word);
    for(int i=80;i<98;++i)h.memory[i]=1;
    h.memory[98]=0;
    // Existing parser length markers for the L2 to L1 question format.
    for(int j=0;j<2;++j)for(int i=0;i<4;++i)h.memory[99+4*j+i]=(i<3);
    for(int i=0;i<4;++i)h.memory[120+i]=1;
    h.memory[125]=1;

    const std::array<std::vector<int>,4> fragments{{
        {0,0,14,31,14,24,4,3,0,2,14,17,9,3,14,19,3,1,15,0},
        {0,0,14,31,14,24,4,3,0,2,14,17,2,3,14,3,5,3,14,19,3,1,15,0},
        {0,2,14,17,3,4,15,0},
        {0,2,14,17,2,3,3,1,15,0}
    }};
    auto choose=[&](bool update,const std::array<bool,4>& keep) {
        Problem blank;h.write_prob(blank);
        for(int i=0;i<4;++i)h.memory[1+i]=keep[i];
        h.memory[5]=update;
        h.pro_1=controller_start;h.pro_2=consistency_start-1;h.step_limit=90;
        simulate_spiral_program(h);
        assert(!h.budget_exhausted&&!h.work_insert_blocked&&h.memory[125]);
        if(!h.written[51])return -1;
        assert(h.written[52]&&h.written[53]&&!h.memory[53]);
        return int(h.memory[51])*2+int(h.memory[52]);
    };
    auto trial=[&](int id,int data) {
        int answer=-1;
        bool correct=false;
        {
            FragmentTransaction tx(genome,fragments.at(id));
            int pos=140+genome.reserve_start*12;
            for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
                write_word(pos,genome.words[i]);
            auto q=elementary_problem(ElementaryTask::Flip,3,data);
            q.question[0]=SpiralToken(3,3,1);
            q.answer=SpiralToken(7-data,3,1);
            const auto bits=encode_layer_packet(3,3,data,3);
            h.write_prob(q);
            for(size_t i=0;i<bits.size();++i)h.memory[1+i]=bits[i];
            h.pro_1=140;h.pro_2=controller_start-1;h.step_limit=900;
            simulate_spiral_program(h);
            assert(!h.budget_exhausted&&!h.work_insert_blocked);
            for(int j=51;j<=54;++j)assert(h.written[j]);
            assert(!h.memory[54]);
            answer=4*int(h.memory[51])+2*int(h.memory[52])+int(h.memory[53]);
            assert(answer==predict_unary(static_cast<UnaryHypothesis>(id),data,3));
            correct=Check_ans(h,q);
            h.memory[40]=correct; // one-bit teacher feedback after the solver
            h.stop=false;h.executed_steps=0;
            h.pro_1=capture_start;h.pro_2=p.layout.total_size-1;h.step_limit=80;
            simulate_spiral_program(h); // no write_prob: original packet and answer remain
            assert(!h.budget_exhausted&&!h.work_insert_blocked);
            for(int j=108;j<=114;++j)assert(h.written[j]);
            for(int bit=2;bit>=0;--bit) {
                assert(h.memory[110-bit]==bool(answer&(1<<bit)));
                assert(h.memory[113-bit]==bool(data&(1<<bit)));
            }
            assert(h.memory[114]==correct);
        }
        // A failed trial is rolled back in the host transaction, including
        // the executable memory used by this particular guest instance.
        int pos=140+genome.reserve_start*12;
        for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
            write_word(pos,genome.words[i]);
        assert(genome.words==original_words);
        pos=140+genome.reserve_start*12;
        for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
            for(bool bit:SpiralToken(genome.words[i],5,1).bits)
                assert(h.memory.at(pos++)==bit);
        return std::pair<int,bool>{answer,correct};
    };
    std::array<bool,4> keep{{false,false,false,false}};
    const std::array<int,4> data{{0,0,1,2}};
    const std::array<int,4> expected_id{{0,1,1,1}};
    const std::array<int,4> expected_left{{2,2,1,1}};
    int wrong=0;
    for(int round=0;round<4;++round) {
        const int id=choose(round!=0,keep);
        assert(id==expected_id[round]);
        auto [answer,correct]=trial(id,data[round]);
        wrong+=!correct;
        Problem blank;h.write_prob(blank);
        for(int i=1;i<=7;++i)assert(!h.memory[i]); // predicates cannot use forwarded input
        h.pro_1=consistency_start;h.pro_2=one_start-1;h.step_limit=90;
        simulate_spiral_program(h);
        assert(!h.budget_exhausted&&h.written[51]);
        const bool guest_zero_keep=h.memory[51];
        h.write_prob(blank);
        for(int i=1;i<=7;++i)assert(!h.memory[i]);
        h.pro_1=one_start;h.pro_2=copy_start-1;h.step_limit=90;
        simulate_spiral_program(h);
        assert(!h.budget_exhausted&&h.written[51]);
        const bool guest_one_keep=h.memory[51];
        h.write_prob(blank);
        for(int i=1;i<=7;++i)assert(!h.memory[i]);
        h.pro_1=copy_start;h.pro_2=flip_start-1;h.step_limit=100;
        simulate_spiral_program(h);
        assert(!h.budget_exhausted&&h.written[55]);
        const bool guest_copy_keep=h.memory[55];
        h.write_prob(blank);
        for(int i=1;i<=7;++i)assert(!h.memory[i]);
        h.pro_1=flip_start;h.pro_2=capture_start-1;h.step_limit=110;
        simulate_spiral_program(h);
        assert(!h.budget_exhausted&&h.written[55]);
        const bool guest_flip_keep=h.memory[55];
        const std::array<bool,4> guest_keep{{guest_copy_keep,guest_flip_keep,
                                              guest_zero_keep,guest_one_keep}};
        for(int i=0;i<4;++i)
            assert(guest_keep[i]==bool((predict_unary(static_cast<UnaryHypothesis>(i),data[round],3)==answer)==correct));
        keep=guest_keep;
        if(round+1<4) {
            int left=0;
            for(int i=0;i<4;++i)left+=h.memory[120+i]&&keep[i];
            assert(left==expected_left[round]);
        }
    }
    assert(wrong==1);
    assert(choose(true,keep)==1);
    for(int i=0;i<4;++i)assert(h.memory[120+i]==(i==1));
    h.new_his();Hamster child(95,p);child.copy_hamu(h);h=std::move(child);
    assert(choose(false,{})==1);
    HamsterParams small=p;
    const int small_one=140+int(consistency.size())*6;
    small.layout.total_size=small_one+int(one_consistency.size())*6;
    Hamster predicate(96,small);
    int small_at=140;
    for(int word:consistency)
        for(bool bit:SpiralToken(word,5,1).bits)predicate.memory.at(small_at++)=bit;
    for(int word:one_consistency)
        for(bool bit:SpiralToken(word,5,1).bits)predicate.memory.at(small_at++)=bit;
    for(int answer=0;answer<8;++answer)for(int grade=0;grade<=1;++grade) {
        for(int check=0;check<2;++check) {
            Problem blank;predicate.write_prob(blank);
            for(int bit=2;bit>=0;--bit)predicate.memory[110-bit]=bool(answer&(1<<bit));
            predicate.memory[114]=grade;
            predicate.pro_1=check?small_one:140;
            predicate.pro_2=check?small.layout.total_size-1:small_one-1;
            predicate.step_limit=90;
            simulate_spiral_program(predicate);
            assert(!predicate.budget_exhausted&&predicate.written[51]);
            assert(predicate.memory[51]==bool((answer==(check?7:0))==bool(grade)));
        }
    }
    HamsterParams cp=p;
    const int small_flip=140+int(copy_consistency.size())*6;
    cp.layout.total_size=small_flip+int(flip_consistency.size())*6;
    Hamster checker(97,cp);int cat=140;
    for(int word:copy_consistency)
        for(bool bit:SpiralToken(word,5,1).bits)checker.memory.at(cat++)=bit;
    for(int word:flip_consistency)
        for(bool bit:SpiralToken(word,5,1).bits)checker.memory.at(cat++)=bit;
    for(int data_value=0;data_value<8;++data_value)
        for(int answer=0;answer<8;++answer)for(int grade=0;grade<=1;++grade) {
            for(int check=0;check<2;++check) {
                Problem blank;checker.write_prob(blank);
                for(int bit=2;bit>=0;--bit) {
                    checker.memory[110-bit]=bool(answer&(1<<bit));
                    checker.memory[113-bit]=bool(data_value&(1<<bit));
                }
                checker.memory[114]=grade;
                checker.pro_1=check?small_flip:140;
                checker.pro_2=check?cp.layout.total_size-1:small_flip-1;
                checker.step_limit=110;
                simulate_spiral_program(checker);
                assert(!checker.budget_exhausted&&checker.written[55]);
                assert(checker.memory[55]==bool(((answer^data_value)==(check?7:0))==bool(grade)));
            }
        }
    HamsterParams capture_params=p;
    capture_params.layout.total_size=140+int(capture.size())*6;
    Hamster capture_checker(99,capture_params);
    int capture_at=140;
    for(int word:capture)
        for(bool bit:SpiralToken(word,5,1).bits)
            capture_checker.memory.at(capture_at++)=bit;
    for(int operator_width=2;operator_width<=3;++operator_width)
        for(int data_width=2;data_width<=3;++data_width)
        for(int data_value=0;data_value<(1<<data_width);++data_value)
            for(int attempt=0;attempt<(1<<data_width);++attempt)
                for(int grade=0;grade<2;++grade) {
                auto q=elementary_problem(ElementaryTask::Flip,3,data_value);
                capture_checker.write_prob(q);
                // The position-specific width marker is stored in work.
                for(int j=0;j<4;++j)
                    capture_checker.memory[99+j]=(j<operator_width);
                const int data_record=99+operator_width+1;
                for(int j=0;j<4;++j)
                    capture_checker.memory[data_record+j]=(j<data_width);
                const auto packet=encode_layer_packet(operator_width==2?1:3,
                                                       operator_width,data_value,data_width);
                for(size_t j=0;j<packet.size();++j)
                    capture_checker.memory[1+j]=packet[j];
                for(int bit=data_width-1;bit>=0;--bit)
                    capture_checker.memory[51+data_width-1-bit]=bool(attempt&(1<<bit));
                capture_checker.memory[51+data_width]=0;
                capture_checker.memory[40]=grade;
                for(int j=0;j<4;++j)capture_checker.memory[120+j]=(j%2==0);
                const auto before=capture_checker.memory;
                capture_checker.pro_1=140;
                capture_checker.pro_2=capture_params.layout.total_size-1;
                capture_checker.step_limit=170;
                simulate_spiral_program(capture_checker);
                assert(!capture_checker.budget_exhausted&&!capture_checker.work_insert_blocked);
                for(int bit=2;bit>=0;--bit) {
                    assert(capture_checker.memory[110-bit]==bool(attempt&(1<<bit)));
                    assert(capture_checker.memory[113-bit]==bool(data_value&(1<<bit)));
                }
                assert(capture_checker.memory[114]==bool(grade));
                for(int j=0;j<45;++j)assert(capture_checker.memory[j]==before[j]);
                for(int j=50;j<55;++j)assert(capture_checker.memory[j]==before[j]);
                for(int j=120;j<124;++j)assert(capture_checker.memory[j]==before[j]);
            }
    std::cout<<"PASS one hamster: VM choice -> host trial -> VM answer -> four guest checks; "
                "direct work checks; IDs 0,1,1,1; FLIP inherited; 288 predicates, 320 captures\n";
}
