#pragma once
#include "hamu_vm_core.hpp"
#include <stdexcept>

struct LayerPacket {
    int operator_id, operator_order, data_value, data_order;
    std::vector<bool> bits;
};

inline std::vector<bool> encode_layer_packet(int op,int op_n,int data,int data_n) {
    std::vector<bool> bits={0,0,1}; // activate k=2; not an ordinary token
    auto append=[&](int id,int n,int k) {
        for(bool b:SpiralToken(id,n,k).bits)bits.push_back(b);
    };
    append(1,3,2); // MATH
    append(6,3,2); // QUESTION
    append(7,3,2); // end layer 2, enter layer 1
    append(op,op_n,1);
    append(data,data_n,1);
    append(15,4,1); // end layer 1; no parent layer remains
    return bits;
}

// Reference oracle: the two n values are per-position context. This is not
// an agent learning them or a self-delimiting parser without a length table.
inline LayerPacket parse_layer_packet(const std::vector<bool>& bits,int op_n,int data_n) {
    if(op_n<1||data_n<1||op_n>5||data_n>5)
        throw std::invalid_argument("invalid position lengths");
    size_t offset=0;
    auto exact=[&](std::initializer_list<bool> expected) {
        for(bool bit:expected) {
            if(offset>=bits.size()||bits[offset++]!=bit)
                throw std::invalid_argument("wrong layer prefix");
        }
    };
    auto token=[&](int n,int k) {
        if(offset+size_t(n+k)>bits.size())throw std::invalid_argument("short token");
        int id=0;
        for(int i=0;i<n;++i)id=(id<<1)|bits[offset++];
        for(int i=0;i<k;++i)if(bits[offset++])
            throw std::invalid_argument("wrong tail for current layer");
        return id;
    };
    exact({0,0,1});
    if(token(3,2)!=1||token(3,2)!=6||token(3,2)!=7)
        throw std::invalid_argument("wrong layer-2 structure");
    LayerPacket result;
    result.operator_order=op_n;result.data_order=data_n;
    result.operator_id=token(op_n,1);
    result.data_value=token(data_n,1);
    if(token(4,1)!=15)throw std::invalid_argument("missing layer-1 end");
    if(offset!=bits.size())throw std::invalid_argument("extra words");
    result.bits=bits;
    return result;
}
