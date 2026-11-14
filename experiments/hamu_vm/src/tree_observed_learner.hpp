#pragma once
#include "tree_four_learning_turn.hpp"
#include "tree_observed_vm.hpp"

// The table is copied and immutable for this learner and its descendants.
// Tree indices identify these exact fragments, rather than semantic labels.
struct TreeObservedLearner {
    Hamster hamster;
    const std::array<std::vector<int>,4> fragments;
    TreeObservedLearner(int id,const HamsterParams& p,const std::array<std::vector<int>,4>& code)
        :hamster(id,p),fragments(code){}
    TreeObservedLearner(const TreeObservedLearner& parent,int id)
        :hamster(id,parent.hamster.params),fragments(parent.fragments){
        Hamster snapshot=parent.hamster;snapshot.new_his();hamster.copy_hamu(snapshot);
    }
};

struct TreeFragmentObservation {
    std::array<bool,3> answer{};
    bool valid=false;
    int steps=0;
};

// Host execution boundary. Only a fresh three-bit answer is exported from the
// private copy. Work writes, restricted reads and invalid execution are not
// semantic evidence. The runner only installs and executes the supplied code.
template<class Runner>
TreeFragmentObservation observe_tree_fragment(const Hamster& learner,
    const std::vector<int>& code,Runner run){
    Hamster probe=learner;const auto l=probe.params.layout;
    if(l.status_start-l.input_start<=40||l.work_start-l.output_start<3||l.work_start+96>=l.program_start)
        throw std::invalid_argument("fragment observation layout");
    probe.memory[l.input_start+40]=false;
    for(int offset:{34,92,93,94})probe.memory[l.work_start+offset]=false;
    std::fill(probe.memory.begin()+l.output_start,probe.memory.begin()+l.work_start,false);
    std::fill(probe.written.begin(),probe.written.end(),false);
    std::fill(probe.read_seen.begin(),probe.read_seen.end(),false);
    std::fill(probe.val_reg.begin(),probe.val_reg.end(),false);probe.val_ptr=0;
    probe.stop=false;probe.budget_exhausted=false;probe.work_insert_blocked=false;probe.executed_steps=0;
    const auto before=probe.memory;
    run(probe,code);
    bool valid=probe.stop&&!probe.budget_exhausted&&!probe.work_insert_blocked;
    for(int pos=0;pos<int(probe.memory.size());++pos){
        const bool answer=pos>=l.output_start&&pos<l.output_start+3;
        if(probe.written[pos]&&!answer)valid=false;
        if(pos<l.program_start&&!answer&&probe.memory[pos]!=before[pos])valid=false;
        const bool input=pos>=l.input_start&&pos<l.status_start&&pos!=l.input_start+40;
        if(probe.read_seen[pos]&&!input&&!answer&&pos!=l.work_start+96)valid=false;
    }
    TreeFragmentObservation result;result.steps=probe.executed_steps;
    for(int bit=0;bit<3;++bit){valid=valid&&probe.written[l.output_start+bit];result.answer[bit]=probe.memory[l.output_start+bit];}
    result.valid=valid;return result;
}

inline void publish_tree_fragment_answer(Hamster& h,const TreeFragmentObservation& observation){
    const int out=h.params.layout.output_start;
    std::fill(h.memory.begin()+out,h.memory.begin()+h.params.layout.work_start,false);
    std::fill(h.written.begin()+out,h.written.begin()+h.params.layout.work_start,false);
    if(observation.valid)for(int bit=0;bit<3;++bit){h.memory[out+bit]=observation.answer[bit];h.written[out+bit]=true;}
}

inline std::vector<int> tree_observed_bind_program(int slot){
    TreeFourCode c;c.e(16,1);c.require(tree_observed_format(slot));c.append(tree_four_bind_program(slot));return c.w;
}
inline std::vector<int> tree_observed_reclaim_program(int slot){
    TreeFourCode c;c.e(16,1);c.require(tree_observed_format(slot));c.append(tree_four_reclaim_program(slot));return c.w;
}

struct TreeObservedTurn {
    TreeLearningTurn learning;
    std::array<bool,4> prediction_valid{};
    std::array<int,4> prediction_steps{};
    bool recovered=false;
    bool initially_invalid=false;
};

