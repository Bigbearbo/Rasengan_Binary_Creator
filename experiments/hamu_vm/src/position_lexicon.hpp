#pragma once
#include <vector>
#include <string>
#include <stdexcept>
#include <utility>
#include <map>

// One explicitly selected grammar context; widths are information bits,
// excluding the k=1 tail. The caller supplies context and remembers state.
struct PositionLexicon {
    std::vector<int> widths;
    std::vector<std::map<int,std::map<int,std::string>>> meanings; // position -> order -> ID -> meaning
    explicit PositionLexicon(std::vector<int> n):widths(std::move(n)),meanings(widths.size()) {
        for(int width:widths)if(width<1||width>7)throw std::invalid_argument("word width");
    }
    struct Word {int id;int order;bool promoted;bool meaning_known;std::string meaning;};
    std::vector<Word> read(const std::string& bits) {
        std::vector<int> next=widths;
        std::vector<Word> words;
        size_t at=0;
        for(size_t i=0;i<widths.size();++i) {
            const int n=widths[i];
            if(at+size_t(n+1)>bits.size())throw std::invalid_argument("incomplete word");
            int id=0;
            for(int j=0;j<n;++j) {
                if(bits[at]!='0'&&bits[at]!='1')throw std::invalid_argument("bit");
                id=(id<<1)+(bits[at++]-'0');
            }
            const char tail=bits[at++];
            if(tail!='0'&&tail!='1')throw std::invalid_argument("bit");
            const bool promoted=tail=='1';
            if(promoted) {
                if(n==7||at>=bits.size()||bits[at++]!='0')
                    throw std::invalid_argument("one-step promotion");
                id=(id<<1)|1;
                next[i]=n+1;
            }
            std::string meaning;
            const auto entries=meanings[i].find(next[i]);
            if(entries!=meanings[i].end()) {
                const auto found=entries->second.find(id);
                if(found!=entries->second.end())meaning=found->second;
            }
            words.push_back({id,next[i],promoted,!meaning.empty(),meaning});
        }
        if(at!=bits.size())throw std::invalid_argument("trailing bits");
        widths=std::move(next); // update only after the entire message parses
        return words;
    }
};
