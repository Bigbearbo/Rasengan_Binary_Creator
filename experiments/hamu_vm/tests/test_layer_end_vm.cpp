#include "../src/layer_packet.hpp"
#include <iostream>

static std::vector<int> end_word_detector() {
    std::vector<int> c;
    auto emit=[&](int op,int param){c.push_back(op);c.push_back(param);};
    emit(16,1); // immediate branching
    emit(0,0);emit(14,30); // input_start+14: END_L2 after 001 + two L2 words
    for(int expected:{1,1,1,0,0}) {
        emit(4,1);
        if(expected) {
            emit(24,2); // one skips the stop, zero stops
            emit(15,0);
        } else {
            emit(24,2); // one jumps to stop
            emit(26,2); // zero skips stop
            emit(15,0);
        }
        emit(14,17); // next bit
    }
    emit(0,3);emit(2,1);emit(15,0); // mark accepted layer transition
    return c;
}

int main() {
    const auto code=end_word_detector();
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;
    p.layout.total_size=p.layout.program_start+int(code.size())*6;
    auto run=[&](int word) {
        Hamster h(0,p);int at=p.layout.program_start;
        for(int w:code)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
        Problem q;q.type=ProblemType::EAZY;
        h.write_prob(q);
        auto bits=encode_layer_packet(1,3,5,3);
        auto replacement=SpiralToken(word,3,2).bits;
        for(int i=0;i<5;++i)bits[13+i]=replacement[i];
        for(size_t j=0;j<bits.size();++j)h.memory[p.layout.input_start+1+j]=bits[j];
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=70;
        simulate_spiral_program(h);
        if(h.budget_exhausted)return false;
        if(h.memory[p.layout.work_start]!=(word==7))return false;
        if(word==7)for(int i=14;i<=18;++i)
            if(!h.read_seen[p.layout.input_start+i])return false;
        return true;
    };
    if(!run(7)||!run(6)||!run(1))return 1; // END, QUESTION, MATH
    std::cout<<"PASS VM reads five L2 end bits; END changes layer flag,"
                " QUESTION and MATH do not\n";
}
