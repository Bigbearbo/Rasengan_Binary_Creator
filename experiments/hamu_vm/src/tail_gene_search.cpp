#include "growth_genome.hpp"
#include "math_questions.hpp"
#include "layer_packet.hpp"
#include <iostream>
#include <random>

// Focused experiment: the protected core is inherited, while one parameter
// in the 64-pair reserve evolves. The teacher enters this reserve for COPY.
// This is not a claim that the core learned to call a new subroutine.
static GrowthGenome candidate(int offset) {
    auto g=growth_genome();
    const int op[][2]={{0,0},{14,31},{14,offset},{4,4},
                       {0,2},{14,17},{9,4},{15,0}};
    for(int i=0;i<8;++i)
        write_gene_pair(g,g.fixed_pairs+i,op[i][0],op[i][1]);
    return g;
}

static int fitness(int offset) {
    auto g=candidate(offset);
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;
    p.layout.total_size=p.layout.program_start+int(g.words.size())*6;
    Hamster donor(0,p);int at=p.layout.program_start;
    for(int word:g.words)
        for(bool bit:SpiralToken(word,5,1).bits)donor.memory.at(at++)=bit;
    donor.new_his();Hamster child(1,p);child.copy_hamu(donor);
    const int gene=p.layout.program_start+g.fixed_pairs*12;
    int passed=0;
    for(int v=0;v<8;++v) {
        auto q=elementary_problem_with_operator_order(ElementaryTask::Copy,2,3,v);
        auto bits=encode_layer_packet(0,2,v,3);
        child.write_prob(q);
        for(size_t j=0;j<bits.size();++j)child.memory[p.layout.input_start+1+j]=bits[j];
        child.pro_1=gene;child.pro_2=gene+8*12-1;child.step_limit=20;
        simulate_spiral_program(child);
        passed+=!child.budget_exhausted &&
                child.read_seen[p.layout.input_start+22] && Check_ans(child,q);
    }
    return passed;
}

int main() {
    if(fitness(16)!=0||fitness(23)!=8)return 1;
    std::mt19937 rng(20261027);
    int best=16,score=0,attempts=0;
    // Preserve the best and sample mutated descendants; random migrants
    // avoid a flat score trapping one lineage. All candidates are VM guests.
    for(int generation=1;generation<=15;++generation) {
        for(int i=0;i<24;++i) {
            int child=best;
            if(i%6==0)child=16+int(rng()%16);
            else {
                const int flips=1+int(rng()%3);
                for(int j=0;j<flips;++j)child^=1<<int(rng()%4);
            }
            const int s=fitness(child);++attempts;
            if(s>score) {best=child;score=s;}
            if(score==8) {
                std::cout<<"PASS reserve COPY: seed=20261027 generation="<<generation
                         <<" attempts="<<attempts<<" offset_param="<<best
                         <<" COPY="<<score<<"/8; protected core unchanged\n";
                return 0;
            }
        }
    }
    std::cerr<<"FAIL reserve COPY best="<<score<<"/8 parameter="<<best<<'\n';
    return 2;
}
