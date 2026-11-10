#pragma once
#include "tree_four_vm.hpp"

// Persistent individual policy +158; last initial execution failure +159.
inline std::vector<int> tree_observed_policy_set_program(bool enabled){
    TreeFourCode c;c.e(16,1);c.at(3,158);c.e(enabled?2:3,1);
    c.at(3,159);c.e(3,1);c.e(15,0);return c.w;
}
inline std::vector<int> tree_observed_policy_export_program(){
    TreeFourCode c;c.e(16,1);c.at(3,158);c.e(4,1);c.at(2,28);c.e(9,1);
    c.at(2,29);c.e(2,1);c.e(15,0);return c.w;
}
inline std::vector<int> tree_observed_policy_react_program(){
    TreeFourCode c;c.e(16,1);c.require(159);c.at(3,158);c.e(2,1);c.e(15,0);return c.w;
}

// work+124..135 predictions, +136..139 validity, +140 batch commit;
// +141..154 context/attempt/grade copy; +156/157 record format markers.
inline std::vector<int> tree_observed_clear_program(){
    TreeFourCode c;c.e(16,1);c.at(3,136);c.e(3,5);c.e(15,0);return c.w;
}

// Four fresh guest-owned request bits at output+20..23. The ordinary choice
// guard binds this read to the current pending context and promoted width.
inline std::vector<int> tree_observed_request_program(int slot){
    TreeFourCode c;c.append(tree_width_choice_guard_program(slot));
    c.require(tree_four_format(slot));c.require(tree_observed_format(slot));
    c.at(3,tree_four_mask(slot));c.e(4,4);
    c.at(2,20);c.e(9,4);c.e(15,0);return c.w;
}

// Select the first survivor with a valid observation from this batch. A failed
// execution never clears the survivor mask or confirms a different meaning.
inline std::vector<int> tree_observed_recover_choice_program(int slot){
    TreeFourCode c;c.append(tree_width_choice_guard_program(slot));
    c.require(tree_four_format(slot));c.require(tree_observed_format(slot));
    c.at(2,25);c.e(3,3);
    for(int id=0;id<4;++id){
        c.at(3,tree_four_mask(slot)+id);c.e(4,1);c.at(2,24);c.e(9,1);
        c.at(3,136+id);c.e(4,1);c.at(2,24);c.e(6,1);c.e(4,1);
        c.e(24,2);const int skip=c.e(26,0);
        c.pair(2,26,id);c.at(2,25);c.e(2,1);c.e(15,0);
        c.patch(skip,int(c.w.size()/2));
    }
    c.e(15,0);return c.w;
}

inline std::vector<int> tree_observed_capture_program(int id){
    if(id<0||id>=4)throw std::invalid_argument("candidate");
    TreeFourCode c;c.e(16,1);
    c.at(3,136+id);c.e(3,1);
    c.at(2,0);c.e(4,3);c.at(3,124+3*id);c.e(9,3);
    c.at(3,136+id);c.e(2,1);c.e(15,0);return c.w;
}

inline std::vector<int> tree_observed_restore_program(){
    TreeFourCode c;c.e(16,1);c.at(3,89);c.e(4,3);c.at(2,0);c.e(9,3);c.e(15,0);return c.w;
}

inline std::vector<int> tree_observed_commit_program(int slot){
    TreeFourCode c;c.append(tree_four_grade_guard_program(slot));c.require(tree_observed_format(slot));
    c.at(3,80);c.e(4,9);c.at(3,141);c.e(9,9);
    c.at(3,102);c.e(4,1);c.at(3,150);c.e(9,1);
    c.at(3,89);c.e(4,3);c.at(3,151);c.e(9,3);
    c.at(3,34);c.e(4,1);c.at(3,154);c.e(9,1);
    c.at(3,140);c.e(2,1);c.e(15,0);return c.w;
}

inline std::vector<int> tree_observed_guard_program(int slot){
    TreeFourCode c;c.append(tree_four_grade_guard_program(slot));
    c.require(tree_observed_format(slot));c.require(140);
    auto compare=[&](int a,int b,int bits){
        c.at(3,a);c.e(4,bits);c.at(2,27);c.e(9,bits);
        c.at(3,b);c.e(4,bits);c.at(2,27);c.e(5,bits);
        for(int k=0;k<bits;++k){c.at(2,27+k);c.e(4,1);c.zero();}
    };
    for(int b=0;b<3;++b)compare(141+3*b,80+3*b,3);
    compare(150,102,1);compare(151,89,3);compare(154,34,1);
    return c.w;
}

inline std::vector<int> tree_observed_feedback_program(int slot){
    TreeFourCode c;c.e(16,1);c.at(3,94);c.e(3,1);
    c.append(tree_observed_guard_program(slot));
    for(int id=0;id<4;++id){
        c.reset();c.at(3,124+3*id);c.e(4,3);c.at(2,20);c.e(9,3);
        c.at(3,89);c.e(4,3);c.at(2,20);c.e(5,3);
        c.at(2,23);c.e(3,1);
        for(int b=0;b<3;++b){c.at(2,20+b);c.e(4,1);c.at(2,23);c.e(7,1);}
        c.at(3,34);c.e(4,1);c.at(2,23);c.e(5,1);
        // Invalid predictions are unknown evidence: OR with NOT validity
        // keeps the prior mask, rather than eliminating a failed execution.
        c.at(3,136+id);c.e(4,1);c.at(2,24);c.e(2,1);c.e(14,1);c.e(5,1);c.e(4,1);
        c.at(2,23);c.e(7,1);c.e(4,1);c.at(3,tree_four_mask(slot)+id);c.e(6,1);
    }
    c.at(3,94);c.e(2,1);c.e(15,0);return c.w;
}

inline std::vector<int> tree_observed_confirm_program(int slot){
    TreeFourCode c;c.append(tree_observed_guard_program(slot));
    c.append(tree_four_confirm_body(slot));return c.w;
}

// Export a fragment-table index. Two tree action bits are a stable index
// encoding here; this program does not implement COPY/FLIP/ZERO/ONE itself.
inline std::vector<int> tree_observed_route_choice_program(){
    TreeFourCode c;c.e(16,1);c.at(2,25);c.e(3,3);
    for(int b=0;b<5;++b){c.at(0,0);c.e(4,1);if(b<4)c.e(8,17);}
    c.e(8,17);c.at(0,2);c.e(8,17);c.e(4,3);c.e(29,0);c.e(8,1);c.found();
    c.at(0,0);c.e(8,17);c.e(4,2);c.at(3,96);c.e(8,18);c.e(4,1);c.e(29,0);c.e(8,3);c.found();
    c.at(3,96);c.e(4,1);const int n3=c.e(24,0);
    c.at(0,0);c.e(8,17);c.e(4,1);c.at(0,6);c.e(8,17);c.e(4,2);c.e(8,2);
    const int done=c.e(26,0),three=int(c.w.size()/2);
    c.at(0,6);c.e(8,17);c.e(4,3);c.e(8,1);
    const int lookup=int(c.w.size()/2);c.patch(n3,three);c.patch(done,lookup);
    c.e(29,0);c.found();c.e(30,0);c.found();
    c.e(8,18);c.at(2,26);c.e(9,1); // action low -> index high
    c.e(8,1);c.at(2,27);c.e(9,1); // action high -> index low
    c.at(2,25);c.e(2,1);c.e(15,0);return c.w;
}
