#pragma once
#include "tree_observed_learner.hpp"
#include <array>
#include <stdexcept>

enum class TreeQuestionKind { Zero, Copy, Flip, ToggleLast, ToggleMiddle, ToggleFirst };
struct TreeQuestion {
    int operator_width,operator_id,data;
    TreeQuestionKind kind;
};
inline int tree_question_value(const TreeQuestion& q){
    if((q.operator_width!=2&&q.operator_width!=3)||q.operator_id<0||
       q.operator_id>=(1<<q.operator_width)||q.data<0||q.data>7)
        throw std::invalid_argument("tree question fields");
    switch(q.kind){
        case TreeQuestionKind::Zero:return 0;
        case TreeQuestionKind::Copy:return q.data;
        case TreeQuestionKind::Flip:return q.data^7;
        case TreeQuestionKind::ToggleLast:return q.data^1;
        case TreeQuestionKind::ToggleMiddle:return q.data^2;
        case TreeQuestionKind::ToggleFirst:return q.data^4;
    }
    throw std::invalid_argument("tree question kind");
}
inline std::array<bool,3> tree_question_answer(const TreeQuestion& q){
    const int value=tree_question_value(q);
    return {bool(value&4),bool(value&2),bool(value&1)};
}
inline void write_tree_question(Hamster& h,const TreeQuestion& q){
    (void)tree_question_value(q);
    const auto l=h.params.layout;
    if(l.status_start-l.input_start<=40)throw std::invalid_argument("tree question layout");
    std::fill(h.memory.begin()+l.input_start,h.memory.begin()+l.status_start,false);
    h.memory[l.input_start+1]=true; // 01 startup
    const auto category=SpiralToken(1,3,1).bits;
    const auto op=SpiralToken(q.operator_id,q.operator_width,1).bits;
    const auto data=SpiralToken(q.data,3,1).bits;
    for(size_t i=0;i<category.size();++i)h.memory[l.input_start+2+i]=category[i];
    for(size_t i=0;i<op.size();++i)h.memory[l.input_start+6+i]=op[i];
    for(size_t i=0;i<data.size();++i)h.memory[l.input_start+7+q.operator_width+i]=data[i];
}

// A closed, authored curriculum: three n=2 meanings, then one n=3 meaning.
// Widening is one-way in the current guest, so narrow questions do not resume.
inline constexpr std::array<TreeQuestion,12> tree_question_curriculum{{
    {2,1,0,TreeQuestionKind::ToggleLast},
    {2,2,0,TreeQuestionKind::Copy},
    {2,1,2,TreeQuestionKind::ToggleLast},
    {2,3,0,TreeQuestionKind::Flip},
    {2,2,3,TreeQuestionKind::Copy},
    {2,3,3,TreeQuestionKind::Flip},
    {2,2,5,TreeQuestionKind::Copy},
    {2,3,4,TreeQuestionKind::Flip},
    {3,1,0,TreeQuestionKind::Zero},
    {3,1,5,TreeQuestionKind::Zero},
    {3,1,3,TreeQuestionKind::Zero},
    {3,1,7,TreeQuestionKind::Zero}
}};
inline TreeQuestion tree_question_variant(int round){
    if(round<1||round>12)throw std::invalid_argument("tree question round");
    // Same teacher schedule for each individual; no individual gets a custom
    // answer. Values vary within each meaning before the one-way width change.
    return tree_question_curriculum[size_t(round-1)];
}
inline TreeQuestion tree_question_permuted(int round,int seed){
    if(round<1||round>12||seed<0||seed>4)throw std::invalid_argument("tree question permutation");
    // Odd strides permute the first eight entries without replacement. The
    // final four remain after the one-way width promotion. This changes only
    // order, preserving the exact multiset of twelve questions.
    constexpr std::array<int,5> start{0,3,2,7,4},stride{1,5,3,7,1};
    const int index=round<=8?(start[size_t(seed)]+(round-1)*stride[size_t(seed)])%8:
        8+(round-9+seed)%4;
    return tree_question_curriculum[size_t(index)];
}
