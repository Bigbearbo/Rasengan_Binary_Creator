// Narrow search experiment: the complete routing skeleton is provided.
// Only the opcode at word 8 mutates; this does not test discovery of a program.
#include "hamu_vm_core.hpp"
#include <array>
#include <iostream>
#include <random>

static int score(int candidate) {
    HamsterParams p; p.layout.total_size=256;
    const std::array<int,17> program={0,3,4,1,0,2,16,1,candidate,30,3,1,15,0,2,1,15};
    int correct=0;
    for(int bit=0;bit<2;++bit) {
        Hamster h(0,p);
        Problem question;question.type=ProblemType::EAZY;
        question.question={SpiralToken(0,2,1),SpiralToken(bit,2,1)};
        question.answer=SpiralToken(bit,2,1);
        h.write_prob(question);
        h.memory[p.layout.work_start]=bit;
        int at=p.layout.program_start;
        for(int op:program) for(bool b:SpiralToken(op,5,1).bits)h.memory.at(at++)=b;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;
        h.step_limit=32;
        simulate_spiral_program(h);
        correct += h.written[p.layout.output_start] &&
                   h.memory[p.layout.output_start]==static_cast<bool>(bit) &&
                   !h.budget_exhausted;
    }
    return correct;
}

int main() {
    for(unsigned seed=1;seed<=5;++seed) {
        std::mt19937 rng(seed);
        int best=16, first=-1;
        if(score(best)!=1) return 1;
        for(int generation=1;generation<=12 && first<0;++generation) {
            for(int child=0;child<16;++child) {
                const int candidate=best ^ (1u<<(rng()%5));
                const int result=score(candidate);
                if(result>score(best))best=candidate;
                if(result==2) {first=generation;break;}
            }
        }
        std::cout<<"seed="<<seed<<" initial=1/2 first_full_generation="<<first
                 <<" opcode="<<best<<"\n";
        if(first<0||best!=17)return 1;
    }
}
