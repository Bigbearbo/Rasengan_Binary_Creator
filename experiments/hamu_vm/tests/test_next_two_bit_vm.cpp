#include "../src/next_two_bit_program.hpp"
#include "../src/layer_packet.hpp"
#include "../src/math_questions.hpp"
#include <iostream>

int main() {
    const auto code=next_two_bit_program();
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;
    p.layout.total_size=p.layout.program_start+int(code.size())*6;
    for(int value=0;value<3;++value) {
        Hamster h(0,p);int at=p.layout.program_start;
        for(int w:code)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
        const auto q=elementary_problem(ElementaryTask::Next,2,value);
        h.write_prob(q);
        const auto bits=encode_layer_packet(2,2,value,2);
        for(size_t j=0;j<bits.size();++j)h.memory[p.layout.input_start+1+j]=bits[j];
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=75;
        simulate_spiral_program(h);
        if(h.budget_exhausted||!Check_ans(h,q)||
           !h.read_seen[p.layout.input_start+22]||
           !h.read_seen[p.layout.input_start+23]) {
            std::cerr<<"FAIL NEXT "<<value<<" output=";
            for(int j=0;j<3;++j)std::cerr<<h.memory[p.layout.output_start+1+j];
            std::cerr<<'\n';return 1;
        }
    }
    std::cout<<"PASS VM two-bit NEXT: 00->01, 01->10 carry, 10->11\n";
}
