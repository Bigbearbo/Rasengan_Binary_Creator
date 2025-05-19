// 20250520
#include <vector>
#include <iostream>
#include <stdexcept>
#include <cstdlib>
#include <ctime>
#include <unordered_map>
#include <string>
#include <bitset>
#include <iomanip>
using namespace std;

const int ROUND_outside=500;
const int ROUND=100;
const int Hamu_num=20;
const bool op_print=false;
const bool mem_print=false;
const int mem_p_size=60;
const int deth_loop_num=10;
const int Change_rate = 100;
const float basic_use = 0.5;

struct SpiralToken {
    int value;
    int order;
    int level;
    std::vector<bool> bits;
    SpiralToken() : value(0), order(0), level(0) {};
    SpiralToken(int val, int ord, int lvl) {
        if (val >= (1 << ord)) {
            throw std::invalid_argument("Value exceeds maximum for given order.");
        }
        value = val;
        order = ord;
        level = lvl;

        for (int i = ord - 1; i >= 0; --i)
            bits.push_back((val >> i) & 1);
        for (int i = 0; i < lvl; ++i)
            bits.push_back(0);
    }

    void print() const {
        std::cout << "Value: " << value
                  << " | Order(n): " << order
                  << " | Level(k): " << level
                  << " | Code: ";
        for (bool b : bits) std::cout << (b ? '1' : '0');
        std::cout << std::endl;
    }
};

// 解碼函式：由螺旋碼 bits 還原 value, order, level
SpiralToken decodeSpiral(const std::vector<bool>& code) {
    int n = code.size();
    if (n == 0) throw std::invalid_argument("Empty code");

    int level = 0;
    for (int i = n - 1; i >= 0; --i) {
        if (code[i] == 0) level++;
        else break;
    }

    int order = n - level;
    int value = 0;
    for (int i = 0; i < order; ++i) {
        value = (value << 1) | code[i];
    }

    return SpiralToken(value, order, level);
}

// 運算符對應值
const std::vector<int> OpCodes = {11, 12, 13, 14}; // - + → ←
const int END_CODE = 15;

enum class ProblemType {
    COUNTING,
    ARITHMETIC
};

struct Problem {
    ProblemType type;
    std::vector<SpiralToken> question;
    SpiralToken answer;
    std::string readable;
};

Problem generateOneProblem(int order, int level) {
    while (true) {
        int a = rand() % 11;
        int b = rand() % 11;
        int result = -999;
        int op = OpCodes[rand() % OpCodes.size()];
        //cout<<a<<" "<<b<<" "<<op<<endl;
        std::string opStr = "?";

        if (op == 12) { // +
            if (a + b > 10) continue;
            result = a + b;
            opStr = "+";
        } else if (op == 11) { // -
            if (a - b < 0) continue;
            result = a - b;
            opStr = "-";
        } else if (op == 13) { // →
            if (a + 1 > 10) continue;
            result = a + 1;
            opStr = "→";
        } else if (op == 14) { // ←
            if (a - 1 < 0) continue;
            result = a - 1;
            opStr = "←";
        }
        //cout<<"st";
        SpiralToken A(a, order, level);
        SpiralToken B(b, order, level);
        SpiralToken R(result, order, level);
        SpiralToken Op(op, order, level);
        SpiralToken End(END_CODE, order, level);
        //cout<<"ed"<<endl;
        std::vector<SpiralToken> q;
        q.push_back(A);
        q.push_back(Op);
        if (op == 12 || op == 11) q.push_back(B);
        q.push_back(End);

        std::string readable = std::to_string(a) + " " + opStr;
        if (op == 12 || op == 11) readable += " " + std::to_string(b);
        readable += " 。→ " + std::to_string(result);
        //return Problem{q, R, readable};
        ProblemType P_Type=ProblemType::COUNTING;
        if (op == 12 || op == 11)P_Type=ProblemType::ARITHMETIC;
        return Problem{P_Type, q, R, readable};
    }
    
}