template<class Runner>
std::optional<TreeObservedTurn> run_tree_observed_learning_turn(TreeObservedLearner& learner,
    const std::array<bool,3>& expected,Runner run,bool recover_invalid=false){
    auto& h=learner.hamster;const int work=h.params.layout.work_start,out=h.params.layout.output_start;
    if(work+157>=h.params.layout.program_start||out+29>=work)throw std::invalid_argument("observed learning layout");
    auto guest=[&](const std::vector<int>& code){run(h,code);};
    h.memory[work+104]=false;h.written[work+104]=false;guest(tree_width_prepare_program());
    if(!h.stop||h.budget_exhausted||!h.written[work+104]||!h.memory[work+104])return std::nullopt;
    for(int slot:{57,70}){guest(tree_observed_bind_program(slot));guest(tree_observed_reclaim_program(slot));}
    for(int slot:{57,70})guest(tree_width_pending_program(slot,true,true));
    for(int slot:{57,70}){
        for(int pos=out+25;pos<=out+27;++pos){h.memory[pos]=false;h.written[pos]=false;}
        guest(tree_four_choice_program(slot,true));
        if(!h.stop||h.budget_exhausted||!h.memory[out+25]||!h.written[out+25]||!h.written[out+26]||!h.written[out+27])continue;
        int id=2*int(h.memory[out+26])+int(h.memory[out+27]);
        for(int j=0;j<4;++j){h.memory[out+20+j]=false;h.written[out+20+j]=false;}
        guest(tree_observed_request_program(slot));
        bool request_valid=h.stop&&!h.budget_exhausted;
        for(int j=0;j<4;++j)request_valid=request_valid&&h.written[out+20+j];
        if(!request_valid||!h.memory[out+20+id])return std::nullopt;
        std::array<bool,4> requested{};
        for(int j=0;j<4;++j)requested[j]=h.memory[out+20+j];
        guest(tree_observed_clear_program());
        std::array<TreeFragmentObservation,4> observations;
        for(int j=0;j<4;++j)if(requested[j])observations[j]=observe_tree_fragment(h,learner.fragments[j],run);
        const bool initially_invalid=!observations[id].valid;
        bool recovered=false,captured=false;
        if(recover_invalid&&!observations[id].valid){
            for(int j=0;j<4;++j)if(observations[j].valid){
                publish_tree_fragment_answer(h,observations[j]);guest(tree_observed_capture_program(j));
            }
            captured=true;
            for(int j=25;j<=27;++j){h.memory[out+j]=false;h.written[out+j]=false;}
            guest(tree_observed_recover_choice_program(slot));
            if(!h.stop||h.budget_exhausted){publish_tree_fragment_answer(h,{});return std::nullopt;}
            if(h.memory[out+25]&&h.written[out+25]&&h.written[out+26]&&h.written[out+27]){
                const int alternate=2*int(h.memory[out+26])+int(h.memory[out+27]);
                if(!requested[alternate]||!observations[alternate].valid){publish_tree_fragment_answer(h,{});return std::nullopt;}
                id=alternate;recovered=true;
            }
        }
        publish_tree_fragment_answer(h,observations[id]);
        const bool valid=observations[id].valid,correct=valid&&observations[id].answer==expected;
        h.memory[h.params.layout.input_start+40]=correct;
        h.memory[work+34]=false;h.memory[work+92]=false;h.memory[work+93]=valid;h.memory[work+94]=false;
        if(valid){
            guest(tree_width_snapshot_program());
            // Recovery already saved these fresh observations. The grade
            // snapshot only updates context fields, so reuse this same batch.
            for(int j=0;j<4;++j)if(!captured&&observations[j].valid){
                publish_tree_fragment_answer(h,observations[j]);guest(tree_observed_capture_program(j));
            }
            guest(tree_observed_restore_program());guest(tree_observed_commit_program(slot));
            guest(tree_observed_feedback_program(slot));guest(tree_observed_confirm_program(slot));guest(tree_observed_bind_program(slot));
        }
        TreeObservedTurn result{{slot,id,valid,correct,bool(h.memory[work+slot])}};
        result.recovered=recovered;
        result.initially_invalid=initially_invalid;
        for(int j=0;j<4;++j){result.prediction_valid[j]=observations[j].valid;result.prediction_steps[j]=observations[j].steps;}
        guest(tree_observed_reclaim_program(slot));return result;
    }
    return std::nullopt;
}

// Guest exports its persistent policy before the turn. The host publishes a
// factual failure sensor afterwards; the guest enables recovery after failure.
// This is an authored sticky rule, not an evolved or cost-optimal policy.
template<class Runner>
std::optional<TreeObservedTurn> run_tree_observed_policy_turn(TreeObservedLearner& learner,
    const std::array<bool,3>& expected,Runner run){
    auto& h=learner.hamster;const auto l=h.params.layout;
    if(l.work_start+159>=l.program_start||l.output_start+29>=l.work_start)
        throw std::invalid_argument("observed policy layout");
    for(int j=28;j<=29;++j){h.memory[l.output_start+j]=false;h.written[l.output_start+j]=false;}
    run(h,tree_observed_policy_export_program());
    if(!h.stop||h.budget_exhausted||!h.written[l.output_start+28]||
       !h.written[l.output_start+29]||!h.memory[l.output_start+29]){
        publish_tree_fragment_answer(h,{});return std::nullopt;
    }
    const bool enabled=h.memory[l.output_start+28];
    const auto result=run_tree_observed_learning_turn(learner,expected,run,enabled);
    if(result){
        h.memory[l.work_start+159]=result->initially_invalid;
        run(h,tree_observed_policy_react_program());
    }
    return result;
}

// Lookup is a guest decision; dispatch and output validation use the same
// immutable table and private execution boundary as learning observations.
template<class Runner>
std::optional<int> run_tree_observed_route(TreeObservedLearner& learner,Runner run){
    auto& h=learner.hamster;const int out=h.params.layout.output_start,work=h.params.layout.work_start;
    if(work+104>=h.params.layout.program_start||out+29>=work)throw std::invalid_argument("observed route layout");
    auto clear=[&](){publish_tree_fragment_answer(h,TreeFragmentObservation{});};
    clear();h.memory[work+104]=false;h.written[work+104]=false;run(h,tree_width_prepare_program());
    if(!h.stop||h.budget_exhausted||!h.written[work+104]||!h.memory[work+104]){clear();return std::nullopt;}
    for(int pos=out+25;pos<=out+27;++pos){h.memory[pos]=false;h.written[pos]=false;}
    run(h,tree_observed_route_choice_program());
    if(!h.stop||h.budget_exhausted||!h.memory[out+25]||!h.written[out+25]||!h.written[out+26]||!h.written[out+27]){clear();return std::nullopt;}
    const int id=2*int(h.memory[out+26])+int(h.memory[out+27]);
    const auto answer=observe_tree_fragment(h,learner.fragments[id],run);publish_tree_fragment_answer(h,answer);
    if(!answer.valid)return std::nullopt;return id;
}
