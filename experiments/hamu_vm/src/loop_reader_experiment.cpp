#include "task_upgrade.hpp"
#include <iostream>
#include <stdexcept>

// Reference brain for translating two bit-at-a-time loops into VM opcodes.
// The only persistent state is three unary lengths in writable work memory.
struct LoopReader {
    Hamster& h;
    const int work, input, output;
    explicit LoopReader(Hamster& hamster):h(hamster),work(h.params.layout.work_start),
        input(h.params.layout.input_start+1),output(h.params.layout.output_start+1) {}

    void initialize() {
        // startup: 01 (two raw bits); operator: n=2,k=1; data: n=2,k=1.
        for(int base:{work,work+5,work+10}) {
            h.memory.at(base)=1;h.memory.at(base+1)=1;h.memory.at(base+2)=0;
        }
    }
    int length(int base) const {
        for(int n=0;n<=4;++n)if(!h.memory.at(base+n))return n;
        throw std::runtime_error("unary length exceeded reserved slot");
    }
    bool read_bit(int& cursor) {
        if(cursor>=h.params.layout.status_start)throw std::runtime_error("input overrun");
        h.read_seen.at(cursor)=true;
        return h.memory.at(cursor++);
    }
    int skip_word(int cursor,int base,int tail_bits) {
        const int n=length(base);
        for(int i=0;i<n+tail_bits;++i)(void)read_bit(cursor);
        return cursor;
    }
    bool answer() {
        int cursor=input;
        cursor=skip_word(cursor,work,0);       // 01 startup
        cursor=skip_word(cursor,work+5,1);     // COPY word
        const int n=length(work+10);
        int bits=0;
        // Answer loop: one input bit, then one output bit per iteration.
        for(int i=0;i<n;++i) {
            const bool bit=read_bit(cursor);
            h.memory.at(output+bits)=bit;h.written.at(output+bits++)=true;
        }
        const bool expected_tail=read_bit(cursor);
        if(expected_tail && n==2) {
            // The old tail has become information; extend just this word.
            h.memory.at(work+10+2)=1;
            h.memory.at(work+10+3)=0;
            h.memory.at(output+bits)=1;h.written.at(output+bits++)=true;
            const bool new_tail=read_bit(cursor);
            if(new_tail)throw std::runtime_error("new tail must be zero");
            h.memory.at(output+bits)=0;h.written.at(output+bits++)=true;
        } else {
            if(expected_tail)throw std::runtime_error("unexpected tail");
            h.memory.at(output+bits)=0;h.written.at(output+bits++)=true;
        }
        return n==2 && expected_tail;
    }
};

int main() {
    HamsterParams p;
    Hamster h(0,p);LoopReader brain(h);brain.initialize();
    CopyUpgradeCurriculum teacher(4,6);
    int promotions=0,even_after_upgrade=0;
    for(int i=0;i<26;++i) {
        Problem q=teacher.next();
        h.write_prob(q);
        const int payload=p.layout.input_start+1;
        const int payload_bits=3+int(q.question[1].bits.size());
        for(int j=payload_bits-1;j>=0;--j)h.memory.at(payload+j+2)=h.memory.at(payload+j);
        h.memory.at(payload)=0;h.memory.at(payload+1)=1; // 01 startup
        const bool grew=brain.answer();
        promotions+=grew;
        if(i>=10 && !h.memory[p.layout.input_start+1+2+3+2])++even_after_upgrade;
        if(grew!=(i==4) || brain.length(p.layout.work_start+10)!=(i<4?2:3) ||
           !Check_ans(h,q)) {
            std::cerr<<"FAIL question="<<i<<" grew="<<grew<<" length="
                     <<brain.length(p.layout.work_start+10)<<"\n";
            return 1;
        }
        if(i==10) {
            h.new_his();Hamster child(1,p);child.copy_hamu(h);
            h=std::move(child);
        }
    }
    if(promotions!=1||even_after_upgrade==0)return 2;
    std::cout<<"PASS: bit loops skip 01 and COPY, answer 4 old + 6 trigger + 16 stable;"
                " one unary promotion, inherited across a generation\n";
}
