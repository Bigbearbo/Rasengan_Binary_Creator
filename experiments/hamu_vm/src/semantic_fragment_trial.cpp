#include "feedback_learner.hpp"
#include "fragment_transaction.hpp"
#include "layer_packet.hpp"
#include "math_questions.hpp"
#include <iostream>
int main() {
    auto genome=integrated_zero_program(15);
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;
    p.layout.total_size=140+int(genome.words.size())*6;
    Hamster h(51,p);int at=140;
    for(int w:genome.words)for(bool bit:SpiralToken(w,5,1).bits)h.memory.at(at++)=bit;
    int pos=80;for(int i=0;i<18;++i)h.memory[pos++]=1;h.memory[pos++]=0;
    for(int j=0;j<2;++j)for(bool bit:{true,true,true,false})h.memory[pos++]=bit;
    const std::vector<std::vector<int>> fragments={
        {0,0,14,31,14,24,4,3,0,2,14,17,9,3,14,19,3,1,15,0}, // COPY
        {0,0,14,31,14,24,4,3,0,2,14,17,2,3,14,3,5,3,14,19,3,1,15,0}, // FLIP
        {0,2,14,17,3,4,15,0}, // ZERO
        {0,2,14,17,2,3,3,1,15,0} // ONE
    };
    FeedbackLearner learner;
    int trials=0;
    for(int data:{0,1,2}) {
        bool solved=false;
        for(int attempt=0;attempt<4&&!solved;++attempt) {
            int hypothesis=-1;
            for(int id=0;id<4;++id)if(learner.possible[id]){hypothesis=id;break;}
            if(hypothesis<0)return 1;
            FragmentTransaction tx(genome,fragments.at(hypothesis));
            at=140+genome.reserve_start*12;
            for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
                for(bool bit:SpiralToken(genome.words[i],5,1).bits)h.memory.at(at++)=bit;
            auto q=elementary_problem(ElementaryTask::Flip,3,data);
            q.question[0]=SpiralToken(3,3,1);q.answer=SpiralToken(7-data,3,1);
            const auto bits=encode_layer_packet(3,3,data,3);
            h.write_prob(q);
            for(size_t i=0;i<bits.size();++i)h.memory[1+i]=bits[i];
            h.pro_1=140;h.pro_2=p.layout.total_size-1;h.step_limit=900;
            simulate_spiral_program(h);
            solved=!h.budget_exhausted&&Check_ans(h,q);
            const int answer=predict_unary(static_cast<UnaryHypothesis>(hypothesis),data,3);
            int actual=0;
            for(int j=51;j<=53;++j) {
                if(!h.written[j])return 5;
                actual=2*actual+h.memory[j];
            }
            if(!h.written[54]||h.memory[54]||actual!=answer)return 6;
            learner.observe(data,3,answer,solved);
            ++trials;
            std::cout<<"data="<<data<<" candidate="<<hypothesis<<" correct="<<solved<<'\n';
        }
        if(!solved)return 2;
        if(data==0&&learner.remaining()!=2)return 3;
    }
    if(learner.remaining()!=1||!learner.possible[1])return 4;
    int checked=0;
    for(int hypothesis=0;hypothesis<4;++hypothesis)for(int data:{1,2}) {
        FragmentTransaction tx(genome,fragments.at(hypothesis));
        at=140+genome.reserve_start*12;
        for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
            for(bool bit:SpiralToken(genome.words[i],5,1).bits)h.memory.at(at++)=bit;
        const int expected=predict_unary(static_cast<UnaryHypothesis>(hypothesis),data,3);
        auto q=elementary_problem(ElementaryTask::Copy,3,data);
        q.question[0]=SpiralToken(3,3,1);q.answer=SpiralToken(expected,3,1);
        const auto bits=encode_layer_packet(3,3,data,3);
        h.write_prob(q);
        for(size_t i=0;i<bits.size();++i)h.memory[1+i]=bits[i];
        h.pro_1=140;h.pro_2=p.layout.total_size-1;h.step_limit=900;
        simulate_spiral_program(h);
        if(h.budget_exhausted||!Check_ans(h,q))return 7;
        for(int j=51;j<=54;++j)if(!h.written[j])return 8;
        ++checked;
    }
    if(checked!=8)return 9;
    std::cout<<"PASS VM fragment answers with binary teacher grades; trials="<<trials<<'\n';
    std::cout<<"PASS four candidate fragments across two data values: "<<checked<<" exact answers\n";
}
