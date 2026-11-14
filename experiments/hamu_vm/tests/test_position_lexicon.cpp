#include "../src/position_lexicon.hpp"
#include <cassert>
#include <iostream>
int main() {
    PositionLexicon a({1,2,1}),b({2,1}); // physical 2,3,2 and 3,2
    a.meanings[1][2]={{1,"old one"},{3,"old three"}};
    auto first=a.read("0001000"); // 00 | 010 | 00
    assert(first.size()==3&&first[1].id==1&&first[1].meaning_known);
    auto other=b.read("01010"); // 010 | 10
    assert(other.size()==2&&b.widths[0]==2&&b.widths[1]==1);
    auto changed=a.read("00011010"); // 00 | 0110 | 10
    assert(changed[1].promoted&&changed[1].id==3&&changed[1].order==3);
    assert(!changed[1].meaning_known&&a.widths[0]==1&&a.widths[1]==3&&a.widths[2]==1);
    assert(b.widths[0]==2&&b.widths[1]==1);
    a.meanings[1][3][3]="new three"; // explicit new-order dictionary action
    auto again=a.read("00011010");
    assert(!again[1].promoted&&again[1].meaning_known&&again[1].id==3);
    auto old_number=a.read("00001010"); // 00 | 0010 | 10: left-pad old ID 1
    assert(old_number[1].id==1&&!old_number[1].meaning_known&&!old_number[1].promoted);
    a.meanings[1][3][1]="new one"; // numeric continuity does not imply semantic continuity
    assert(a.read("00001010")[1].meaning_known);
    bool rejected=false;
    try {(void)a.read("0001101");}catch(const std::invalid_argument&){rejected=true;}
    assert(rejected&&a.widths[1]==3);
    PositionLexicon simultaneous({1,2,1});
    auto twice=simultaneous.read("010010110"); // 010 | 010 | 110
    assert(twice[0].promoted&&twice[0].id==1&&twice[0].order==2);
    assert(!twice[1].promoted&&twice[1].id==1&&twice[1].order==2);
    assert(twice[2].promoted&&twice[2].id==3&&twice[2].order==2);
    assert((simultaneous.widths==std::vector<int>{2,2,2}));
    PositionLexicon atomic({1,2,1});
    rejected=false;
    try {(void)atomic.read("01001011");}catch(const std::invalid_argument&){rejected=true;}
    assert(rejected&&(atomic.widths==std::vector<int>{1,2,1}));
    PositionLexicon concept({6});
    concept.meanings[0][6][1]="Newton apple story";
    concept.meanings[0][7][1]="universal gravitation";
    auto six=concept.read("0000010"); // n=6, id=1, k=1
    assert(six[0].id==1&&six[0].meaning=="Newton apple story");
    auto seven=concept.read("00000010"); // old tail becomes 1, n=7, id=1
    assert(seven[0].promoted&&seven[0].id==1&&
           seven[0].meaning=="universal gravitation");
    std::cout<<"PASS position widths: a 2,3,2 -> 2,4,2; b 3,2 unchanged; meaning separate\n";
}
