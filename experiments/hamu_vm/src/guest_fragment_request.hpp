#pragma once
#include "hamu_vm_core.hpp"

// Control-phase protocol: four n=2,k=1 tokens, verb/fragment/slot/END.
// Verb 2 requests a trial; verb 1 commits. Feedback bits in input are
// has_feedback, trial_passed. This policy is human-written VM code.
inline std::vector<int> fragment_request_policy(int state_offset=0) {
    if(state_offset<0||state_offset>45)throw std::invalid_argument("controller state offset");
    std::vector<int> c;
    auto e=[&](int op,int param){int i=int(c.size()/2);c.push_back(op);c.push_back(param);return i;};
    auto patch=[&](int from,int to) {
        if(to<=from||to-from>31)throw std::logic_error("request jump range");
        c[2*from+1]=to-from;
    };
    auto state=[&]() {
        e(0,3);
        for(int left=state_offset;left>0;) {
            int step=std::min(left,15);e(14,16+step);left-=step;
        }
    };
    auto message=[&](bool commit) {
        e(0,2);e(14,17);
        const int bits[]={commit?0:1,commit?1:0,0,0,1,0,0,0,0,1,1,0};
        for(int i=0;i<12;++i) {
            if(i==4&&!commit){e(9,1);e(14,17);}
            else e(bits[i]?2:3,1);
        }
        e(15,0);
    };
    e(16,1);e(0,0);e(14,17);e(4,1); // has feedback?
    e(24,2);const int first=e(26,0);
    e(14,17);e(4,1); // trial passed?
    const int passed=e(24,0);
    state();e(2,1); // failed: choose fragment 1 next
    const int request=int(c.size()/2);
    state();e(4,1);message(false);
    const int commit=int(c.size()/2);message(true);
    patch(first,request);patch(passed,commit);
    return c;
}

struct FragmentRequest {int verb,fragment,slot;};
inline FragmentRequest read_fragment_request(const Hamster& h) {
    const int start=h.params.layout.output_start+1;
    int ids[4]={0,0,0,0};
    for(int t=0;t<4;++t) {
        for(int bit=0;bit<3;++bit)
            if(!h.written.at(start+3*t+bit))throw std::runtime_error("incomplete guest request");
        if(h.memory.at(start+3*t+2))throw std::runtime_error("request tail");
        ids[t]=2*h.memory.at(start+3*t)+h.memory.at(start+3*t+1);
    }
    if(ids[3]!=3||ids[2]!=0||ids[0]>2)
        throw std::runtime_error("unsupported guest request");
    return {ids[0],ids[1],ids[2]};
}

// A two-bit policy gene selects one of four candidates after failure.
// Selection remains a host-controlled finite search over these policy genes.
inline std::vector<int> fragment_choice_policy(int failure_id) {
    if(failure_id<0||failure_id>3)throw std::invalid_argument("fragment choice gene");
    std::vector<int> c;
    auto e=[&](int op,int param){int i=int(c.size()/2);c.push_back(op);c.push_back(param);return i;};
    auto patch=[&](int from,int to) {
        if(to<=from||to-from>31)throw std::logic_error("choice jump range");
        c[2*from+1]=to-from;
    };
    auto state=[&](){e(0,3);e(14,31);e(14,31);e(14,26);}; // work+40
    auto message=[&](bool commit) {
        e(0,2);e(14,17);
        const int bits[]={commit?0:1,commit?1:0,0,0,0,0,0,0,0,1,1,0};
        for(int i=0;i<12;++i) {
            if(i==3){e(9,2);e(14,18);++i;}
            else e(bits[i]?2:3,1);
        }
        e(15,0);
    };
    e(16,1);e(0,0);e(14,17);e(4,1);e(24,2);
    const int first=e(26,0);
    e(14,17);e(4,1);const int passed=e(24,0);
    state();e(failure_id&2?2:3,1);e(failure_id&1?2:3,1);
    const int request=int(c.size()/2);state();e(4,2);message(false);
    const int commit=int(c.size()/2);state();e(4,2);message(true);
    patch(first,request);patch(passed,commit);
    return c;
}

// A resident four-candidate policy. The candidate number is a two-bit
// big-endian counter at work+40/+41. Only failed feedback advances it.
// work+42 records exhaustion after the fourth rejection; verb 0 means stop.
inline std::vector<int> fragment_sequential_policy() {
    std::vector<int> c;
    auto e=[&](int op,int param){int i=int(c.size()/2);c.push_back(op);c.push_back(param);return i;};
    auto patch=[&](int from,int to) {
        if(to<=from||to-from>31)throw std::logic_error("sequential jump range "+std::to_string(from)+" -> "+std::to_string(to));
        c[2*from+1]=to-from;
    };
    auto state=[&](){e(0,3);e(14,31);e(14,31);e(14,26);};
    e(16,1);
    state();e(14,18);e(4,1);const int exhausted=e(24,0);
    e(0,0);e(14,17);e(4,1); // has feedback in register 0
    e(24,2);const int initial=e(26,0);
    e(14,17);e(4,1); // passed in register 0
    const int passed=e(24,0);
    // Set exhaustion exactly when the rejected candidate was 3 (binary 11).
    state();e(4,2);state();e(14,18);e(2,1);e(14,1);
    e(6,1);e(8,17);e(6,1);e(8,1);
    e(26,2);const int skip=e(26,0); // bypass for failed feedback
    // Failed trial: old low bit is the carry, then invert low and XOR high.
    state();e(14,17);e(8,17);e(4,1);e(8,1);e(4,1);
    e(2,1);e(14,1);e(5,1);
    state();e(4,1);e(25,1);e(9,1);
    const int message=int(c.size()/2);
    // Re-read passed feedback; write verb (!passed, passed), fragment ID,
    // slot 000 and END 110, with all four n=2,k=1 tails explicitly zero.
    e(0,0);e(14,18);e(4,1);
    e(0,2);e(14,17);e(2,1);e(14,1);e(5,1);
    e(14,17);e(9,1);e(14,17);e(3,1);
    state();e(4,2);
    e(0,2);e(14,20);e(9,2);e(14,18);e(3,1);
    e(3,3);e(2,2);e(3,1);e(15,0);
    // A persistent exhaustion bit changes the verb to 00 without changing
    // the structural fragment/slot/END tokens.
    c.resize(c.size()-2);
    state();e(14,18);e(4,1);e(24,2);e(15,0);
    e(0,2);e(14,17);e(3,2);e(15,0);
    patch(exhausted,skip);patch(initial,skip);patch(passed,skip);patch(skip,message);
    return c;
}