std::vector<int> memory(32, 0);
int ptr = 0;
std::vector<int> val_reg;
int val_ptr = 0;

int bin_to_signed_int(const std::string& bin) {
    int val = std::bitset<4>(bin).to_ulong();
    return (val >= 8) ? val - 16 : val;
}

enum class SpiralOp {
    SET_AREA, MOVE_PTR, WRITE_1, WRITE_0, READ,
    XOR, AND, OR, MOVE_VAL_PTR, WRITE_VAL,
    INSERT, DELETE, SET_PTR1, SET_PTR2, 
    SMOVE_PTR, OUT_AREA,
    INVALID
};

SpiralOp decode_op(const std::string& token) {
    static const std::unordered_map<std::string, SpiralOp> op_map = {
        {"00000", SpiralOp::SET_AREA}, {"00010", SpiralOp::MOVE_PTR},
        {"00100", SpiralOp::WRITE_1},  {"00110", SpiralOp::WRITE_0},
        {"01000", SpiralOp::READ},     {"01010", SpiralOp::XOR},
        {"01100", SpiralOp::AND},      {"01110", SpiralOp::OR},
        {"10000", SpiralOp::MOVE_VAL_PTR}, {"10010", SpiralOp::WRITE_VAL},
        {"10100", SpiralOp::INSERT},   {"10110", SpiralOp::DELETE},
        {"11000", SpiralOp::SET_PTR1}, {"11010", SpiralOp::SET_PTR2},
        {"11100", SpiralOp::SMOVE_PTR}, {"11110", SpiralOp::OUT_AREA}
    };
    auto it = op_map.find(token);
    return it != op_map.end() ? it->second : SpiralOp::INVALID;
}

SpiralOp decode_op(const SpiralToken& token) {
    static const std::vector<std::pair<std::vector<bool>, SpiralOp>> op_map = {
        {{0,0,0,0,0}, SpiralOp::SET_AREA},
        {{0,0,0,1,0}, SpiralOp::MOVE_PTR},
        {{0,0,1,0,0}, SpiralOp::WRITE_1},
        {{0,0,1,1,0}, SpiralOp::WRITE_0},
        {{0,1,0,0,0}, SpiralOp::READ},
        {{0,1,0,1,0}, SpiralOp::XOR},
        {{0,1,1,0,0}, SpiralOp::AND},
        {{0,1,1,1,0}, SpiralOp::OR},
        {{1,0,0,0,0}, SpiralOp::MOVE_VAL_PTR},
        {{1,0,0,1,0}, SpiralOp::WRITE_VAL},
        {{1,0,1,0,0}, SpiralOp::INSERT},
        {{1,0,1,1,0}, SpiralOp::DELETE},
        {{1,1,0,0,0}, SpiralOp::SET_PTR1},
        {{1,1,0,1,0}, SpiralOp::SET_PTR2},
        {{1,1,1,0,0}, SpiralOp::SMOVE_PTR},
        {{1,1,1,1,0}, SpiralOp::OUT_AREA}
    };

    for (const auto& [pattern, op] : op_map) {
        if (token.bits.size() >= pattern.size()) {
            bool match = true;
            for (size_t i = 0; i < pattern.size(); ++i) {
                if (token.bits[i] != pattern[i]) {
                    match = false;
                    break;
                }
            }
            if (match) return op;
        }
    }

    return SpiralOp::INVALID;
}

std::string op_to_string(SpiralOp op) {
    switch (op) {
        case SpiralOp::SET_AREA: return "0 set_area";
        case SpiralOp::MOVE_PTR: return "1 move_ptr";
        case SpiralOp::WRITE_1: return "2 write_1";
        case SpiralOp::WRITE_0: return "3 write_0";
        case SpiralOp::READ: return "4 read";
        case SpiralOp::XOR: return "5 xor";
        case SpiralOp::AND: return "6 and";
        case SpiralOp::OR: return "7 or";
        case SpiralOp::MOVE_VAL_PTR: return "8 move_val_ptr";
        case SpiralOp::WRITE_VAL: return "9 write_val";
        case SpiralOp::INSERT: return "10 insert";
        case SpiralOp::DELETE: return "11 delete";
        case SpiralOp::SET_PTR1: return "12 set_ptr1";
        case SpiralOp::SET_PTR2: return "13 set_ptr2";
        case SpiralOp::SMOVE_PTR: return "14 smove_ptr";
        case SpiralOp::OUT_AREA: return "15 out_area";
        default: return "invalid";
    }
}
        
        

