// Controlled adaptation: old COPY routine is locked; only parameters of the
// Branch opcode and appended routine parameters can mutate; layout is fixed.
#include "hamu_vm_core.hpp"
#include <array>
#include <iostream>
#include <random>

using Routine=std::array<int,11>;
static constexpr Routine old_code={14,20,4,3,0,2,14,17,9,3,15};
static constexpr std::array<int,10> dispatcher={0,1,14,1,4,1,16,1,18,31};
static constexpr std::array<int,2> reset_input={0,0};
static constexpr int mutable_words[]={1,3,9};

static Problem copy_problem(int n,int value) {
    Problem p;p.type=ProblemType::EAZY;
    p.question={SpiralToken(0,n,1),SpiralToken(value,n,1)};
    p.answer=SpiralToken(value,n,1);
    return p;
}

template<size_t N> static void append_code(Hamster& h,const std::array<int,N>& code,int at) {
    for(int op:code)for(bool bit:SpiralToken(op,5,1).bits)h.memory.at(at++)=bit;
}

struct Metrics {int old_exact=0,new_exact=0,new_bits=0,new_reads=0;};
static Metrics evaluate(const Routine& new_code,int branch_opcode) {
    HamsterParams p;p.op_order=5;p.layout.total_size=p.layout.program_start+10*6;
    Hamster donor(0,p);
    const int first=p.layout.program_start,second=first+25*6;
    auto prefix=dispatcher;prefix[8]=branch_opcode;
    append_code(donor,prefix,first);
    donor.extend_program_capacity(36);
    append_code(donor,reset_input,first+10*6);
    append_code(donor,old_code,first+12*6);
    append_code(donor,reset_input,first+23*6);
    append_code(donor,new_code,second);
    donor.new_his();
    Hamster archive(1,p);archive.copy_hamu(donor);
    Hamster child(2,p);child.copy_hamu(archive);
    Metrics m;
    for(int version=0;version<2;++version) {
        const int n=version?3:2;
        for(int value=0;value<(1<<n);++value) {
            const Problem q=copy_problem(n,value);
            child.write_prob(q,version);
            child.pro_1=first;
            child.pro_2=first+36*6-1;
            simulate_spiral_program(child);
            if(version) {
                m.new_exact+=Check_ans(child,q);
                for(int i=0;i<4;++i) {
                    const int out=p.layout.output_start+1+i;
                    m.new_bits+=child.written[out] && child.memory[out]==q.answer.bits[i];
                    m.new_reads+=child.read_seen[1+4+i];
                }
            } else m.old_exact+=Check_ans(child,q);
        }
    }
    return m;
}
static int fitness(const Metrics& m) {
    return 100*m.new_exact+m.new_bits+m.new_reads;
}

int main() {
    for(unsigned seed=1;seed<=5;++seed) {
        std::mt19937 rng(seed);
        const auto initial=evaluate(old_code,16);
        const auto branch_only=evaluate(old_code,18);
        if(seed==1)std::cout<<"baseline_fitness="<<fitness(initial)
                            <<" branch_only_fitness="<<fitness(branch_only)
                            <<" baseline_bits="<<initial.new_bits
                            <<" branch_bits="<<branch_only.new_bits<<"\n";
        if(initial.old_exact!=4) return 1;
        // Keep a separate candidate for every observed opcode. This prevents
        // a neutral but useful branch from being discarded by a competing one.
        std::array<Routine,32> population{};
        std::array<int,32> scores{};scores.fill(-1);
        population[16]=old_code;scores[16]=fitness(initial);
        int generation=-1,first_branch=-1;
        for(int gen=1;gen<=100 && generation<0;++gen) {
            for(int child=0;child<64;++child) {
                std::vector<int> parents;
                for(int op=0;op<32;++op)if(scores[op]>=0)parents.push_back(op);
                const int parent=parents[rng()%parents.size()];
                Routine candidate=population[parent];
                int branch=parent;
                if(rng()%4==0)branch^=1u<<(rng()%5);
                else {
                    const int word=mutable_words[rng()%3];
                    const int flips=1+rng()%3;
                    for(int i=0;i<flips;++i)candidate[word]^=1u<<(rng()%5);
                }
                // Controlled search only over the adjacent layout/count choices.
                if ((candidate[1]!=20 && candidate[1]!=21) ||
                    (candidate[3]!=3 && candidate[3]!=4) ||
                    (candidate[9]!=3 && candidate[9]!=4))continue;
                const auto result=evaluate(candidate,branch);
                if(result.old_exact!=4)continue;
                const int value=fitness(result);
                if(value>scores[branch] || (value==scores[branch] && rng()%4==0)) {
                    population[branch]=candidate;scores[branch]=value;
                    if(branch==18 && first_branch<0)first_branch=gen;
                }
                if(result.new_exact==8 && branch==18) {generation=gen;break;}
            }
        }
        const auto final=scores[18]>=0?evaluate(population[18],18):initial;
        std::cout<<"seed="<<seed<<" initial_old="<<initial.old_exact<<"/4"
                 <<" initial_new="<<initial.new_exact<<"/8 generation="<<generation
                 <<" final_old="<<final.old_exact<<"/4 final_new="<<final.new_exact<<"/8"
                 <<" first_branch="<<first_branch<<" branch_opcode="<<(scores[18]>=0?18:16)
                 <<" new_parameters="<<population[18][1]<<","<<population[18][3]<<","<<population[18][9]<<"\n";
        if(generation<0||final.old_exact!=4||final.new_exact!=8)return 3;
    }
}
