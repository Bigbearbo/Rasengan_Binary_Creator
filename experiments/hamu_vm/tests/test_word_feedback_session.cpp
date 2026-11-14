#include "../src/word_feedback_session.hpp"
#include <cassert>
#include <iostream>
int main() {
    WordFeedbackSession session(2);
    // Old n=2 ID 1 and promoted n=3 ID 3 are different dictionary keys.
    const auto old=session.read_operator("010");
    assert(old.order==2&&old.id==1&&!old.promoted);
    for(int data:{0,1}) {
        const int target=predict_unary(UnaryHypothesis::Flip,data,2);
        bool solved=false;
        for(int attempts=0;attempts<4&&!solved;++attempts) {
            const int answer=session.propose(old,data,2);
            solved=answer==target;
            session.feedback(old,data,2,answer,solved);
        }
        assert(solved);
    }
    assert(session.remaining(old)==1);
    const auto fresh=session.read_operator("0110");
    assert(fresh.order==3&&fresh.id==3&&fresh.promoted);
    assert(session.remaining(fresh)==4); // old FLIP not presumed for new word
    // Teacher has assigned the new word ZERO; learner sees only binary grades.
    for(int data:{1,2}) {
        bool solved=false;
        for(int attempts=0;attempts<4&&!solved;++attempts) {
            const int answer=session.propose(fresh,data,2);
            solved=answer==0;
            session.feedback(fresh,data,2,answer,solved);
        }
        assert(solved);
    }
    assert(session.remaining(fresh)==1);
    assert(session.propose(old,2,2)==1); // old FLIP remains available
    assert(session.propose(fresh,2,2)==0);
    assert(!fresh.meaning_known); // hypothesis state is not a registered label
    std::cout<<"PASS two word-specific feedback models across n2->n3 promotion\n";
}