struct HamsterParams {
    int initial_hp = 20;
    int max_hp = 40;
    int mature_age = 10;
    int reward_correct = 5;
    int penalty_wrong = 10;
    int unit_cost_per = 600; 
    int add_hp_ratio = 2;
    int op_order = 4;
    int op_lvl = 1;

    struct {
        int input_start = 0;
        int status_start = 32;
        int output_start = 40;
        int work_start = 60;
        int program_start = 180;
        int total_size = 256;
        int val_reg_size = 32;
    } layout;
    
    struct {
        int pro_1 = 181;
        int pro_2 = 255;
    } ptr;
};

struct Hamster {
    int id;
    HamsterParams params;
    float hp;
    float max_hp_his;
    int max_hp_age_his;
    std::vector<bool> memory_his;
    std::vector<bool> val_reg_his;
    bool creat_his;
    
    int age;
    int ptr;
    int val_ptr;
    int pro_1;
    int pro_2;
    bool stop;
    
    std::vector<bool> memory;
    std::vector<bool> val_reg;
    std::vector<std::string> result_log;
    int correct_count_counting = 0;
    int correct_count_arith = 0;
    int incorrect_count = 0;

    Hamster(int _id, const HamsterParams& p) : id(_id), params(p), hp(p.initial_hp), age(0) {
        memory = std::vector<bool>(params.layout.total_size, 0);
        val_reg = std::vector<bool>(params.layout.val_reg_size, 0);
        
        memory_his = std::vector<bool>(params.layout.total_size, 0);
        val_reg_his = std::vector<bool>(params.layout.val_reg_size, 0);
        
        
        pro_1=params.layout.program_start+1-50;
        pro_2=params.layout.total_size-1;
        hp=params.initial_hp;
        max_hp_his=hp;
        creat_his = false;
        ptr=0;
        val_ptr=0;
        stop=false;
    }
    
    void set_mem_rand() {
        for (int i = params.layout.output_start; i < params.layout.total_size; ++i) {
            memory[i] = rand() % 2;
        }
    }
    
    bool is_alive() const {
        return hp > 0;
    }
    
    
    void write_prob(const Problem& p) {
        int start = params.layout.input_start;
        int end = params.layout.status_start;
        int idx = start;
    
        // 將題目 token bits 寫入 input 區
        for (const auto& token : p.question) {
            for (bool bit : token.bits) {
                if (idx >= end) break; // 避免越界寫到狀態區
                memory[1+idx++] = bit;
            }
        }
    
        // 補 0（清空未使用部分）
        while (idx < end) {
            memory[idx++] = 0;
        }
    
        // 設定 control bit：input_start 位置標記為有效
        memory[start] = 1;
    }
    
    void status_ref() {
        int start = params.layout.status_start;
        int end = params.layout.output_start;
        hp -= basic_use;
        SpiralToken s(int(hp), 7, 1); // 血量轉螺旋碼（order=7可表示0~127）
    
        int max_bits = end - start;
        if (s.bits.size() > max_bits) {
            std::cout << "[Hamster#" << id << "] 狀態區不足，血量無法完整寫入\n";
            return;
        }
    
        for (int i = 0; i < s.bits.size(); ++i)
            memory[start + i] = s.bits[i];
        
        // 補零（保持區段清潔）
        for (int i = s.bits.size(); i < max_bits; ++i)
            memory[start + i] = 0;
        
        ptr=0;
        val_ptr=0;
        
        pro_2=params.layout.total_size-1;
        pro_1=params.layout.program_start+1-50;
        stop=false;
        
    }
    
