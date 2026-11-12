#pragma once
#include <string>
#include <stdexcept>
#include <utility>

// Fixed math-v0.1 reference parser. The configured width is not inferred
// from the bits; this profile is separate from the adaptive hamster VM.
struct MathResult { int value; std::string answer_bits; };
// UNKNOWN_TOKEN means a well-formed word absent from this dictionary; its
// meaning remains open. This fixed profile does not perform adaptive growth.
struct MathProfileError : std::invalid_argument {
    std::string status;
    size_t bit_offset;
    MathProfileError(std::string code,size_t offset):
        std::invalid_argument(code),status(std::move(code)),bit_offset(offset) {}
};
inline std::string math_word(int id,int n,int k=1) {
    if(n<1||n>5||k<1||k>2||id<0||id>=(1<<n))throw std::invalid_argument("word range");
    std::string s;
    for(int b=n-1;b>=0;--b)s.push_back((id>>b)&1?'1':'0');
    return s+std::string(k,'0');
}
inline MathResult parse_math_profile(const std::string& bits,int n,int layer) {
    if((n!=4&&n!=5)||(layer!=1&&layer!=2))throw MathProfileError("BAD_INPUT",0);
    size_t at=0;
    auto literal=[&](const std::string& t){
        if(bits.compare(at,t.size(),t)!=0)throw MathProfileError("SYNTAX",at);
        at+=t.size();
    };
    if(layer==1)literal("01");
    else {literal("001");literal(math_word(1,3,2));literal(math_word(6,3,2));literal(math_word(7,3,2));}
    auto word=[&]() {
        if(at+size_t(n+1)>bits.size())throw MathProfileError("TRUNCATED",bits.size());
        int id=0;
        for(int i=0;i<n;++i) {
            const char c=bits[at++];
            if(c!='0'&&c!='1')throw MathProfileError("BAD_INPUT",at-1);
            id=id*2+(c-'0');
        }
        if(bits[at++]!='0')throw MathProfileError("BAD_SUFFIX",at-1);
        return id;
    };
    const size_t a_at=at;
    const int a=word();
    if(a>15)throw MathProfileError("UNKNOWN_TOKEN",a_at);
    if(a>10)throw MathProfileError("SYNTAX",a_at);
    const size_t op_at=at;
    const int op=word();
    int value=0;
    if(op==15)value=a;
    else if(op==13)value=a+1;
    else if(op==14)value=a-1;
    else if(op==11||op==12) {
        const size_t b_at=at;
        const int b=word();
        if(b>15)throw MathProfileError("UNKNOWN_TOKEN",b_at);
        if(b>10)throw MathProfileError("SYNTAX",b_at);
        value=op==12?a+b:a-b;
    } else throw MathProfileError(op>15?"UNKNOWN_TOKEN":"SYNTAX",op_at);
    if(op!=15) {
        const size_t period_at=at;
        const int period=word();
        if(period!=15)throw MathProfileError(period>15?"UNKNOWN_TOKEN":"SYNTAX",period_at);
    }
    if(at!=bits.size())throw MathProfileError("SYNTAX",at);
    if(value<0||value>10)throw MathProfileError("NUMERIC_RANGE",op_at);
    return {value,math_word(value,n)+math_word(15,n)};
}
