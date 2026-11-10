#include "../prototypes/segmented_tree_growth_ref.hpp"
#include <iostream>
#include <stdexcept>
#include <vector>

static std::vector<std::uint8_t> key(int n){
    // Namespace 7, then four 3-bit pieces: supports 4096 distinct keys.
    return {7,std::uint8_t((n>>9)&7),std::uint8_t((n>>6)&7),
            std::uint8_t((n>>3)&7),std::uint8_t(n&7)};
}
int main(){
    SegmentedTreeGrowthReference tree(200);
    const auto first=tree.add_path(key(0));
    if(!first)throw std::runtime_error("first insertion failed");
    tree.record(first,0,false);tree.record(first,1,true);
    if(tree.next(first)!=1)throw std::runtime_error("first learning failed");
    std::size_t crossed_31_at=0;
    for(int n=1;n<3000;++n){
        const auto before=tree.node_count();
        auto handle=tree.add_path(key(n));
        if(!crossed_31_at&&before<=31&&tree.node_count()>31)crossed_31_at=n;
        if(!handle||tree.find_path(key(n))!=handle)
            throw std::runtime_error("duplicate or missing key at expansion");
        if(n%13==0){tree.record(handle,0,false);tree.record(handle,3,true);}
        if(tree.find_path(key(0))!=first||tree.next(first)!=1)
            throw std::runtime_error("old handle moved or old knowledge changed");
    }
    if(!crossed_31_at||tree.node_count()<3000||tree.segment_count()<90)
        throw std::runtime_error("growth did not pass multiple segments");
    for(int n=0;n<3000;++n){
        auto handle=tree.find_path(key(n));
        if(!handle)throw std::runtime_error("lost grown question");
        if(n==0){if(tree.next(handle)!=1)throw std::runtime_error("lost earliest answer");}
        else if(n%13==0){if(tree.next(handle)!=3)throw std::runtime_error("lost memorized answer");}
        else if(tree.next(handle)!=0)throw std::runtime_error("unexpected answer");
        const auto segment=SegmentedTreeGrowthReference::segment_for(handle);
        const auto slot=SegmentedTreeGrowthReference::slot_for(handle);
        if(segment>=tree.segment_count()||slot>=31)
            throw std::runtime_error("invalid physical handle");
    }
    const auto inherited=tree; // host-only snapshot, not VM heredity
    if(inherited.find_path(key(0))!=first||inherited.next(first)!=1||
       inherited.find_path(key(2999))!=tree.find_path(key(2999)))
        throw std::runtime_error("prototype copy lost data");
    SegmentedTreeGrowthReference tiny(1);
    for(int n=0;n<16;++n)tiny.add_path(key(n));
    const auto size_before=tiny.node_count();
    const auto first_before=tiny.find_path(key(0));
    bool blocked=false;
    try {for(int n=16;n<40;++n)tiny.add_path(key(n));}
    catch(const std::runtime_error&){blocked=true;}
    if(!blocked||tiny.node_count()>31||tiny.find_path(key(0))!=first_before)
        throw std::runtime_error("capacity refusal corrupted earlier keys");
    const auto before_again=tiny.node_count();
    try {tiny.add_path(key(4095));}catch(const std::runtime_error&){}
    if(tiny.node_count()!=before_again)
        throw std::runtime_error("partial path inserted on out-of-memory");
    std::cout<<"PASS host-only segmented tree: 3000 distinct keys, "
            <<tree.node_count()<<" nodes / "<<tree.segment_count()<<" segments; "
            <<"first boundary on key "<<crossed_31_at
            <<"; stable handles, memorization, inheritance copy, atomic refusal\n";
}
