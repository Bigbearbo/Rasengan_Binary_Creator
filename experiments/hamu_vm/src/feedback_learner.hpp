#pragma once
#include <array>
#include <stdexcept>
#include <vector>

// Human supplied hypothesis space. Feedback contains only correct/incorrect;
// the target answer and target operator are not passed into the learner.
enum class UnaryHypothesis { Copy, Flip, Zero, One };
inline int predict_unary(UnaryHypothesis op,int data,int n) {
    if(n<1||n>7||data<0||data>=(1<<n))throw std::invalid_argument("unary input");
    const int mask=(1<<n)-1;
    switch(op) {
    case UnaryHypothesis::Copy:return data;
    case UnaryHypothesis::Flip:return data^mask;
    case UnaryHypothesis::Zero:return 0;
    case UnaryHypothesis::One:return mask;
    }
    throw std::invalid_argument("hypothesis");
}
struct FeedbackLearner {
    std::array<bool,4> possible{{true,true,true,true}};
    int choose(int data,int n) const {
        // Choose an answer not previously rejected on this same input.
        // Distinct hypotheses may predict the same output; one success alone
        // must not be mistaken for a uniquely identified meaning.
        for(int i=0;i<4;++i)if(possible[i])return predict_unary(static_cast<UnaryHypothesis>(i),data,n);
        throw std::logic_error("no viable hypothesis");
    }
    void observe(int data,int n,int answer,bool correct) {
        bool any=false;
        for(int i=0;i<4;++i)if(possible[i]) {
            const bool agrees=predict_unary(static_cast<UnaryHypothesis>(i),data,n)==answer;
            if(agrees!=correct)possible[i]=false;
            else any=true;
        }
        if(!any)throw std::logic_error("inconsistent feedback");
    }
    int remaining() const {
        int count=0;for(bool bit:possible)count+=bit;return count;
    }
};
