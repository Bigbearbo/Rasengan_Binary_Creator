#pragma once
#include "feedback_learner.hpp"
#include "position_lexicon.hpp"
#include <map>
#include <utility>

// Human configured one-position grammar. Each parsed (order, ID) gets its own
// feedback state; a promoted token does not inherit its predecessor's meaning.
struct WordFeedbackSession {
    PositionLexicon lex;
    std::map<std::pair<int,int>,FeedbackLearner> models;
    explicit WordFeedbackSession(int starting_order):lex({starting_order}) {}
    PositionLexicon::Word read_operator(const std::string& bits) {
        auto word=lex.read(bits).at(0);
        models.try_emplace({word.order,word.id});
        return word;
    }
    int propose(const PositionLexicon::Word& word,int data,int n) const {
        return models.at({word.order,word.id}).choose(data,n);
    }
    void feedback(const PositionLexicon::Word& word,int data,int n,int answer,bool correct) {
        models.at({word.order,word.id}).observe(data,n,answer,correct);
    }
    int remaining(const PositionLexicon::Word& word) const {
        return models.at({word.order,word.id}).remaining();
    }
};
