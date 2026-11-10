#pragma once
#include "integrated_zero_program.hpp"

// Host-side trial installation in the first 16 pairs of the reserved slot.
// Guest decisions and execution-time program writes are separate future work.
class FragmentTransaction {
    IntegratedZero& target;
    std::vector<int> before;
    bool committed=false;
public:
    FragmentTransaction(IntegratedZero& g,const std::vector<int>& fragment):target(g),before(g.words) {
        if(fragment.empty()||fragment.size()%2||fragment.size()>32||
           fragment[fragment.size()-2]!=15||fragment.back()!=0)
            throw std::invalid_argument("fragment must fit slot and end in STOP");
        for(size_t i=0;i<fragment.size();i+=2)
            if(fragment[i]<0||fragment[i]>26||fragment[i+1]<0||fragment[i+1]>31)
                throw std::invalid_argument("fragment word out of range");
        const int start=2*g.reserve_start;
        if(g.reserve_start<0||g.reserve_pairs<16||start+32>int(g.words.size()))
            throw std::invalid_argument("invalid reserved slot");
        // Clear the complete slot, so a shorter fragment cannot inherit a
        // hidden suffix from its predecessor. Bridges begin at pair 16.
        for(int i=0;i<16;++i){g.words[start+2*i]=15;g.words[start+2*i+1]=0;}
        std::copy(fragment.begin(),fragment.end(),g.words.begin()+start);
    }
    FragmentTransaction(const FragmentTransaction&)=delete;
    FragmentTransaction& operator=(const FragmentTransaction&)=delete;
    ~FragmentTransaction(){if(!committed)target.words.swap(before);}
    void commit(){committed=true;}
};
