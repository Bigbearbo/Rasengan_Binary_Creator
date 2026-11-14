#include "../src/math_profile.hpp"
#include <cassert>
#include <iostream>
#include <vector>

int main() {
    int cases=0;
    auto check=[&](int n,int layer,int a,int op,int b,int expected) {
        std::string bits=layer==1?"01":"001"+math_word(1,3,2)+math_word(6,3,2)+math_word(7,3,2);
        bits+=math_word(a,n);
        if(op!=15)bits+=math_word(op,n);
        if(b>=0)bits+=math_word(b,n);
        bits+=math_word(15,n);
        const auto got=parse_math_profile(bits,n,layer);
        assert(got.value==expected);
        assert(got.answer_bits==math_word(expected,n)+math_word(15,n));
        ++cases;
    };
    for(int n:{4,5})for(int layer:{1,2}) {
        for(int a=0;a<=10;++a)check(n,layer,a,15,-1,a);
        for(int a=0;a<10;++a)check(n,layer,a,13,-1,a+1);
        for(int a=1;a<=10;++a)check(n,layer,a,14,-1,a-1);
        for(int a=0;a<=10;++a)for(int b=0;a+b<=10;++b)check(n,layer,a,12,b,a+b);
        for(int a=0;a<=10;++a)for(int b=0;b<=a;++b)check(n,layer,a,11,b,a-b);
    }
    assert(cases==652);
    // Hand-checked 5+3 -> 8, plus same bit pattern has different meanings by layer.
    assert(parse_math_profile("00100100110001110001010110000011011110",4,2).value==8);
    assert(math_word(2,4)==math_word(1,3,2));
    auto rejects=[&](const std::string& bits,int n,int layer) {
        try {(void)parse_math_profile(bits,n,layer);return false;}
        catch(const std::invalid_argument&) {return true;}
        catch(const std::out_of_range&) {return true;}
    };
    auto frame=[](int a,int op,int b=-1) {
        auto bits=std::string("01")+math_word(a,4)+math_word(op,4);
        if(b>=0)bits+=math_word(b,4);
        return bits+math_word(15,4);
    };
    assert(rejects(frame(10,13),4,1)); // successor overflow
    assert(rejects(frame(0,14),4,1));  // predecessor underflow
    assert(rejects(frame(10,12,1),4,1));
    assert(rejects(frame(0,11,1),4,1));
    assert(rejects("01"+math_word(2,4)+math_word(15,4)+"0",4,1));
    assert(rejects("01"+math_word(2,4)+math_word(13,4)+"11111",4,1));
    auto diagnostic=[&](const std::string& bits,int n,const std::string& code,size_t offset) {
        try {(void)parse_math_profile(bits,n,1);assert(false);}
        catch(const MathProfileError& e) {assert(e.status==code&&e.bit_offset==offset);}
    };
    diagnostic("01"+math_word(16,5)+math_word(15,5),5,"UNKNOWN_TOKEN",2);
    diagnostic("01"+math_word(0,5)+math_word(16,5)+math_word(15,5),5,"UNKNOWN_TOKEN",8);
    diagnostic(frame(10,13),4,"NUMERIC_RANGE",7);
    diagnostic("01"+math_word(0,4)+math_word(13,4)+"11111",4,"BAD_SUFFIX",16);
    std::cout<<"PASS math-v0.1 reference: "<<cases<<" representations\n";
}
