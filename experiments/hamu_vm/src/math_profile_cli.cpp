#include "math_profile.hpp"
#include <iostream>
#include <string>
int main() {
    int n,layer;
    std::string bits;
    while(std::cin>>n>>layer>>bits) {
        try {
            auto r=parse_math_profile(bits,n,layer);
            std::cout<<r.answer_bits<<' '<<r.value<<'\n';
        } catch(const MathProfileError& e) {
            std::cout<<e.status<<' '<<e.bit_offset<<'\n';
        } catch(const std::exception&) {
            std::cout<<"ERROR\n";
        }
    }
}
