#include "../src/tree_observed_learner.hpp"
#include <cassert>
#include <iostream>

int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=700;p.layout.total_size=24000;p.stable_work_bits=100;p.tree_start=600;p.tree_capacity=8;p.layout.val_reg_size=12;
    const std::vector<int> partial={16,1,0,2,3,1,15,0},extra={16,1,0,2,3,4,15,0},loop={16,1,12,20,12,4};
    auto run=[&](Hamster& h,const std::vector<int>& words,int budget=4000){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);h.val_ptr=0;
        h.stop=false;h.budget_exhausted=false;h.executed_steps=0;h.step_limit=budget;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;simulate_spiral_program(h);
        if(budget==4000)assert(h.stop&&!h.budget_exhausted);
    };
    auto runner=[&](Hamster& h,const std::vector<int>& words){run(h,words,words==loop?64:4000);};
    auto question=[&](Hamster& h,int width,int op,int data){
        std::fill(h.memory.begin(),h.memory.begin()+45,false);h.memory[1]=true;
        for(int b=0;b<4;++b)h.memory[2+b]=SpiralToken(1,3,1).bits[b];
        for(int b=0;b<width+1;++b)h.memory[6+b]=SpiralToken(op,width,1).bits[b];
        for(int b=0;b<4;++b)h.memory[7+width+b]=SpiralToken(data,3,1).bits[b];
    };
    auto bits=[](int v){return std::array<bool,3>{bool(v&4),bool(v&2),bool(v&1)};};
    // New behavior absent from the old four prediction formulas: toggle only
    // the last data bit. READ(input+1) supplies 1, XOR affects output+2.
    auto xor_one=tree_width_trial_program(false);xor_one.resize(xor_one.size()-2);
    const std::vector<int> toggle={0,0,14,17,4,1,0,2,14,18,5,1,15,0};
    xor_one.insert(xor_one.end(),toggle.begin(),toggle.end());
    std::array<std::vector<int>,4> code={tree_four_trial_program(2),xor_one,tree_four_trial_program(0),tree_four_trial_program(1)};
    TreeObservedLearner learner(1,p,code);auto& h=learner.hamster;
    code[1]=tree_four_trial_program(2);assert(learner.fragments[1]==xor_one); // copied immutable catalogue
    for(int width:{2,3})for(int data=0;data<8;++data){
        question(h,width,1,data);runner(h,tree_width_prepare_program());
        const auto memory=h.memory,written=h.written;
        for(int id=0;id<4;++id){
            auto o=observe_tree_fragment(h,learner.fragments[id],runner);
            const int expected=id==0?0:id==1?data^1:id==2?data:data^7;
            assert(o.valid&&o.answer==bits(expected)&&o.steps>0);
            assert(h.memory==memory&&h.written==written);
        }
    }
    // Invalid programs cannot change the source learner, including tree/work.
    TreeFourCode write_work;write_work.e(16,1);write_work.at(3,0);write_work.e(2,1);write_work.append(tree_four_trial_program(2));
    TreeFourCode read_work;read_work.e(16,1);read_work.at(3,55);read_work.e(4,1);read_work.append(tree_four_trial_program(2));
    TreeFourCode read_grade;read_grade.e(16,1);read_grade.at(0,40);read_grade.e(4,1);read_grade.append(tree_four_trial_program(2));
    const auto source=h.memory;
    for(const auto& bad:{partial,extra,loop,write_work.w,read_work.w,read_grade.w}){
        assert(!observe_tree_fragment(h,bad,runner).valid);assert(h.memory==source);
    }
    h=Hamster(2,p);
    auto turn=[&](int width,int op,int data,int expected){question(h,width,op,data);return run_tree_observed_learning_turn(learner,bits(expected),runner);};
    auto masks=[&](int slot){int value=0;for(int j=0;j<4;++j)if(h.memory[80+tree_four_mask(slot)+j])value|=1<<j;return value;};
    auto t=turn(2,1,0,1);assert(t&&!t->learning.correct&&masks(57)==10);
    assert((t->prediction_valid==std::array<bool,4>{true,true,true,true}));
    t=turn(2,1,2,3);assert(t&&t->learning.candidate==1&&t->learning.confirmed&&!h.memory[127]);
    assert((t->prediction_valid==std::array<bool,4>{false,true,false,true}));
    assert(t->prediction_steps[0]==0&&t->prediction_steps[2]==0);
    t=turn(2,2,0,0);assert(t&&t->learning.correct&&!t->learning.confirmed&&masks(57)==5);
    t=turn(2,2,3,3);assert(t&&!t->learning.correct&&masks(57)==4);
    t=turn(2,2,5,5);assert(t&&t->learning.candidate==2&&t->learning.confirmed);
    assert((t->prediction_valid==std::array<bool,4>{false,false,true,false}));
    t=turn(2,3,0,7);assert(t&&!t->learning.correct&&masks(57)==10);
    t=turn(2,3,3,4);assert(t&&t->learning.candidate==1&&!t->learning.correct&&masks(57)==8);
    t=turn(2,3,4,3);assert(t&&t->learning.candidate==3&&t->learning.confirmed);
    TreeObservedLearner n2_child(learner,3);assert(n2_child.fragments==learner.fragments);
    t=turn(3,1,0,0);assert(t&&!t->learning.confirmed);
    t=turn(3,1,5,0);assert(t&&t->learning.candidate==0&&t->learning.confirmed);
    auto answer=[&](TreeObservedLearner& who,int width,int op,int data,int id,int expected){
        question(who.hamster,width,op,data);auto selected=run_tree_observed_route(who,runner);
        assert(selected&&*selected==id);
        for(int b=0;b<3;++b){assert(who.hamster.written[50+b]);assert(who.hamster.memory[50+b]==bits(expected)[b]);}
        for(int pos=53;pos<80;++pos)assert(!who.hamster.written[pos]);
    };
    for(int data=0;data<8;++data){
        answer(n2_child,2,1,data,1,data^1);answer(n2_child,2,2,data,2,data);answer(n2_child,2,3,data,3,data^7);
        answer(learner,3,1,data,0,0);
    }
    TreeObservedLearner child(learner,4);
    for(int data=0;data<8;++data)answer(child,3,1,data,0,0);

    // Failed hypothetical executions remain unknown, including stale answers.
    const std::array<std::vector<int>,4> broken={tree_four_trial_program(2),partial,extra,loop};
    TreeObservedLearner uncertain(5,p,broken);question(uncertain.hamster,2,1,5);
    auto u=run_tree_observed_learning_turn(uncertain,bits(0),runner);
    assert(u&&u->learning.valid&&u->learning.correct&&!u->learning.confirmed);
    assert((u->prediction_valid==std::array<bool,4>{true,false,false,false}));
    for(int j=0;j<4;++j)assert(uncertain.hamster.memory[80+tree_four_mask(57)+j]);
    const Hamster observed=uncertain.hamster;
    // Context batch is independently bound to snapshot data and attempt.
    uncertain.hamster.memory[80+147]=!uncertain.hamster.memory[80+147];
    runner(uncertain.hamster,tree_observed_feedback_program(57));
    assert(!uncertain.hamster.memory[80+94]);
    for(int j=0;j<4;++j)assert(uncertain.hamster.memory[80+tree_four_mask(57)+j]);
    uncertain.hamster=observed;
    // A fixture with earlier-eliminated alternatives isolates completion guard.
    for(int j=1;j<4;++j)uncertain.hamster.memory[80+tree_four_mask(57)+j]=false;
    const Hamster singleton=uncertain.hamster;
    const auto feedback=tree_observed_feedback_program(57);runner(uncertain.hamster,feedback);const int steps=uncertain.hamster.executed_steps;
    uncertain.hamster=singleton;run(uncertain.hamster,feedback,steps-2);
    assert(uncertain.hamster.budget_exhausted&&!uncertain.hamster.memory[80+94]);
    runner(uncertain.hamster,tree_observed_confirm_program(57));assert(!uncertain.hamster.memory[80+57]);
    runner(uncertain.hamster,feedback);runner(uncertain.hamster,tree_observed_confirm_program(57));runner(uncertain.hamster,tree_observed_bind_program(57));
    assert(uncertain.hamster.memory[80+57]);
    // A corrupt index pointing at a partial program cannot emit a stale answer.
    const int action=600+72+6;uncertain.hamster.memory[action+1]=true;uncertain.hamster.memory[action+2]=false;
    question(uncertain.hamster,2,1,3);assert(!run_tree_observed_route(uncertain,runner));
    for(int pos=50;pos<80;++pos)assert(!uncertain.hamster.written[pos]);
    const std::array<std::vector<int>,4> selected_bad={partial,learner.fragments[1],learner.fragments[2],learner.fragments[3]};
    TreeObservedLearner invalid(6,p,selected_bad);question(invalid.hamster,2,1,5);
    auto rejected=run_tree_observed_learning_turn(invalid,bits(5),runner);
    assert(rejected&&!rejected->learning.valid&&!invalid.hamster.memory[80+140]);
    for(int j=0;j<4;++j)assert(invalid.hamster.memory[80+tree_four_mask(57)+j]);
    // Opt-in recovery uses actual observations, without discarding the partial
    // fragment as a semantic hypothesis. First XOR1 fails, then COPY succeeds.
    question(invalid.hamster,2,1,5);
    auto recovered=run_tree_observed_learning_turn(invalid,bits(5),runner,true);
    assert(recovered&&recovered->recovered&&recovered->learning.candidate==1);
    assert(recovered->learning.valid&&!recovered->learning.correct);
    assert(invalid.hamster.memory[80+tree_four_mask(57)]);
    assert(!invalid.hamster.memory[80+tree_four_mask(57)+1]);
    question(invalid.hamster,2,1,5);
    recovered=run_tree_observed_learning_turn(invalid,bits(5),runner,true);
    assert(recovered&&recovered->recovered&&recovered->learning.candidate==2);
    assert(recovered->learning.correct&&!recovered->learning.confirmed);
    assert(invalid.hamster.memory[80+tree_four_mask(57)]);
    assert(invalid.hamster.memory[80+tree_four_mask(57)+2]);
    assert(recovered->prediction_steps[1]==0);
    TreeObservedLearner all_bad(7,p,{partial,extra,loop,partial});
    question(all_bad.hamster,2,1,5);
    auto none=run_tree_observed_learning_turn(all_bad,bits(5),runner,true);
    assert(none&&!none->learning.valid&&!none->recovered&&!all_bad.hamster.memory[80+140]);
    for(int j=0;j<4;++j)assert(all_bad.hamster.memory[80+tree_four_mask(57)+j]);
    TreeObservedLearner interrupted(8,p,selected_bad);question(interrupted.hamster,2,1,5);
    const auto recovery_code=tree_observed_recover_choice_program(57);
    auto interrupt_runner=[&](Hamster& who,const std::vector<int>& words){
        if(words==recovery_code)run(who,words,2);else runner(who,words);
    };
    assert(!run_tree_observed_learning_turn(interrupted,bits(5),interrupt_runner,true));
    assert(!interrupted.hamster.memory[80+140]);
    for(int j=0;j<4;++j)assert(interrupted.hamster.memory[80+tree_four_mask(57)+j]);
    for(int pos=50;pos<80;++pos)assert(!interrupted.hamster.written[pos]);
    std::cout<<"PASS observed fragments: 64 isolated observations, shuffled XOR1 catalogue, 40 routed answers, invalid evidence and recovery\n";
}
