#include <vector>
#include <iostream>
#include <stdexcept>
#include <cstdlib>
#include <ctime>
#include <unordered_map>
#include <string>
#include <bitset>
#include <iomanip>
#include <fstream>
#include <map>
#include <random>

using namespace std;

const int ROUND_outside = 1000;
const int ROUND = 500;
const int Grow_up = 50;
const int Hamu_num = 100;


const int deth_loop_num = 5;
const int Change_rate = 50;
const int Op_cost = 200;
const float basic_use = 1.5;
const int Add_hp_ratio = 3;

const int Print_per = 20;
int Good_age = 15;
const int Good_ratio = 10;
const int Adition_hp = 0;
float Correct_rate = 0.45;
float Mem_inc_rate = 0;
const int Mem_size = 150;
const int Reg_size = 5;
const int Pro_start = 80;

const bool only_count = true;

string File_name = "output.txt";
string File_name2 = "output2.txt";
bool print_hamu_control = 0;
const bool op_print = 0;
const bool mem_print = 0;
const int mem_p_size = Mem_size;
const bool Simu_dbug = 0;

bool Tese_other = 0;

struct SpiralToken {
    int value;
    int order;
    int level;
    std::vector<bool> bits;
    // 預先分配空間更穩定
    SpiralToken() : value(0), order(1), level(1) {
        bits.push_back(0); // 1-bit order
        bits.push_back(0); // 1-bit level
    }
    SpiralToken(int val, int ord, int lvl) {
        if (val >= (1 << ord)) {
            throw std::invalid_argument("Value exceeds maximum for given order.");
        }
        value = val;
        order = ord;
        level = lvl;

        bits.reserve(ord + lvl);

        if (ord > 0) {
            for (int i = ord - 1; i >= 0; --i)
                bits.push_back((val >> i) & 1);
        }
        for (int i = 0; i < lvl; ++i)
            bits.push_back(0);
    }
    /*
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
    */
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
const std::vector<int> OpCodes = { 11, 12, 13, 14 }; // - + → ←
const int END_CODE = 15;

enum class ProblemType {
    COUNTING,
    ARITHMETIC,
    EAZY
};




struct Problem {
    ProblemType type;
    std::vector<SpiralToken> question;
    SpiralToken answer;
    std::string readable;
    void print_Problem() {
        for (int i = 0; i < question.size(); i++) {
            cout << question[i].value << " ";
        }
        cout << endl;
    }
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
            if (only_count) continue;
            if (a + b > 10) continue;
            result = a + b;
            opStr = "+";
        }
        else if (op == 11) { // -
            if (only_count) continue;
            if (a - b < 0) continue;
            result = a - b;
            opStr = "-";
        }
        else if (op == 13) { // →
            if (a + 1 > 10) continue;
            result = a + 1;
            opStr = "→";
        }
        else if (op == 14) { // ←
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
        ProblemType P_Type = ProblemType::COUNTING;
        if (op == 12 || op == 11)P_Type = ProblemType::ARITHMETIC;
        return Problem{ P_Type, q, R, readable };
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


// generate simple problem
enum class OpType { COPY, AND, OR, XOR };

std::map<OpType, int> op_to_code = {
    {OpType::COPY, 0},
    {OpType::AND, 1},
    {OpType::OR, 2},
    {OpType::XOR, 3}
};

std::map<int, OpType> code_to_op = {
    {0, OpType::COPY},
    {1, OpType::AND},
    {2, OpType::OR},
    {3, OpType::XOR}
};

std::string op_to_string(OpType op) {
    switch (op) {
    case OpType::COPY: return "COPY";
    case OpType::AND:  return "AND";
    case OpType::OR:   return "OR";
    case OpType::XOR:  return "XOR";
    default: return "UNKNOWN";
    }
}

// 生成一個隨機 n 階 (n+1 bit) 題目（2階共 4 bits）
Problem generate_simple_problem(int order = 2, int level = 1) {
    static std::mt19937 rng(std::random_device{}());
    std::uniform_int_distribution<int> val_dist(0, (1 << order) - 1);
    std::uniform_int_distribution<int> op_dist(0, 3);  // 四種運算

    int a = val_dist(rng);
    int b = val_dist(rng);
    OpType op = static_cast<OpType>(op_dist(rng));

    int result = 0;
    switch (op) {
    case OpType::COPY: result = a; break;
    case OpType::AND:  result = a & b; break;
    case OpType::OR:   result = a | b; break;
    case OpType::XOR:  result = a ^ b; break;
    }

    Problem p;
    p.type = ProblemType::EAZY;
    p.question.push_back(SpiralToken(op_to_code[op], order, level));
    p.question.push_back(SpiralToken(a, order, level));
    if(op != OpType::COPY) 
        p.question.push_back(SpiralToken(b, order, level));
    p.answer = SpiralToken(result, order, level);

    p.readable = op_to_string(op) + " " + std::to_string(a) + " " + std::to_string(b) +
        " = " + std::to_string(result);

    return p;
}

// 判斷倉鼠回答是否正確
bool check_answer(const std::vector<SpiralToken>& hamster_output, const SpiralToken& correct) {
    if (hamster_output.empty()) return false;
    return hamster_output[0].value == correct.value;
}

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
    
    if (token.bits.empty()) {
        std::cerr << "[decode_op] token.bits is empty!\n";
    }
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
    int unit_cost_per = Op_cost;
    int add_hp_ratio = Add_hp_ratio;
    int op_order = 4;
    int op_lvl = 1;

    struct {
        int input_start = 0;
        int status_start = 20;
        int output_start = 30;
        int work_start = 60;
        int program_start = Pro_start;
        int total_size = Mem_size;
        int val_reg_size = Reg_size;
    } layout;

    struct {
        //int pro_1 = 181;
        //int pro_2 = 255;
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
    int correct_EAZY = 0;
    int incorrect_count = 0;

    Hamster(int _id, const HamsterParams& p) : id(_id), params(p), hp(p.initial_hp), age(0) {
        params.layout.total_size += int(Mem_inc_rate * ROUND_outside);
        memory = std::vector<bool>(params.layout.total_size, 0);
        val_reg = std::vector<bool>(params.layout.val_reg_size, 0);

        memory_his = std::vector<bool>(params.layout.total_size, 0);
        val_reg_his = std::vector<bool>(params.layout.val_reg_size, 0);


        pro_1 = params.layout.program_start + 1 - 50;
        pro_2 = params.layout.total_size - 1;
        hp = params.initial_hp;
        max_hp_his = hp + Adition_hp;
        max_hp_age_his = 1;
        creat_his = false;
        ptr = 0;
        val_ptr = 0;
        stop = false;
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
                memory[1 + idx++] = bit;
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

        ptr = 0;
        val_ptr = 0;

        pro_2 = params.layout.total_size - 1;
        pro_1 = params.layout.program_start + 1;
        stop = false;

    }

    void new_his() {
        creat_his = true;
        memory_his = memory;
        val_reg_his = val_reg;
        max_hp_his = hp;
        max_hp_age_his = age;
    }

    void copy_hamu(Hamster& h2) {
        for(int i= params.layout.work_start;i<h2.params.layout.total_size;i++){
            memory[i] = h2.memory_his[i];
		}
        //memory = h2.memory_his;
        for (int i = 0; i < h2.val_reg_his.size(); i++) {
            val_reg[i] = h2.val_reg_his[i];
            //val_reg = h2.val_reg_his;
        }
    }

    void change_hamu(int r) {

        for (int i = params.layout.work_start; i < memory.size(); i++) {
            if (rand() % r == 1) {
                memory[i] = !memory[i];
            }
        }

    }

    void use_hp() {
        float cost = float(pro_2 - pro_1) / float(params.unit_cost_per);
        hp -= cost;
    }

    void add_hp(Problem& p) {

        if (p.type == ProblemType::EAZY) {
            //cout << "*";
            hp += params.add_hp_ratio;
        }
        else hp += params.add_hp_ratio * 2;
        if (hp > params.max_hp) hp = params.max_hp;
    }

    bool Chk_vag() {
        for (int i = 0; i < val_reg.size(); i++) {
            if (val_reg[i] == 1)return true;
        }
        return false;
    }

    void record_result(bool correct, const Problem& prob) {
        std::string entry = (correct ? "[O] " : "[X] ") + prob.readable;
        result_log.push_back(entry);
        if (correct) {
            if (prob.type == ProblemType::EAZY) ++correct_EAZY;
            else if (prob.type == ProblemType::COUNTING) ++correct_count_counting;
            else if (prob.type == ProblemType::ARITHMETIC)++correct_count_arith;
            //hp += params.reward_correct;
        }
        else {
            ++incorrect_count;
            //hp -= params.penalty_wrong;
        }
        //if (hp > 100) hp = 100;
    }

    void print_summary() const {
        std::cout << "Hamster#" << id << std::setw(6)
            << " | HP: " << std::setw(3) << int(hp)
            << " | Age: " << std::setw(2) << age
            << " Rate = " << correct_EAZY * 100 / age
            << " EAZY: "  << correct_EAZY
            //<< "% | COUNTING: " << correct_count_counting
            //<< " | ARITH: " << correct_count_arith
            << " | WRONG: " << incorrect_count << std::endl;
    }
    void print_ptr() {
        cout << "ptr= " << ptr << " val_ptr= " << val_ptr <<
            " pro1= " << pro_1 << " pro2= " << pro_2 << endl;
    }

    void print_Hamu() {
        cout << "Hamster#" << id << " HP: " << hp << " Age: " << age << endl;
        cout << "Max HP: " << max_hp_his << " Age: " << max_hp_age_his << endl;
        cout << "Memory: "<<endl;
        for (int i = 0; i < memory.size(); i++) {
            cout << memory[i];
            if (i % 64 == 63)cout << endl;
        }
        cout << endl<<"Memory_his: "<<endl;
        for (int i = 0; i < memory_his.size(); i++) {
            
            cout << memory_his[i];
            if (i % 64 == 63)cout << endl;
        }
        cout << endl;
        cout << "Val_reg: ";
        for (int i = 0; i < val_reg.size(); i++) {
            cout << val_reg[i];
        }
        cout << endl;
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
        if (p.answer.bits[i] != h.memory[out_data_start + i + 1]) {
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
    //if (print_hamu_control)h.print_Hamu();
    int loop_num = 0;
    int lvl = h.params.op_lvl;
    int op_order = h.params.op_order;
    int move_width = op_order + lvl;
    static bool mem_old[mem_p_size];

    int token_bits_total = (h.pro_2 - h.pro_1 + 1);
    if (token_bits_total < move_width) return; // 不夠一個 token，跳出

    int tokens_size = token_bits_total / move_width;
    std::vector<SpiralToken> tokens;

    // Token解析
    if(Simu_dbug) cout << "A" << flush;
    for (int i = 0; i < tokens_size; i++) {
        int start_idx = h.pro_1 + i * move_width;
        if (start_idx < 0 || start_idx + move_width >(int)h.memory.size()) {
            std::cerr << "[Hamster#" << h.id << "] Token[" << i << "] memory out of bounds.\n";
            return;
        }

        int val = 0;
        for (int j = 0; j < op_order; ++j) {
            val = (val << 1) | h.memory[start_idx + j];
        }

        SpiralToken tok;
        try {
            tok = SpiralToken(val, op_order, lvl);
        }
        catch (const std::exception& e) {
            std::cerr << "[Hamster#" << h.id << "] Invalid SpiralToken: " << e.what() << "\n";
            return;
        }

        if (tok.bits.empty() || (int)tok.bits.size() != move_width) {
            std::cerr << "[Hamster#" << h.id << "] Token[" << i << "] bits size mismatch.\n";
            return;
        }

        tokens.push_back(tok);
    }

    if(tokens_size != tokens.size()){
        cout << "!!!!!" << endl << flush;
    }
    
    if (tokens.empty()) return;
    if (Simu_dbug)cout << "Q"<<flush;
    // Token執行
   
    //cout << "---";
    for (size_t i = 0; i < tokens_size;) {
        if (Simu_dbug)cout << "D" << flush;
        if (op_print) {
            cout << tokens[i].value << " ~ "<<flush;
            if(i+1 < tokens_size) cout << tokens[i+1].value << " . " << flush;
        }

        if (++loop_num > deth_loop_num) {
            //std::cerr << "[Hamster#" << h.id << "] Loop exceeded " << deth_loop_num << " steps.\n";
            return;
        }

        if (i >= tokens.size()) {
            std::cerr << "[Hamster#" << h.id << "] Execution index out of bounds.\n";
            return;
        }

        const SpiralToken& tok = tokens[i];
        if (tok.bits.empty()) {
            std::cerr << "[Hamster#" << h.id << "] Token[" << i << "] has empty bits.\n";
            ++i;
            continue;
        }

        SpiralOp op = decode_op(tok);

        if (op == SpiralOp::INVALID) {
            if (op_print)
                std::cout << "[Hamster#" << h.id << "] Invalid op: Token[" << i << "]\n";
            ++i;
            continue;
        }

        // 非合法 spiral 結尾 (一般判定為資料區而非指令)
        if ((int)tok.bits.size() < move_width || tok.bits[move_width - 1] == 1) {
            ++i;
            continue;
        }

        int op_len = 2;


        if (op == SpiralOp::INVALID) {
            if (op_print)std::cout << "[Hamster#" << h.id << "] Invalid op token: " << tokens[i] << "\n";
            ++i;
            continue;
        }

        // not SpiralToken
        if (tokens[i].bits[move_width - 1] == 1) {
            i += 1;
            continue;
        }
        // no param exit

        if (op == SpiralOp::OUT_AREA) {
            if (op_print)std::cout << "[Hamster#" << h.id << "] Op: out_area\n";
            op_len = 1;
            // OUT_AREA will break 
            /*
            h.stop=true;
            return;
            */
            break;
        }

        if (i == tokens_size - 1) {
            i++;
            return;

        }


        if (i + 1 >= tokens_size) {
            if (op_print)std::cout << "[Hamster#" << h.id << "] Missing parameter for: " << tokens[i] << "\n";
            return;
        }

        int param = tokens[i + 1].value;

        if(Simu_dbug)cout << "Y" << flush;

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

            for (int j = 0; j < param && (h.ptr + j) < h.memory.size(); ++j) {
                if (j + h.val_ptr > h.params.layout.val_reg_size - 1)break;
                h.val_reg[j + h.val_ptr] = h.memory[h.ptr + j];
            }
        case SpiralOp::XOR:
            for (int j = 0; j < param && (h.ptr + j) < h.memory.size() && j + h.val_ptr < h.val_reg.size(); ++j)
                h.memory[h.ptr + j] = h.memory[h.ptr + j] ^ h.val_reg[h.val_ptr + j];
            break;
        case SpiralOp::AND:
            for (int j = 0; j < param && (h.ptr + j) < h.memory.size() && j + h.val_ptr <  h.val_reg.size(); ++j)
                h.memory[h.ptr + j] = h.memory[h.ptr + j] & h.val_reg[h.val_ptr + j];
            break;
        case SpiralOp::OR:
            for (int j = 0; j < param && (h.ptr + j) < h.memory.size() && j+ h.val_ptr <h.val_reg.size(); ++j)
                h.memory[h.ptr + j] = h.memory[h.ptr + j] | h.val_reg[h.val_ptr + j];
            break;
        case SpiralOp::MOVE_PTR: {
            
            int total_bits = tokens[i + 1].order;
            if (total_bits < 1) break;

            int raw_val = tokens[i + 1].value;
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
            int dir_bit = tokens[i + 1].bits[0];
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
            int dir_bit = tokens[i + 1].bits[0];
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
            int dir_bit = tokens[i + 1].bits[0];
            int direction = dir_bit ? +1 : -1;
            int bias = dir_bit << (op_order - 1);
            int move_amount = direction * (param - bias);

            h.pro_1 += move_amount * move_width;
            if (h.pro_1 < 0) h.pro_1 = 0;
            if (h.pro_1 > h.params.layout.total_size) h.pro_1 = h.params.layout.total_size - 1;
            break;
        }
        case SpiralOp::SET_PTR2: {
            int dir_bit = tokens[i + 1].bits[0];
            int direction = dir_bit ? +1 : -1;
            int bias = dir_bit << (op_order - 1);
            int move_amount = direction * (param - bias);

            h.pro_2 += move_amount * move_width;
            if (h.pro_2 < 0) h.pro_2 = 0;
            if (h.pro_2 > h.params.layout.total_size) h.pro_2 = h.params.layout.total_size - 1;
            break;
        }


        case SpiralOp::SET_AREA:
            if (param % 8 == 0);//h.ptr=0;
            else if (param % 8 == 1) h.ptr = h.params.layout.status_start;
            else if (param % 8 == 2) h.ptr = h.params.layout.output_start;
            else if (param % 8 == 3) h.ptr = h.params.layout.work_start;
            else if (param % 8 == 4) h.ptr = h.params.layout.work_start + 10 * (op_order + lvl);
            else if (param % 8 == 5) h.ptr = h.pro_1;
            else if (param % 8 == 6) h.ptr = h.pro_2;
            //else if(param%8==7) h.ptr=h.params.layout.total_size;
            else if (param % 8 == 7) h.stop = true;

            break;

        case SpiralOp::WRITE_VAL:
            for (int j = 0; j < param && (h.ptr + j) < h.memory.size() && j+ h.val_ptr < h.val_reg.size(); ++j) {
                int addr = h.ptr + j;
                if (addr >= h.params.layout.output_start) {
                    h.memory[addr] = h.val_reg[h.val_ptr + j];
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
                h.memory[j] = rand() % 2;
            }
            break;



        default:
            break;
        }
        if (Simu_dbug)cout << "W" << flush;
        // Optional: debug memory snapshot
		
        if (op_print) {
            cout << tokens[i].value << " " << tokens[i + 1].value << " " << param << endl;
            cout << "Op=" << op_to_string(op) << " i=" << i << " " << tokens[i] << " " << param << " ";
            if (i + 1 < tokens_size)cout << tokens[i + 1] << " ";
            std::cout << "[Hamster#" << h.id << "] Mem[ptr=" << h.ptr << "] "<<endl;
        }
        if (mem_print) {
            /*
            for (int j = -8; j < 16; ++j)
                if(h.ptr + j>=0 && h.ptr + j<h.params.layout.total_size)
                    std::cout << h.memory[h.ptr + j];
            std::cout << std::endl;
            */
            bool mem_p_arr[mem_p_size];
            for (int j = 0; j < mem_p_size; j++)
                mem_p_arr[j] = h.memory[j + 0];
            bool p_same = true;
            for (int j = 0; j < mem_p_size; j++)
                if (mem_p_arr[j] != mem_old[j]) {
                    p_same = false;
                    break;
                }
            if (p_same) {
                cout << ".";
                loop_num++;
            }
            else {
                cout << endl;
                for (int j = 0; j < mem_p_size; j++) {
                    cout << mem_p_arr[j];
                    mem_old[j] = mem_p_arr[j];
                }
            }
        }
        //h.print_ptr();
        if (print_hamu_control)h.print_Hamu();
        i += 2;
    }

}

void Renew_good_hamu(std::vector<Hamster>& good_hamsters) {
	if (good_hamsters.size() == 0)return;
    int a = 0;
    for (int i = 0; i < good_hamsters.size(); ++i) {
        a += good_hamsters[i].age;
    }
    Good_age = a / good_hamsters.size();
}

void export_hamster_state(const Hamster& h, std::string filename) {
    std::ofstream outfile(filename, std::ios::app);  // 開啟輸出檔案
    
    if (!outfile.is_open()) {
        std::cerr << "Failed to open file: " << filename << "\n";
        return;
    }
    
    outfile << "Hamster ID: " << h.id << "\n";
    outfile << "Age: " << h.age << " HP: " << h.hp << "\n";
    outfile << "Pointer: " << h.ptr << "  ValPtr: " << h.val_ptr << "\n";
    outfile << "Pro1: " << h.pro_1 << "  Pro2: " << h.pro_2 << "\n";
    outfile << "Creat_his: = " << h.creat_his << endl;
    outfile << "\nMemory:\n";
    for (int i = 0; i < h.memory.size(); ++i) {
        outfile << h.memory[i];
        if ((i + 1) % 64 == 0) outfile << "\n";  // 每 64 位元換行
    }
    /*
    outfile << "\nAge:_his " << h.max_hp_age_his << " HP_his: " << h.max_hp_his << "\n";
    outfile << "\nMemory_his:\n";
    for (int i = 0; i < h.memory_his.size(); ++i) {
        outfile << h.memory_his[i];
        if ((i + 1) % 64 == 0) outfile << "\n";  // 每 64 位元換行
    }
    */
    outfile << endl<< "Val_Reg: ";
    for (auto v : h.val_reg) outfile << v;
    outfile << "\n";
    outfile.close();
    //std::cout << "Hamster state exported to: " << filename << "\n";
}


int main() {
    srand(time(0));
    int order = 4, level = 1;
    std::vector<Problem> problems;
    std::ofstream outfile2(File_name2);  // 開啟輸出檔案

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
    /*
    for (int i = 0; i < 20; i++) {
        auto p1 = generate_simple_problem();
        while (1) {
            p1 = generate_simple_problem();
            if (p1.question[0].value == 0)break;
        }
        p1.print_Problem();
        cout<<p1.answer<<endl;
    }
    */

    if (Tese_other == true) return 0;

    std::ofstream outfile(File_name2);  // 開啟輸出檔案

    if (!outfile.is_open()) {
        std::cerr << "Failed to open file: " << File_name2 << "\n";

    }


    HamsterParams base_param;
    std::vector<Hamster> good_hamsters;
    int index = 0;
    std::vector<Hamster> hamsters;

    for (int out_round = 1; out_round <= ROUND_outside; out_round++) {
        if (out_round % Print_per == 0) {
            std::cout << "--- Out_Round " << out_round << " --- ";
			outfile << "--- Out_Round " << out_round << " --- " << std::endl;
        }
        hamsters.clear();
        //std::vector<Hamster> hamsters;
        int hamu_num_rand = 0;
        //cout<<"+";
        Renew_good_hamu(good_hamsters);
        if (good_hamsters.size() == 0) {
            hamu_num_rand = Hamu_num;
        }
        else {

            hamu_num_rand = Hamu_num / 5 + Hamu_num / (2 + good_hamsters.size() / Good_ratio);
        }
        //cout<<"*";    
        for (int i = 0; i < hamu_num_rand; ++i) {
            hamsters.emplace_back(index++, base_param);
            if (i < hamsters.size())hamsters[i].set_mem_rand();
            else cout << "!!!!!";
        }
        for (int i = hamu_num_rand; i < Hamu_num && good_hamsters.size()>0; i++) {
            int good_id = rand() % good_hamsters.size();
            good_id += (((good_hamsters.size() - good_id) * (rand() % 3)) / 3);
            if (good_id >= good_hamsters.size()) {
                cout << "Out bound good_id!!" << endl;
                good_id -= 1;
            }
            hamsters.emplace_back(index++, base_param);
            hamsters[i].copy_hamu(good_hamsters[good_id]);
            hamsters[i].change_hamu(Change_rate);


        }
        if (out_round % Print_per == 0) {
            cout << hamu_num_rand << " " << good_hamsters.size() << endl;
			outfile << hamu_num_rand << " " << good_hamsters.size() << endl;
        }

        for (auto& h : hamsters) {
            //cout<<".";
            for (int round = 1; round <= ROUND; ++round) {
                if (!h.is_alive()) {
                    break;
                }
                //Problem p = generateOneProblem(order, level);
                auto p = generate_simple_problem();
                while (1) {
                    p = generate_simple_problem();
                    if (p.question[0].value == 0)break;
                }
                h.write_prob(p);
                //bool count_cont = true;

                int loop_num = 0;
                while (h.stop == false) {
                    if (loop_num > deth_loop_num)break;
                    //h.status_ref();
                    //cout<<"simu ";
                    simulate_spiral_program(h);
                    h.use_hp();
                    h.ptr = 0;
                    //count_cont=h.memory[h.params.layout.program_start];
                    if (h.hp < 0)break;
                    loop_num += deth_loop_num;
                }
                h.status_ref();
                bool correct = Check_ans(h, p);
                if (correct) {
                    //cout << "+";
                    h.add_hp(p);
                }

                //hamu creat history 
                h.record_result(correct, p);

                if (h.hp > h.max_hp_his && h.hp > (Adition_hp + h.params.initial_hp) && h.age > (ROUND / Grow_up)
                    && float(h.correct_EAZY) / float(h.age) > Correct_rate) {
                    h.new_his();
                    //cout << "creat";
                }
                h.age++;
                h.stop = false;
                //h.print_summary();
            }
            // if(h.id%100==0)cout<<h.id<<" age="<<h.age<<" hp="<<int(h.hp)<<endl;


        }

        float avg_age = 0;
        float avg_hp = 0;
        float avg_rate1 = 0;
        float avg_rate2 = 0;
        float avg_rate3 = 0;

        for (auto& h : hamsters) {
            avg_age += h.age;
            avg_hp += h.hp;
            avg_rate1 += h.correct_count_counting;
            avg_rate2 += h.correct_count_arith;
            avg_rate3 += h.correct_EAZY;

            if (h.creat_his && (h.age > Good_age)) {
                if ((h.correct_EAZY * 100) / h.age > Correct_rate * 100) {
                    cout << " Age=" << h.max_hp_age_his <<
                        " maxhp=" << int(h.max_hp_his) << " ";
                    h.print_summary();
                    h.print_Hamu();


                }
                //h.print_summary();
                //h.print_Hamu();
                good_hamsters.emplace_back(index++, base_param);
                good_hamsters[good_hamsters.size() - 1].copy_hamu(h);
                //output file
                export_hamster_state(good_hamsters[good_hamsters.size() - 1], File_name);
                //good_hamsters[good_hamsters.size()-1].change_hamu(Change_rate);

            }
        }
        avg_age /= Hamu_num;
        avg_hp /= Hamu_num;
        avg_rate1 /= Hamu_num;
        avg_rate2 /= Hamu_num;
        avg_rate3 /= Hamu_num;

        if (out_round % Print_per == 0) {

            cout << "avg_age= " << avg_age << " ,avg_hp= " << avg_hp <<
                " ,avg_EAZY= " << avg_rate3
                //" ,avg_count= " << avg_rate1 << " avg_arth= " << avg_rate2 
                << endl;

            
            outfile2 << "avg_age= " << avg_age << " ,avg_hp= " << avg_hp <<
                " ,avg_EAZY= " << avg_rate3
                //" ,avg_count= " << avg_rate1 << " avg_arth= " << avg_rate2 
                << endl;
            
        }

        
    }


    for (int i = 0; i < good_hamsters.size(); i++) {

        //export_hamster_state(good_hamsters[i], File_name);
    }
    //outfile2.close();
    return 0;
}
