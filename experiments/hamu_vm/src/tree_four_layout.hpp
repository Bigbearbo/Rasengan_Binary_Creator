#pragma once
#include <array>
#include <stdexcept>

// Candidate order and tree action codes are deliberately distinct. Existing
// COPY=00 and FLIP=10 actions retain their meanings.
inline constexpr std::array<int,4> tree_four_actions={0,2,1,3};
inline int tree_four_index(int slot){
    if(slot!=57&&slot!=70)throw std::invalid_argument("pending slot");
    return slot==57?0:1;
}
inline int tree_four_mask(int slot){return 110+4*tree_four_index(slot);}
inline int tree_four_action(int slot){return 118+2*tree_four_index(slot);}
inline int tree_four_format(int slot){return 122+tree_four_index(slot);}
inline int tree_observed_format(int slot){return 156+tree_four_index(slot);}
