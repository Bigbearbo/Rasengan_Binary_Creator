#include "../src/layer_packet.hpp"
#include "../src/promoting_flip_program.hpp"
#include "../src/math_questions.hpp"
#include <iostream>

int main() {
    const auto code=promoting_flip_program(true);
    HamsterParams p;p.op_order=5;p.layout.status_start=45;
    p.layout.output_start=50;p.layout.work_start=80;p.layout.program_start=140;
    p.layout.total_size=p.layout.program_start+int(code.size())*6;
    Hamster h(0,p);int at=p.layout.program_start;
    for(int w:code)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
    int solved=0;
    for(int n:{2,3})for(int value=0;value<(1<<n);++value)
        for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip}) {
            const int op=task==ElementaryTask::Copy?0:1;
            const auto bits=encode_layer_packet(op,n,value,n);
            const auto parsed=parse_layer_packet(bits,n,n); // host-side oracle
            if(parsed.operator_id!=op||parsed.data_value!=value)return 1;
            const auto q=elementary_problem_with_operator_order(task,n,n,value);
            h.write_prob(q);
            for(size_t j=0;j<bits.size();++j)h.memory.at(p.layout.input_start+1+j)=bits[j];
            int pos=p.layout.work_start;
            for(int j=0;j<18;++j)h.memory[pos++]=1;
            h.memory[pos++]=0;
            for(int word=0;word<2;++word) {
                for(int j=0;j<n;++j)h.memory[pos++]=1;
                h.memory[pos++]=0;
            }
            h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=420;
            simulate_spiral_program(h);
            if(h.budget_exhausted||h.work_insert_blocked||!Check_ans(h,q)) {
                std::cerr<<"FAIL layer VM n="<<n<<" value="<<value
                         <<" op="<<op<<" steps="<<h.executed_steps<<'\n';return 2;
            }
            for(int j=0;j<18;++j)
                if(!h.read_seen[p.layout.input_start+1+j])return 3;
            ++solved;
        }
    if(solved!=24)return 4;
    std::cout<<"PASS VM reads all 18 L2 prefix bits and solves 24 L1 COPY/FLIP"
                " questions using supplied unary prefix length\n";
}
