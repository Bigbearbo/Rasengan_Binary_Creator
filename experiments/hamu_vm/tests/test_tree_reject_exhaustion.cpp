// Independent policy/invariant test. Does not alter VM ABI or claim guest policy integration.
#define main previous_reject_mask_main
#include "test_tree_reject_mask.cpp"
#undef main
#include <optional>
static std::optional<int> choose_unrejected(Hamster& h,int id){
    for(int c=0;c<8;++c)if(!rejected(h,id,c))return c;
    return std::nullopt;
}
int main(){
    int checks=0;
    for(int mask=0;mask<256;++mask){
        Hamster h(mask+100,cfg(true,2));
        set_id_candidate(h,0,0);execute(h,{28,1,15,0});
        for(int c=0;c<8;++c)if(mask&(1<<c))mark(h,1,c);
        auto chosen=choose_unrejected(h,1);
        int expected=-1;
        for(int c=0;c<8;++c)if(!(mask&(1<<c))){expected=c;break;}
        require(chosen.value_or(-1)==expected,"selection violates rejected-mask invariant");
        require(chosen.has_value()==(mask!=255),"exhausted mask not detected");
        const auto original=h.segment_pages;
        if(chosen){mark(h,1,*chosen);require(rejected(h,1,*chosen),"candidate not marked");}
        else require(h.segment_pages==original,"exhausted policy mutated canonical pages");
        ++checks;
    }
    std::cout<<"PASS 256 masks: never select rejected, deterministic lowest available, 0xff exhaustion explicit\n";
}
