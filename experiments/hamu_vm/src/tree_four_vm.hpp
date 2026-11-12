#pragma once
#include "tree_four_layout.hpp"
#include "tree_width_choice_vm.hpp"
#include "tree_width_grade_vm.hpp"
#include "tree_width_trial_vm.hpp"

// Program construction only: every context, prediction and mask decision
// below is emitted as guest instructions, not evaluated by the host.
struct TreeFourCode {
    std::vector<int> w;
    int e(int op,int arg){int i=int(w.size()/2);w.push_back(op);w.push_back(arg);return i;}
    void at(int area,int pos){e(0,area);while(pos>=15){e(14,31);pos-=15;}if(pos)e(14,16+pos);}
    void reset(){e(8,11);}
    void found(){e(18,20);e(15,0);}
    void zero(){e(24,2);e(26,2);e(15,0);}
    void require(int pos){at(3,pos);e(4,1);found();}
    void append(const std::vector<int>& code){w.insert(w.end(),code.begin(),code.end());}
    void patch(int from,int target){
        if(target-from<=0||target-from>31)throw std::logic_error("four candidate jump");
        w[2*from+1]=target-from;
    }
    void pair(int area,int pos,int value){
        at(area,pos);
        if(value==0||value==3)e(value==3?2:3,2);
        else {e(value&2?2:3,1);e(value&1?2:3,1);}
    }
};

inline std::vector<int> tree_four_trial_program(int candidate){
    if(candidate<0||candidate>=4)throw std::invalid_argument("candidate");
    if(candidate<2)return tree_width_trial_program(candidate==1);
    return {16,1,0,2,candidate==2?3:2,3,15,0};
}

inline std::vector<int> tree_four_choice_program(int slot,bool observed=false){
    TreeFourCode c;c.append(tree_width_choice_guard_program(slot));
    c.require(tree_four_format(slot));
    if(observed)c.require(tree_observed_format(slot));
    c.at(2,25);c.e(3,3);
    for(int id=0;id<4;++id){
        c.at(3,tree_four_mask(slot)+id);c.e(4,1);
        c.e(24,2);const int skip=c.e(26,0);
        c.pair(2,26,id);c.at(2,25);c.e(2,1);c.e(15,0);
        c.patch(skip,int(c.w.size()/2));
    }
    c.e(15,0);return c.w;
}

inline std::vector<int> tree_four_grade_guard_program(int slot){
    TreeFourCode c;c.append(tree_width_grade_guard_program(slot));
    c.require(tree_four_format(slot));return c.w;
}

inline void tree_four_prediction(TreeFourCode& c,int id){
    c.reset();
    if(id<2){
        c.at(3,86);c.e(4,3);c.at(2,20);
        if(id==0)c.e(9,3);
        else {c.e(2,3);c.e(14,3);c.e(5,3);}
    }else{c.at(2,20);c.e(id==2?3:2,3);}
}

inline std::vector<int> tree_four_feedback_program(int slot){
    TreeFourCode c;c.e(16,1);c.at(3,94);c.e(3,1);
    c.append(tree_four_grade_guard_program(slot));
    for(int id=0;id<4;++id){
        tree_four_prediction(c,id);
        c.at(3,89);c.e(4,3);c.at(2,20);c.e(5,3);
        c.at(2,23);c.e(3,1);
        for(int b=0;b<3;++b){c.at(2,20+b);c.e(4,1);c.at(2,23);c.e(7,1);}
        c.at(3,34);c.e(4,1);c.at(2,23);c.e(5,1);c.e(4,1);
        c.at(3,tree_four_mask(slot)+id);c.e(6,1);
    }
    c.at(3,94);c.e(2,1);c.e(15,0);return c.w;
}

inline std::vector<int> tree_four_confirm_body(int slot){
    TreeFourCode c;
    c.require(94);c.require(34);
    for(int id=0;id<4;++id){
        c.at(2,23);c.e(3,1);
        for(int j=0;j<4;++j){
            c.at(3,tree_four_mask(slot)+j);c.e(4,1);
            if(j==id){c.at(2,24);c.e(2,1);c.e(14,1);c.e(5,1);c.e(4,1);}
            c.at(2,23);c.e(7,1);
        }
        c.at(2,23);c.e(4,1);const int next=c.e(24,0);
        c.pair(3,tree_four_action(slot),tree_four_actions[id]);
        c.at(3,slot);c.e(2,1);c.e(15,0);
        c.patch(next,int(c.w.size()/2));
    }
    c.e(15,0);return c.w;
}

inline std::vector<int> tree_four_confirm_program(int slot){
    TreeFourCode c;c.append(tree_four_grade_guard_program(slot));
    c.append(tree_four_confirm_body(slot));return c.w;
}

inline TreeFourCode tree_four_saved_leaf(int slot){
    TreeFourCode c;c.e(16,1);
    const int present=slot==57?47:60;
    c.require(present);c.require(slot==57?78:79);c.require(slot);c.require(tree_four_format(slot));
    for(int b=0;b<5;++b){c.at(0,0);c.e(4,1);if(b<4)c.e(8,17);}
    c.e(8,17);
    c.at(3,slot==57?72:75);c.e(8,17);c.e(4,3);c.e(29,0);c.e(8,1);c.found();
    c.at(0,0);c.e(8,17);c.e(4,2);
    c.at(3,slot==57?100:101);c.e(8,18);c.e(4,1);c.e(29,0);c.e(8,3);c.found();
    c.at(3,present+2);c.e(8,17);c.e(4,3);c.e(29,0);c.e(8,1);c.found();
    return c;
}

inline std::vector<int> tree_four_bind_program(int slot){
    auto c=tree_four_saved_leaf(slot);
    c.e(30,0);c.e(24,2);c.e(26,2);c.e(15,0);
    c.at(3,tree_four_action(slot));c.e(8,17);c.e(4,2);
    c.e(30,1);c.e(15,0);return c.w;
}

inline std::vector<int> tree_four_reclaim_program(int slot){
    auto c=tree_four_saved_leaf(slot);
    c.e(30,0);c.found();c.e(8,17);
    c.at(2,24);c.e(9,2);
    c.at(3,tree_four_action(slot));c.e(4,2);c.at(2,24);c.e(5,2);
    for(int b=0;b<2;++b){c.at(2,24+b);c.e(4,1);c.zero();}
    c.at(3,92);c.e(3,3);c.at(3,slot==57?47:60);c.e(3,1);
    c.e(15,0);return c.w;
}
