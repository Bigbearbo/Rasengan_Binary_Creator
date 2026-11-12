#include "../src/feedback_learner.hpp"
#include "../src/position_lexicon.hpp"
#include <cassert>
#include <iostream>
int main() {
    PositionLexicon lex({2});
    auto word=lex.read("0110")[0]; // 01 plus old tail changed to 1, new tail 0
    assert(word.promoted&&word.id==3&&!word.meaning_known);
    FeedbackLearner learner;
    int trials=0,repetitions=0;
    for(int data:{0,1,2}) {
        const int expected=predict_unary(UnaryHypothesis::Flip,data,2);
        bool correct=false;
        for(int attempt=0;attempt<4&&!correct;++attempt) {
            const int answer=learner.choose(data,2);
            correct=answer==expected; // teacher-only oracle
            learner.observe(data,2,answer,correct);
            ++trials;
            if(!correct)++repetitions; // teacher repeats same question
        }
        assert(correct);
        if(data==0)assert(learner.remaining()==2); // FLIP and ONE both answer 3
    }
    assert(learner.remaining()==1);
    assert(learner.possible[static_cast<int>(UnaryHypothesis::Flip)]);
    for(int data=0;data<4;++data)
        assert(learner.choose(data,2)==predict_unary(UnaryHypothesis::Flip,data,2));
    assert(!lex.read("0110")[0].meaning_known); // hypothesis is not dictionary registration
    lex.meanings[0][3][3]="FLIP";
    assert(lex.read("0110")[0].meaning=="FLIP");
    std::cout<<"PASS feedback learner: trials="<<trials<<" wrong="<<repetitions
             <<" remaining="<<learner.remaining()<<"; separate lexicon registration\n";
}
