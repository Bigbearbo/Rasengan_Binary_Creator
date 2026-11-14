#pragma once
// Explicit host-only migration of current wide bit-row tree semantics to
// canonical 31-row pages. Does NOT migrate program/work/HP or VM execution.
#include "hamu_vm_core.hpp"
#include <unordered_map>
#include <vector>
#include <stdexcept>

struct TreeMigrationStats {
    int live_nodes=0;
    int free_holes=0;
    int highest_live_id=0;
};

inline TreeMigrationStats import_wide_tree_rows_into_segmented(
    Hamster& target, const Hamster& source) {
    const auto& s=source.params;
    const auto& t=target.params;
    const int row_bits=s.tree_id_bits+7;
    if (s.tree_segmented_enabled || s.tree_id_bits<=5 || s.tree_id_bits>12 ||
        s.tree_capacity<=0 || s.tree_capacity>(1<<s.tree_id_bits)-1 ||
        s.tree_start<s.layout.work_start ||
        s.tree_start<s.layout.program_start-s.stable_work_bits ||
        static_cast<long long>(s.tree_start)+
            static_cast<long long>(s.tree_capacity)*row_bits>s.layout.program_start ||
        s.layout.program_start>static_cast<int>(source.memory.size()) ||
        !t.tree_segmented_enabled || t.tree_id_bits<s.tree_id_bits ||
        t.tree_capacity<s.tree_capacity || target.segment_used!=0 ||
        target.segment_pages.size()!=
            (std::size_t(t.tree_capacity)+Hamster::SEGMENT_PAGE_ROWS-1)/
                Hamster::SEGMENT_PAGE_ROWS)
        throw std::invalid_argument("Incompatible tree migration layout");
    for(const auto& page:target.segment_pages)
        for(uint32_t row:page)if(row)
            throw std::invalid_argument("Migration target is not empty");

    // All allocations and validation occur in temporary objects, so a bad
    // source tree cannot partially modify the target.
    std::deque<Hamster::SegmentPage> new_pages(target.segment_pages.size());
    std::vector<int> parents(std::size_t(s.tree_capacity)+1,0);
    std::vector<unsigned char> live(std::size_t(s.tree_capacity)+1,0);
    std::unordered_map<uint64_t,int> edges;
    TreeMigrationStats stats;
    for(int id=1;id<=s.tree_capacity;++id){
        const int base=s.tree_start+(id-1)*row_bits;
        if(!source.memory.at(base))continue; // dead rows carry no semantic data
        int parent=0,key=0;
        for(int b=1;b<=s.tree_id_bits;++b)
            parent=(parent<<1)|int(source.memory.at(base+b));
        for(int b=s.tree_id_bits+1;b<=s.tree_id_bits+3;++b)
            key=(key<<1)|int(source.memory.at(base+b));
        unsigned action=0;
        for(int b=s.tree_id_bits+4;b<=s.tree_id_bits+6;++b)
            action=(action<<1)|unsigned(source.memory.at(base+b));
        if(parent>s.tree_capacity || parent==id ||
           !edges.emplace(Hamster::segment_edge(parent,key),id).second)
            throw std::invalid_argument("Invalid parent or duplicate tree edge");
        const uint32_t packed=(uint32_t(parent)<<7)|(uint32_t(key)<<4)|
                              (uint32_t(action)<<1)|1u;
        new_pages[(id-1)/Hamster::SEGMENT_PAGE_ROWS]
                 [(id-1)%Hamster::SEGMENT_PAGE_ROWS]=packed;
        live[id]=1;parents[id]=parent;
        ++stats.live_nodes;
        stats.highest_live_id=id;
    }
    // Every live node must reach root 0 without passing a dead node or cycle.
    std::vector<unsigned char> color(std::size_t(s.tree_capacity)+1,0);
    for(int id=1;id<=s.tree_capacity;++id)if(live[id]&&!color[id]){
        std::vector<int> path;
        int cur=id;
        while(cur && !color[cur]){
            if(!live[cur])throw std::invalid_argument("Tree parent is dead");
            color[cur]=1;path.push_back(cur);cur=parents[cur];
        }
        if(cur && color[cur]==1)throw std::invalid_argument("Tree cycle");
        for(int node:path)color[node]=2;
    }
    stats.free_holes=stats.highest_live_id-stats.live_nodes;
    target.segment_pages.swap(new_pages);
    target.segment_used=stats.highest_live_id;
    target.rebuild_segment_first_free_id();
    target.segment_edge_index.swap(edges);
    target.segment_edge_index_valid=t.tree_index_enabled;
    if(!t.tree_index_enabled)target.invalidate_segment_index();
    target.creat_his=false; // an explicit new_his() is required before heredity
    return stats;
}