    void new_his(){
        creat_his = true;
        memory_his = memory;
        val_reg_his = val_reg;
        max_hp_his = hp;
        max_hp_age_his = age;
    }
    
    void copy_hamu(Hamster& h2){
        memory = h2.memory_his;
        val_reg = h2.val_reg_his;
    }
    
    void change_hamu(int r){
        
        for(int i=0;i<memory.size();i++){
            if(rand()%r==1){
                memory[i] = !memory[i];
            }
        }
        
    }
    
    void use_hp() {
        float cost = float(pro_2-pro_1)/float(params.unit_cost_per);
        hp -= cost;
    }
    
    void add_hp(Problem& p){
        if(p.type==ProblemType::COUNTING)hp += params.add_hp_ratio;
        else hp += params.add_hp_ratio*2;
        if(hp>params.max_hp) hp = params.max_hp;
    }
    
    void record_result(bool correct, const Problem& prob) {
        std::string entry = (correct ? "[O] " : "[X] ") + prob.readable;
        result_log.push_back(entry);
        if (correct) {
            if (prob.type == ProblemType::COUNTING) ++correct_count_counting;
            else ++correct_count_arith;
            //hp += params.reward_correct;
        } else {
            ++incorrect_count;
            //hp -= params.penalty_wrong;
        }
        //if (hp > 100) hp = 100;
    }

    void print_summary() const {
        std::cout << "Hamster#" << id
                  << " | HP: " << std::setw(3) << hp
                  << " | Age: " << std::setw(2) << age
                  << " | COUNTING: " << correct_count_counting
                  << " | ARITH: " << correct_count_arith
                  << " | WRONG: " << incorrect_count << std::endl;
    }
    void print_ptr(){
        cout<<"ptr= "<<ptr<<" val_ptr= "<<val_ptr<<
        " pro1= "<<pro_1<<" pro2= "<<pro_2<<endl;
    }
};
/*
bool Check_ans(Hamster& h,Problem p){
    for(int i=0;i<p.answer.bits.size()){
        if(p.answer.bits[i]!=h.memory[h.params.layout.output_start+1+i])
            return false;
    }
    return true;
}*/

bool Check_ans(Hamster& h, const Problem& p) {
    const int out_base = h.params.layout.output_start;
    const int out_data_start = out_base + 1;
    /*
    // 檢查 control bit 是否啟用（倉鼠是否真的填答案）
    if (h.memory[out_base] == 0) {
        //std::cout << "[Hamster#" << h.id << "] 未填答案\n";
        return false;
    }
    */
    // 比對答案
    for (int i = 0; i < p.answer.bits.size(); ++i) {
        if (p.answer.bits[i] != h.memory[out_data_start + i+1]) {
            return false;
        }
    }
    return true;
}
void dump_memory() {
    std::cout << "Memory  [";
    for (int i = 0; i < memory.size(); ++i)
        std::cout << memory[i];
    std::cout << "]\n";
    std::cout << "val_reg [";
    for (int i = 0; i < val_reg.size(); ++i)
        std::cout << val_reg[i];
    std::cout << "]\n";
    std::cout << "ptr=" << ptr << " val_ptr=" << val_ptr << "\n\n";
}

std::ostream& operator<<(std::ostream& os, const SpiralToken& token) {
    os << "token=(" << token.value
       //<< ", ord=" << token.order
       //<< ", lvl=" << token.level
       << ", bits=";
    for (bool b : token.bits) os << (b ? '1' : '0');
    os << ")";
    return os;
}

