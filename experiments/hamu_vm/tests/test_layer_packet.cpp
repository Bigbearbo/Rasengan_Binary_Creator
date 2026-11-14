#include "../src/layer_packet.hpp"
#include <iostream>

int main() {
    int count=0;
    for(int op_n:{2,3})for(int data_n:{2,3})
        for(int op:{0,1})for(int value=0;value<(1<<data_n);++value) {
            const auto bits=encode_layer_packet(op,op_n,value,data_n);
            const auto parsed=parse_layer_packet(bits,op_n,data_n);
            if(parsed.operator_id!=op||parsed.data_value!=value||
               parsed.bits!=bits)return 1;
            ++count;
        }
    // Identical bits need different (layer, order) keys.
    const auto math=SpiralToken(1,3,2).bits;
    const auto low=SpiralToken(2,4,1).bits;
    const auto end=SpiralToken(7,3,2).bits;
    const auto prev=SpiralToken(14,4,1).bits;
    if(math!=low||end!=prev)return 2;
    const auto bits=encode_layer_packet(1,3,5,3);
    if(bits.size()!=3+3*5+4+4+5 ||
       parse_layer_packet(bits,3,3).data_value!=5)return 3;
    std::cout<<"PASS 48 L2->L1 packets, mixed operator/data lengths;"
                " 00100 and 11100 are context-dependent codes\n";
}
