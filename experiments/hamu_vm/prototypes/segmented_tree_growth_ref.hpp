#pragma once
// HOST-ONLY MODEL, NOT A HAMSTER VM OPCODE OR GUEST IMPLEMENTATION.
// Validates one possible stable-ID growth contract, separately from the
// current 5-bit single-tree VM implementation. Neither byte-size nor
// lookup-time of this host reference is a VM performance claim.
#include <array>
#include <cstdint>
#include <stdexcept>
#include <unordered_map>
#include <vector>

class SegmentedTreeGrowthReference {
public:
    using Id = std::uint64_t;  // 0 = root; 1..31 map to segment 0; 32..62 segment 1
    struct Node {
        Id parent=0;
        std::uint8_t key=0;
        std::uint8_t wrong_mask=0;
        std::uint8_t correct=0;
        bool mastered=false;
    };
    struct Segment { std::array<Node,31> slots{}; };

    explicit SegmentedTreeGrowthReference(std::size_t max_segments=256)
        : max_segments_(max_segments) {}
    std::size_t node_count() const { return count_; }
    std::size_t segment_count() const { return segments_.size(); }
    std::size_t segment_limit() const { return max_segments_; }
    static std::size_t segment_for(Id id) {
        if (!id) throw std::invalid_argument("root has no physical row");
        return std::size_t((id-1)/31);
    }
    static std::size_t slot_for(Id id) {
        if (!id) throw std::invalid_argument("root has no physical row");
        return std::size_t((id-1)%31); // physical local ID is 1..31
    }
    Id find(Id parent, std::uint8_t key) const {
        if(key>7)throw std::invalid_argument("3-bit key");
        if(parent>count_)throw std::invalid_argument("unknown parent");
        auto it=links_.find(edge(parent,key));
        return it==links_.end()?0:it->second;
    }
    Id find_path(const std::vector<std::uint8_t>& keys) const {
        Id id=0;
        for(auto key:keys){id=find(id,key);if(!id)return 0;}
        return id;
    }
    // Preflight full path allocation before mutating anything. On exhaustion
    // earlier nodes/answers stay untouched, including shared prefixes.
    Id add_path(const std::vector<std::uint8_t>& keys) {
        if(keys.empty())throw std::invalid_argument("empty question key");
        Id id=0;std::size_t first_missing=keys.size();
        for(std::size_t i=0;i<keys.size();++i){
            if(keys[i]>7)throw std::invalid_argument("3-bit key");
            if(first_missing==keys.size()){
                const Id child=find(id,keys[i]);
                if(child) id=child;
                else first_missing=i;
            }
        }
        if(first_missing==keys.size())return id;
        const std::size_t needed=keys.size()-first_missing;
        if(max_segments_==0 || needed>max_segments_*31-count_)
            throw std::runtime_error("segmented tree has no capacity");
        for(std::size_t i=first_missing;i<keys.size();++i){
            if(count_%31==0)segments_.emplace_back();
            Id next=++count_;
            segments_[segment_for(next)].slots[slot_for(next)].parent=id;
            segments_[segment_for(next)].slots[slot_for(next)].key=keys[i];
            links_.emplace(edge(id,keys[i]),next);
            id=next;
        }
        return id;
    }
    const Node& node(Id id) const {
        if(id==0||id>count_)throw std::out_of_range("unknown stable node id");
        return segments_.at(segment_for(id)).slots.at(slot_for(id));
    }
    int next(Id id) const {
        const auto& n=node(id);
        if(n.mastered)return n.correct;
        for(int i=0;i<8;++i)if(!(n.wrong_mask&(1u<<i)))return i;
        return -1;
    }
    void record(Id id,int option,bool right){
        if(option<0||option>7)throw std::invalid_argument("option range");
        if(id==0||id>count_)throw std::out_of_range("unknown node id");
        auto& n=segments_.at(segment_for(id)).slots.at(slot_for(id));
        if(right){n.correct=std::uint8_t(option);n.mastered=true;}
        else if(!n.mastered)n.wrong_mask|=std::uint8_t(1u<<option);
    }
private:
    static Id edge(Id parent,std::uint8_t key){
        if(parent>(UINT64_MAX>>3))throw std::overflow_error("edge ID overflow");
        return (parent<<3)|key;
    }
    std::size_t max_segments_;
    std::size_t count_=0;
    std::vector<Segment> segments_;
    std::unordered_map<Id,Id> links_;
};