void simulate_spiral_program(Hamster& h) {
    
    int loop_num=0;
    int lvl = h.params.op_lvl;
    
    static bool mem_old[mem_p_size];
    
    //if(h.memory[h.params.layout.program_start] == 0)return;
    int op_order = h.params.op_order;
    int tokens_size = (h.pro_2 - h.pro_1+1) / (op_order+lvl);
    std::vector<SpiralToken> tokens;
    int move_width = op_order+lvl;
    
    for(int i = 0; i < tokens_size; i++) {
        int op_to_num = 0;
        // stop if loop
        if(loop_num > deth_loop_num){
            cout<<"Loop stop"<<endl;
            return;
        }
        // 檢查這次操作是否會越界
        int start_idx = 1 + h.pro_1 + i * (op_order + lvl);
        int end_idx = start_idx + op_order; // 不含end_idx
    
        if(end_idx > h.memory.size()) {
            std::cerr << "Memory access out of bounds when reading token " << i << std::endl;
            break;
        }
    
        for(int j = 0; j < op_order; j++) {
            op_to_num += h.memory[start_idx + j];
            op_to_num *= 2;
        }
        op_to_num /= 2;
    
        tokens.push_back(SpiralToken(op_to_num, op_order, lvl));
    }
    
    for (size_t i = 0; i < tokens_size;) {
        int op_len=2;
        SpiralOp op = decode_op(tokens[i]);
        
        
        if (op == SpiralOp::INVALID) {
            if(op_print)std::cout << "[Hamster#" << h.id << "] Invalid op token: " << tokens[i] << "\n";
            ++i;
            continue;
        }
        
        // not SpiralToken
        if(tokens[i].bits[move_width-1] == 1){
            i += 1;
            continue;
        }
        // no param exit
            
        if (op == SpiralOp::OUT_AREA) {
            if(op_print)std::cout << "[Hamster#" << h.id << "] Op: out_area\n";
            op_len=1;
            // OUT_AREA will break 
            /*
            h.stop=true;
            return;
            */
            break;
        }
        
        if(i==tokens_size-1){
            i++;
            return;
            
        }
        
                
        if (i + 1 >= tokens_size) {
            if(op_print)std::cout << "[Hamster#" << h.id << "] Missing parameter for: " << tokens[i] << "\n";
            break;
        }
        
        int param=tokens[i+1].value;
        
        switch (op) {
            case SpiralOp::WRITE_1:
                for (int j = 0; j < param && h.ptr < h.memory.size(); ++j) {
                    int addr = h.ptr++;
                    if (addr >= h.params.layout.work_start) {
                        h.memory[addr] = 1;
                    }
                }
                break;
            case SpiralOp::WRITE_0:
                for (int j = 0; j < param && h.ptr < h.memory.size(); ++j) {
                    int addr = h.ptr++;
                    if (addr >= h.params.layout.work_start) {
                        h.memory[addr] = 0;
                    }
                }
                break;
            case SpiralOp::READ:

                for (int j = 0; j < param && (h.ptr + j) < h.memory.size(); ++j){
                    if(j+h.val_ptr>h.params.layout.val_reg_size-1)break;
                    h.val_reg[j+h.val_ptr] = h.memory[h.ptr + j];
                }
                //h.ptr += param;
                // move ptr after READ
                break;
                
            case SpiralOp::XOR:
                for (int j = 0; j < param && (h.ptr + j) < h.memory.size() && j < h.val_reg.size(); ++j)
                    h.memory[h.ptr + j] = h.memory[h.ptr + j] ^ h.val_reg[h.val_ptr+j];
                break;
            case SpiralOp::AND:
                for (int j = 0; j < param && (h.ptr + j) < h.memory.size() && j < h.val_reg.size(); ++j)
                    h.memory[h.ptr + j] = h.memory[h.ptr + j] & h.val_reg[h.val_ptr+j];
                break;
            case SpiralOp::OR:
                for (int j = 0; j < param && (h.ptr + j) < h.memory.size() && j < h.val_reg.size(); ++j)
                    h.memory[h.ptr + j] = h.memory[h.ptr + j] | h.val_reg[h.val_ptr+j];
                break;
            case SpiralOp::MOVE_PTR: {
                // 取得方向位元（用第一個 bit 控制方向）
                /*
                int dir_bit = tokens[i+1].bits[0];
                int direction = dir_bit ? +1 : -1;
            
                // 將 direction bit 乘上高權重（<< op_order-1）作為 bias 調整量
                int bias = dir_bit << (op_order - 1);
            
                // 真正位移量 = 螺旋數值 - 偏移 → *方向
                int move_amount = direction * (param - bias);
            
                h.ptr += (move_amount * move_width);
            
                // 邊界限制
                if (h.ptr < 0) h.ptr = 0;
                if (h.ptr >= (int)h.memory.size()) h.ptr = h.memory.size() - 1;
                break;
                */
                // param 來自 token[i+1] 的值，最高位為方向
                int total_bits = tokens[i+1].order;
                if (total_bits < 1) break;
            
                int raw_val = tokens[i+1].value;
                int dir_bit = (raw_val >> (total_bits - 1)) & 1;
                int magnitude = raw_val & ((1 << (total_bits - 1)) - 1);
                
                int direction = dir_bit ? +1 : -1;
                //cout<<"Move "<<direction * magnitude * move_width<<endl;
                h.ptr += direction * magnitude * move_width;
            
                // 邊界修正
                h.ptr = std::max(0, std::min(h.ptr, (int)h.memory.size() - 1));
                break;

            }
            
            case SpiralOp::SMOVE_PTR: {
                // 取得方向位元（用第一個 bit 控制方向）
                int dir_bit = tokens[i+1].bits[0];
                int direction = dir_bit ? +1 : -1;
            
                // 將 direction bit 乘上高權重（<< op_order-1）作為 bias 調整量
                int bias = dir_bit << (op_order - 1);
            
                // 真正位移量 = 螺旋數值 - 偏移 → *方向
                int move_amount = direction * (param - bias);
            
                h.ptr += move_amount;
            
                // 邊界限制
                if (h.ptr < 0) h.ptr = 0;
                if (h.ptr >= (int)h.memory.size()) h.ptr = h.memory.size() - 1;
                break;
            }
            
            case SpiralOp::MOVE_VAL_PTR: {
                int dir_bit = tokens[i+1].bits[0];
                int direction = dir_bit ? +1 : -1;
            
                // 將 direction bit 乘上高權重（<< op_order-1）作為 bias 調整量
                int bias = dir_bit << (op_order - 1);
            
                // 真正位移量 = 螺旋數值 - 偏移 → *方向
                int move_amount = direction * (param - bias);
            
                h.val_ptr += move_amount * move_width;
            
                // 邊界限制
                if (h.val_ptr < 0) h.val_ptr = 0;
                if (h.val_ptr >= h.params.layout.val_reg_size) 
                    h.val_ptr = h.params.layout.val_reg_size - 1;
                /*
                h.val_ptr += param;
                if (h.val_ptr < 0) h.val_ptr = 0;
                if (h.val_ptr >= (int)h.val_reg.size()) h.val_ptr = h.val_reg.size() - 1;
                */
                break;
            }
            case SpiralOp::SET_PTR1: {
                int dir_bit = tokens[i+1].bits[0];
                int direction = dir_bit ? +1 : -1;
                int bias = dir_bit << (op_order - 1);
                int move_amount = direction * (param - bias) ;
            
                h.pro_1 += move_amount * move_width;
                if (h.pro_1 < 0) h.pro_1 = 0;
                if (h.pro_1 > h.params.layout.total_size) h.pro_1 = h.params.layout.total_size - 1;
                break;
            }    
            case SpiralOp::SET_PTR2: {
                int dir_bit = tokens[i+1].bits[0];
                int direction = dir_bit ? +1 : -1;
                int bias = dir_bit << (op_order - 1);
                int move_amount = direction * (param - bias);
            
                h.pro_2 += move_amount * move_width;
                if (h.pro_2 < 0) h.pro_2 = 0;
                if (h.pro_2 > h.params.layout.total_size) h.pro_2 = h.params.layout.total_size - 1;
                break;
            }
            
           
            case SpiralOp::SET_AREA:
                if(param%8==0) ;//h.ptr=0;
                else if(param%8==1) h.ptr=h.params.layout.status_start;
                else if(param%8==2) h.ptr=h.params.layout.output_start;
                else if(param%8==3) h.ptr=h.params.layout.work_start;
                else if(param%8==4) h.ptr=h.params.layout.work_start+10*(op_order+lvl);
                else if(param%8==5) h.ptr=h.pro_1;
                else if(param%8==6) h.ptr=h.pro_2;
                //else if(param%8==7) h.ptr=h.params.layout.total_size;
                else if(param%8==7) h.stop=true;
                
                break;
                
            case SpiralOp::WRITE_VAL:
                for (int j = 0; j < param && (h.ptr + j) < h.memory.size() && j < h.val_reg.size(); ++j) {
                    int addr = h.ptr + j;
                    if (addr >= h.params.layout.output_start) {
                        h.memory[addr] = h.val_reg[val_ptr+j];
                    }
                }
                break;
            
            case SpiralOp::INSERT:
            // 在 ptr 位置插入 val_reg 中的前 param 個位元，後方位元右移
                for (int j = h.params.layout.total_size - 1; j >= h.ptr + param; --j) {
                    if (j < h.memory.size() && j - param >= 0)
                        h.memory[j] = h.memory[j - param];
                }
                for (int j = 0; j < param && j + h.val_ptr < h.val_reg.size(); ++j) {
                    if (h.ptr + j < h.memory.size())
                        h.memory[h.ptr + j] = h.val_reg[j + h.val_ptr];
                }
                break;
            
            case SpiralOp::DELETE:
            // 刪除 ptr 位置後 param 個位元，後方位元左移填補
                for (int j = h.ptr; j + param < h.memory.size(); ++j) {
                    h.memory[j] = h.memory[j + param];
                }
                for (int j = h.memory.size() - param; j < h.memory.size(); ++j) {
                    h.memory[j] = rand() %2 ;
                }
                break;
            
            
            
                        default:
                break;
        }

        // Optional: debug memory snapshot
        
        if(op_print){
            cout<<tokens[i].value<<" "<<tokens[i+1].value<<" "<<param<<endl;
            cout<<"Op="<<op_to_string(op)<<" i="<<i<<" "<<tokens[i]<<" "<<param<<" ";
            if(i+1<tokens_size)cout<<tokens[i+1]<<" ";
            std::cout << "[Hamster#" << h.id << "] Mem[ptr=" << h.ptr << "] ";
        }
        if(mem_print){
            /*
            for (int j = -8; j < 16; ++j) 
                if(h.ptr + j>=0 && h.ptr + j<h.params.layout.total_size)
                    std::cout << h.memory[h.ptr + j];
            std::cout << std::endl;
            */
            bool mem_p_arr[mem_p_size];
            for(int j=0;j<mem_p_size;j++)
                mem_p_arr[j]=h.memory[j+190];
            bool p_same=true;
            for(int j=0;j<mem_p_size;j++)
                if(mem_p_arr[j]!=mem_old[j]){
                    p_same=false;
                    break;
                }
            if(p_same){
                cout<<".";
                loop_num++;
            }else{
                cout<<endl;
                for(int j=0;j<mem_p_size;j++){
                    cout<<mem_p_arr[j];
                    mem_old[j]=mem_p_arr[j];
                }
            }
        }
        //h.print_ptr();
        
        i += 2;
    }
}


