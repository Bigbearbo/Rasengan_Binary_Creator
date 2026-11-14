#include "../src/next_carry_program.hpp"
#include "../src/layer_packet.hpp"
#include "../src/math_questions.hpp"
#include <iostream>

int main() {
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;
    int passed=0;
    for(int n:{2,3}) {
        const auto code=next_carry_program(n,3);
        p.layout.total_size=p.layout.program_start+int(code.size())*6;
        for(int value=0;value<(1<<n)-1;++value) {
            Hamster h(0,p);int at=p.layout.program_start;
            for(int w:code)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
            const auto q=elementary_problem_with_operator_order(ElementaryTask::Next,3,n,value);
            h.write_prob(q);
            const auto bits=encode_layer_packet(2,3,value,n);
            for(size_t j=0;j<bits.size();++j)h.memory[p.layout.input_start+1+j]=bits[j];
            h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=150;
            simulate_spiral_program(h);
            if(h.budget_exhausted||!Check_ans(h,q)) {
                std::cerr<<"FAIL n="<<n<<" value="<<value<<" out=";
                for(int j=0;j<n+1;++j)std::cerr<<h.memory[p.layout.output_start+1+j];
                std::cerr<<'\n';return 1;
            }
            ++passed;
        }
    }
    if(passed!=10)return 2;
    std::cout<<"PASS 2/3-bit NEXT VM circuit 10/10, including 011->100 carry\n";
}