int main() {
    srand(time(0));
    int order = 4, level = 1;
    std::vector<Problem> problems;
    
    /*
    for (int i = 0; i < 5; ++i) {
        //cout<<"i= "<<i<<endl;
        Problem p = generateOneProblem(order, level);
        problems.push_back(p);

        //std::cout << "可讀題目：" << p.readable << std::endl;
       // std::cout << "題目螺旋碼：" << std::endl;
       // for (auto& token : p.question) token.print();
        //std::cout << "答案螺旋碼：" << std::endl;
       // p.answer.print();
        //cout << "-----------------------------\n";
    }
     std::vector<std::string> spiral_program = {
        "00100", "00110",  // write_1, 3 bits
        "00010", "11100",  // move_ptr -2
        "01000", "00110",  // read 3 bits
        "00010", "01000",  // move_ptr +4
        "01010", "00110",  // xor 3 bits
        "00010", "01000",  // move_ptr +4
        "10010", "00110",  // write_val 3 bits
        "11110"            // out_area
    };
    */
    //simulate_spiral_program(spiral_program);
    
    HamsterParams base_param;
    std::vector<Hamster> good_hamsters;
    int index=0;
    
    
    for (int out_round = 1; out_round <= ROUND_outside; out_round++) {
        std::cout << "--- Out_Round " << out_round << " ---" << std::endl;
        
        std::vector<Hamster> hamsters;
        int hamu_num_rand;
        if(good_hamsters.size()==0){
            hamu_num_rand=Hamu_num;
        }else{
            hamu_num_rand=Hamu_num/(2+(out_round/ROUND_outside)*10);
        }
            
        for (int i = 0; i < hamu_num_rand; ++i) {
        hamsters.emplace_back(index++, base_param);
        hamsters[i].set_mem_rand();
        }
        for(int i= hamu_num_rand ;i < Hamu_num && good_hamsters.size()>0; i++){
            int good_id = rand()%good_hamsters.size();
            good_id += (good_hamsters.size() - good_id)*((rand()%10)/10);
            if(good_id > good_hamsters.size()) cout<<"Out bound good_id!!"<<endl;
            hamsters.emplace_back(index++, base_param);
            hamsters[i].copy_hamu(good_hamsters[good_id]);
            hamsters[i].change_hamu(Change_rate);
        
        
        }
        
        
        for (auto& h : hamsters) {
            
            for(int round = 1; round <= ROUND; ++round){
                if (!h.is_alive()){
                    break;
                }
                Problem p = generateOneProblem(order, level);
                h.write_prob(p);
                bool count_cont=true;
                
                int loop_num=0;
                while(h.stop == false){
                    if(loop_num>deth_loop_num)break;
                    //h.status_ref();
                    //cout<<"simu ";
                    simulate_spiral_program(h);
                    h.use_hp();
                    h.ptr=0;
                    //count_cont=h.memory[h.params.layout.program_start];
                    if(h.hp<0)break;
                    loop_num += 3;
                }
                h.status_ref();
                bool correct = Check_ans(h,p);
                if(correct)h.add_hp(p);
            
                h.record_result(correct, p);
                if(h.hp > h.max_hp_his && h.hp > (5 + h.params.initial_hp) && h.age>20
                && float(h.correct_count_counting/2+h.correct_count_counting)/float(h.age)>0.1){
                    h.new_his();
                }
                h.age++;
                h.stop=false;
                //h.print_summary();
            }
            if(h.id%100==0)cout<<h.id<<" age="<<h.age<<" hp="<<int(h.hp)<<endl;
            
            
        }
        
        float avg_age=0;
        float avg_hp=0;
        float avg_rate1=0;
        float avg_rate2=0;
        
        for(auto& h : hamsters){
            avg_age += h.age;
            avg_hp += h.hp;
            avg_rate1 += h.correct_count_counting;
            avg_rate2 += h.correct_count_arith;
            
            if(h.creat_his){
                cout<<h.id<<" age="<<h.max_hp_age_his<<
                " maxhp="<<int(h.max_hp_his)<<endl;
                h.print_summary();
                good_hamsters.emplace_back(index ++, base_param);
                good_hamsters[good_hamsters.size()-1].copy_hamu(h);
                //good_hamsters[good_hamsters.size()-1].change_hamu(Change_rate);
        
            }
        }
        avg_age /= Hamu_num;
        avg_hp /= Hamu_num;
        avg_rate1 /= Hamu_num;
        avg_rate2 /= Hamu_num;
        
        if(out_round%5==1){
            cout<<"avg_age= "<<avg_age<<" ,avg_hp= "<<avg_hp<<
            " ,avg_count= "<<avg_rate1<<" avg_arth= "<<avg_rate2<<endl;
        }
        
    }
    return 0;
}
