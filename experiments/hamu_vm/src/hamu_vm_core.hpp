#pragma once
#include <algorithm>
#include <cmath>
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
#include <climits>
#include <array>
#include <deque>
#include <cstdint>

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
        if (ord < 1 || ord > 24 || lvl < 1 || lvl > 16 || val < 0 || val >= (1 << ord)) {
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
SpiralToken decodeSpiral(const std::vector<bool>& code, int order, int level) {
    if (order < 1 || order > 24 || level < 1 || level > 16 ||
        code.size() != static_cast<size_t>(order + level))
        throw std::invalid_argument("Token needs explicit order, level and exact length");
    for (int i = order; i < order + level; ++i)
        if (code[i]) throw std::invalid_argument("Unexpected token suffix");
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
    SMOVE_PTR, OUT_AREA, JUMP_MODE, JUMP_IF_1, JUMP_IF_LOCAL, SWAP_PTR, JUMP_LOCAL,
    SWAP_OUTPUT_PTR, JUMP_BACK, JUMP_BACK_WIDE, JUMP_IF_FORWARD_WIDE, XOR_REG,
    JUMP_FORWARD_WIDE, TREE_FIND, TREE_ADD, TREE_FIND_REG, TREE_ACTION,
    TREE_ADD_REG,
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
    // Numeric opcode identity survives left-padding; no five-bit prefix match.
    if (token.order >= 4 && token.value >= 0 &&
        (token.value < 16 || (token.order >= 5 && token.value <= 18)) &&
        token.bits.size() == static_cast<size_t>(token.order + token.level)) {
        for (int i = token.order; i < token.order + token.level; ++i)
            if (token.bits[i]) return SpiralOp::INVALID;
        return static_cast<SpiralOp>(token.value);
    }
    return SpiralOp::INVALID;
#if 0
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
#endif
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
    case SpiralOp::JUMP_MODE: return "16 jump_mode";
    case SpiralOp::JUMP_IF_1: return "17 jump_if_1";
    case SpiralOp::JUMP_IF_LOCAL: return "18 jump_if_local";
    case SpiralOp::SWAP_PTR: return "19 swap_ptr";
    case SpiralOp::JUMP_LOCAL: return "20 jump_local";
    case SpiralOp::SWAP_OUTPUT_PTR: return "21 swap_output_ptr";
    case SpiralOp::JUMP_BACK: return "22 jump_back";
    case SpiralOp::JUMP_BACK_WIDE: return "23 jump_back_wide";
    case SpiralOp::JUMP_IF_FORWARD_WIDE: return "24 jump_if_forward_wide";
    case SpiralOp::XOR_REG: return "25 xor_reg";
    case SpiralOp::JUMP_FORWARD_WIDE: return "26 jump_forward_wide";
    case SpiralOp::TREE_FIND: return "27 tree_find";
    case SpiralOp::TREE_ADD: return "28 tree_add";
    case SpiralOp::TREE_FIND_REG: return "29 tree_find_reg";
    case SpiralOp::TREE_ADD_REG: return "31 tree_add_reg";
    case SpiralOp::TREE_ACTION: return "30 tree_action";
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
    int op_order = 5;
    int op_lvl = 1;
    bool strict_work_insert = true; // false enables the historical VAG spill mode
    int stable_work_bits = 0; // writable persistent tail, excluded from INSERT/DELETE
    int tree_start = -1; // optional 9-bit nodes in stable work; root ID is 0
    int tree_capacity = 0; // IDs 1..capacity; default five-bit legacy mode
    int tree_id_bits = 5; // opt-in wider tree handles, 5..12 (not segmented allocation)
    bool tree_index_enabled = true; // wide-mode VM-native derived index, not inherited memory
    bool tree_segmented_enabled = false; // EXPERIMENTAL opt-in, canonical tree in 31-row pages
    bool tree_reject_mask_enabled = false; // opt-in 8-candidate rejected-answer bits, segmented only
    bool tree_confirm_three_bits_enabled = false; // opt-in 3-bit answer; high bit stored at row bit31

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
    int secondary_ptr = 0;
    int output_ptr = 0;
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
    int executed_steps = 0;
    // Diagnostics only: native rows inspected by TREE_FIND/TREE_ADD.
    // Not charged to the guest executed_steps or HP budget.
    unsigned long long tree_lookup_rows_examined = 0;
    // Wide-tree derived lookup cache. The guest's tree rows remain canonical.
    // Lazy rebuild is charged in row-inspection metrics but not guest steps.
    // Experimental page ABI: each canonical row is one packed 32-bit value.
    // [parent <=16 bits][3-bit key][3-bit action state][live]. A 31-row
    // deque page has stable addresses when pages are appended. This ABI is
    // NOT interchangeable with the legacy guest-addressable bit rows.
    static constexpr int SEGMENT_PAGE_ROWS=31;
    using SegmentPage=std::array<uint32_t,SEGMENT_PAGE_ROWS>;
    std::deque<SegmentPage> segment_pages;
    std::deque<SegmentPage> segment_pages_his;
    int segment_used=0; // high-watermark, not necessarily live count
    int segment_used_his=0;
    int segment_first_free_id=1; // derived: lowest dead ID or high-watermark+1
    std::unordered_map<uint64_t,int> segment_edge_index; // derived, never inherited
    bool segment_edge_index_valid=false;
    unsigned long long segment_edge_rebuild_rows=0,segment_edge_lookups=0;
    unsigned long long segment_edge_linear_rows=0,segment_growth_pages=0;

    uint32_t segment_row(int id) const {
        if(id<=0||id>segment_used) return 0;
        return segment_pages.at((id-1)/SEGMENT_PAGE_ROWS).at((id-1)%SEGMENT_PAGE_ROWS);
    }
    uint32_t &segment_row_ref(int id) {
        if(id<=0||id>params.tree_capacity) throw std::out_of_range("segment row ID out of capacity");
        return segment_pages.at((id-1)/SEGMENT_PAGE_ROWS).at((id-1)%SEGMENT_PAGE_ROWS);
    }
    void rebuild_segment_first_free_id(){
        segment_first_free_id=1;
        while(segment_first_free_id<=segment_used &&
              (segment_row(segment_first_free_id)&1u))
            ++segment_first_free_id;
    }
    static uint64_t segment_edge(int parent,int key) {
        return (uint64_t(parent)<<3)|uint64_t(key);
    }
    void invalidate_segment_index(){segment_edge_index.clear();segment_edge_index_valid=false;}
    void ensure_segment_index() {
        if(segment_edge_index_valid) return;
        segment_edge_index.clear();
        for(int id=1;id<=segment_used;++id){
            ++segment_edge_rebuild_rows;
            const uint32_t row=segment_row(id);
            if(row&1u) segment_edge_index.emplace(segment_edge(int(row>>7),int((row>>4)&7)),id);
        }
        segment_edge_index_valid=true;
    }
    int segment_find(int parent,int key) {
        ++segment_edge_lookups;
        if(params.tree_index_enabled){
            ensure_segment_index();
            const auto it=segment_edge_index.find(segment_edge(parent,key));
            return it==segment_edge_index.end()?0:it->second;
        }
        for(int id=1;id<=segment_used;++id){
            ++segment_edge_linear_rows;
            const uint32_t row=segment_row(id);
            if((row&1u) && int(row>>7)==parent && int((row>>4)&7)==key)return id;
        }
        return 0;
    }
    void grow_segmented_tree_capacity(int capacity){
        if(!params.tree_segmented_enabled || capacity<=params.tree_capacity ||
           capacity>(1<<params.tree_id_bits)-1 || capacity<1)
            throw std::invalid_argument("Invalid segmented tree capacity growth");
        const std::size_t pages_needed=(std::size_t(capacity)+SEGMENT_PAGE_ROWS-1)/SEGMENT_PAGE_ROWS;
        if(pages_needed>65536)throw std::invalid_argument("Segmented tree page limit");
        // Deque appends preserve existing row addresses. If allocation throws,
        // discard only the newly appended empty pages before rethrowing.
        const std::size_t old_pages=segment_pages.size();
        try {
            while(segment_pages.size()<pages_needed)
                segment_pages.push_back(SegmentPage{});
        } catch (...) {
            while(segment_pages.size()>old_pages)segment_pages.pop_back();
            throw;
        }
        segment_growth_pages+=segment_pages.size()-old_pages;
        params.tree_capacity=capacity;
        creat_his=false;
    }

    bool tree_index_valid = false;
    bool tree_index_mutation_guard = false;
    // Packed 32-bit open-addressed index, separate from inheritable VM bits.
    // Encodes ((parent*8+key)<<id_bits) | id. Zero marks an empty hash slot.
    // At 12 ID bits the encoding uses at most 27 bits.
    std::vector<uint32_t> tree_index_slots;
    std::size_t tree_index_count = 0;
    int tree_first_free_id = 1; // cap+1 means full; no per-empty-row allocation
    unsigned long long tree_index_rebuilds = 0;
    unsigned long long tree_index_lookups = 0;
    unsigned long long tree_index_updates = 0;
    unsigned long long tree_index_invalidations = 0;
    unsigned long long tree_index_build_rows = 0;
    unsigned long long tree_index_probes = 0;
    unsigned long long tree_index_rehashes = 0;

    static uint32_t tree_hash(unsigned key) {
        // Deterministic multiplicative hash; storage sizes are powers of two.
        uint32_t x=static_cast<uint32_t>(key);
        x^=x>>16; x*=0x7feb352du; x^=x>>15;
        x*=0x846ca68bu; x^=x>>16;
        return x;
    }
    int indexed_tree_find(unsigned key) {
        if(tree_index_slots.empty())return 0;
        const uint32_t mask=(1u<<params.tree_id_bits)-1u;
        const std::size_t size_mask=tree_index_slots.size()-1;
        std::size_t at=tree_hash(key)&size_mask;
        while(tree_index_slots[at]) {
            ++tree_index_probes;
            const uint32_t entry=tree_index_slots[at];
            if((entry>>params.tree_id_bits)==key)return int(entry&mask);
            at=(at+1)&size_mask;
        }
        ++tree_index_probes;
        return 0;
    }
    // Insert only the first matching handle, preserving legacy scan semantics.
    void indexed_tree_put(unsigned key,int id) {
        if(tree_index_slots.empty() ||
           (tree_index_count+1)*10>=tree_index_slots.size()*7) {
            const std::size_t new_size=tree_index_slots.empty()?16:tree_index_slots.size()*2;
            std::vector<uint32_t> next(new_size,0);
            for(uint32_t entry:tree_index_slots)if(entry) {
                const uint32_t old_key=entry>>params.tree_id_bits;
                std::size_t at=tree_hash(old_key)&(new_size-1);
                while(next[at]) {++tree_index_probes;at=(at+1)&(new_size-1);}
                ++tree_index_probes;
                next[at]=entry;
            }
            tree_index_slots.swap(next);
            ++tree_index_rehashes;
        }
        const std::size_t size_mask=tree_index_slots.size()-1;
        std::size_t at=tree_hash(key)&size_mask;
        while(tree_index_slots[at]) {
            ++tree_index_probes;
            if((tree_index_slots[at]>>params.tree_id_bits)==key)return;
            at=(at+1)&size_mask;
        }
        ++tree_index_probes;
        tree_index_slots[at]=(uint32_t(key)<<params.tree_id_bits)|uint32_t(id);
        ++tree_index_count;
    }
    void invalidate_tree_index() {
        if (tree_index_valid) ++tree_index_invalidations;
        tree_index_valid = false;
        std::vector<uint32_t>().swap(tree_index_slots);
        tree_index_count=0;
        tree_first_free_id=1;
    }

    void rebuild_tree_index_if_needed() {
        if (tree_index_valid) return;
        const int base=params.tree_start, cap=params.tree_capacity;
        const int bits=params.tree_id_bits, stride=bits+7;
        if (bits<=5 || !params.tree_index_enabled || base<0 || cap<1 ||
            base+static_cast<long long>(cap)*stride>params.layout.program_start)
            return;
        tree_index_slots.clear();tree_index_count=0;tree_first_free_id=cap+1;
        for(int id=1;id<=cap;++id) {
            ++tree_lookup_rows_examined;
            ++tree_index_build_rows;
            const int row=base+(id-1)*stride;
            if(!memory[row]) { tree_first_free_id=std::min(tree_first_free_id,id); continue; }
            unsigned parent=0,key=0;
            for(int b=1;b<=bits;++b) parent=(parent<<1)|int(memory[row+b]);
            for(int b=bits+1;b<bits+4;++b) key=(key<<1)|int(memory[row+b]);
            indexed_tree_put((parent<<3)|key,id);
        }
        tree_index_valid=true;
        ++tree_index_rebuilds;
    }
    int step_limit = 32;
    bool budget_exhausted = false;
    bool work_insert_blocked = false;
    bool tree_capacity_blocked = false; // wide-mode path transaction failed
    std::vector<bool> written;
    std::vector<bool> read_seen;
    // Optional per-word information widths, in program order. Empty uses
    // the original uniform op_order. The controller must learn/supply this TST.

    bool writable(int addr) const {
        return addr >= params.layout.output_start && addr < params.layout.program_start;
    }

    // Host-controlled capacity increase. Active execution bounds stay unchanged;
    // a program can append complete words before selecting the new window.
    void extend_program_capacity(int words) {
        if (words < 1 || words > 1024 ||
            params.layout.total_size > 1048576 - words * (params.op_order + params.op_lvl))
            throw std::invalid_argument("Invalid program capacity increase");
        const int bits = words * (params.op_order + params.op_lvl);
        params.layout.total_size += bits;
        memory.resize(params.layout.total_size, false);
        written.resize(params.layout.total_size, false);
        read_seen.resize(params.layout.total_size, false);
        memory_his.resize(params.layout.total_size, false);
    }

    // Host-authorized capacity growth for the opt-in wide tree ABI.
    // Wide rows keep their 3-bit action payload inline, so old row addresses
    // and handles remain stable while the program is moved upward. This
    // operation must run BETWEEN guest invocations, not during execution.
    void grow_wide_tree_capacity(int new_capacity) {
        const int bits=params.tree_id_bits,row_bits=bits+7;
        const int old_cap=params.tree_capacity,old_program=params.layout.program_start;
        if(params.tree_segmented_enabled || bits<=5 || old_cap<1 || new_capacity<=old_cap ||
           new_capacity>(1<<bits)-1 ||
           params.tree_start<params.layout.work_start ||
           params.tree_start+old_cap*row_bits!=old_program ||
           params.stable_work_bits<old_cap*row_bits)
            throw std::invalid_argument("Wide tree growth requires contiguous tree-at-work-tail");
        const int delta=(new_capacity-old_cap)*row_bits;
        if(delta>1048576-static_cast<int>(memory.size()) ||
           static_cast<int>(memory.size())!=params.layout.total_size)
            throw std::invalid_argument("Wide tree growth exceeds memory limit");
        // Prepare the modified backing vectors before committing layout.
        // Allocation failure leaves the original object untouched.
        auto new_memory=memory,new_written=written,new_seen=read_seen;
        new_memory.insert(new_memory.begin()+old_program,delta,false);
        new_written.insert(new_written.begin()+old_program,delta,false);
        new_seen.insert(new_seen.begin()+old_program,delta,false);
        auto new_history=new_memory;
        auto new_reg_history=val_reg;
        memory.swap(new_memory);written.swap(new_written);
        read_seen.swap(new_seen);memory_his.swap(new_history);
        val_reg_his.swap(new_reg_history);
        params.tree_capacity=new_capacity;
        params.stable_work_bits+=delta;
        params.layout.program_start+=delta;
        params.layout.total_size+=delta;
        if(pro_1>=old_program)pro_1+=delta;
        if(pro_2>=old_program)pro_2+=delta;
        if(ptr>=old_program)ptr+=delta;
        if(secondary_ptr>=old_program)secondary_ptr+=delta;
        if(output_ptr>=old_program)output_ptr+=delta;
        // Growth extends the vacant tail; the persisted rows and IDs are fixed.
        // Only the derived cache's free-id registry needs the new slots.
        if (tree_index_valid && tree_first_free_id>old_cap)
            tree_first_free_id=old_cap+1;
        // The old checkpoint has a different memory layout. Leave a coherent
        // current-state backing copy, but require an explicit new_his()
        // before it is authorized as a heredity snapshot.
        creat_his=false;
    }

    Hamster(int _id, const HamsterParams& p) : id(_id), params(p), hp(p.initial_hp), age(0) {
        if (!(0 <= p.layout.input_start && p.layout.input_start < p.layout.status_start &&
              p.layout.status_start < p.layout.output_start &&
              p.layout.output_start < p.layout.work_start &&
              p.layout.work_start < p.layout.program_start &&
              p.layout.program_start < p.layout.total_size) || p.layout.val_reg_size < 1 ||
              p.op_order < 4 || p.op_order > 16 || p.op_lvl < 1 || p.op_lvl > 8 ||
              p.unit_cost_per <= 0 || p.stable_work_bits < 0 ||
              p.tree_id_bits < 5 ||
              p.tree_id_bits > (p.tree_segmented_enabled?16:12) ||
              (p.tree_segmented_enabled &&
               (p.tree_id_bits<=5 || p.tree_capacity<1 ||
                p.tree_capacity>(1<<p.tree_id_bits)-1 ||
                p.layout.val_reg_size<p.tree_id_bits+4)) ||
              p.stable_work_bits >= p.layout.program_start-p.layout.work_start)
            throw std::invalid_argument("Invalid hamster memory layout or VM parameters");
        params.layout.total_size += int(Mem_inc_rate * ROUND_outside);
        memory = std::vector<bool>(params.layout.total_size, 0);
        if(p.tree_segmented_enabled){
            const auto pages=(std::size_t(p.tree_capacity)+SEGMENT_PAGE_ROWS-1)/SEGMENT_PAGE_ROWS;
            segment_pages.resize(pages);
            segment_growth_pages=pages;
        }
        val_reg = std::vector<bool>(params.layout.val_reg_size, 0);

        memory_his = std::vector<bool>(params.layout.total_size, 0);
        val_reg_his = std::vector<bool>(params.layout.val_reg_size, 0);


        written.assign(memory.size(), false);
        read_seen.assign(memory.size(), false);
        pro_1 = params.layout.program_start;
        pro_2 = params.layout.total_size - 1;
        hp = params.initial_hp;
        max_hp_his = hp + Adition_hp;
        max_hp_age_his = 1;
        creat_his = false;
        ptr = 0;
        secondary_ptr = 0;
        output_ptr = 0;
        val_ptr = 0;
        stop = false;
    }

    void set_mem_rand() {
        invalidate_tree_index();
        for (int i = params.layout.output_start; i < params.layout.total_size; ++i) {
            memory[i] = rand() % 2;
        }
    }

    bool is_alive() const {
        return hp > 0;
    }


    void write_prob(const Problem& p, int version_bit = -1) {
        int start = params.layout.input_start;
        int end = params.layout.status_start;
        int idx = start + 1;
        size_t bits_needed = 0;
        for (const auto& token : p.question) bits_needed += token.bits.size();
        if (version_bit < -1 || version_bit > 1)
            throw std::invalid_argument("Invalid task version bit");
        if (bits_needed > static_cast<size_t>(end - idx - (version_bit >= 0)))
            throw std::invalid_argument("Problem does not fit input area");
        std::fill(memory.begin() + start, memory.begin() + end, false);
        std::fill(memory.begin() + params.layout.output_start,
                  memory.begin() + params.layout.work_start, false);
        std::fill(written.begin(), written.end(), false);
        std::fill(read_seen.begin(), read_seen.end(), false);
        std::fill(val_reg.begin(), val_reg.end(), false);
        ptr = 0;
        secondary_ptr = 0;
        output_ptr = 0;
        val_ptr = 0;
        stop = false;
        executed_steps = 0;
        budget_exhausted = false;
        work_insert_blocked = false;
        tree_capacity_blocked = false;

        // 將題目 token bits 寫入 input 區
        for (const auto& token : p.question) {
            for (bool bit : token.bits) {
                if (idx >= end) break; // 避免越界寫到狀態區
                memory[idx++] = bit;
            }
        }

        // 補 0（清空未使用部分）
        while (idx < end) {
            memory[idx++] = 0;
        }

        // 設定 control bit：input_start 位置標記為有效
        memory[start] = 1;
        // Optional explicit version mark after the payload/padding. Older
        // programs retain their original data offsets and default format.
        if (version_bit >= 0) memory[end - 1] = version_bit;
    }

    void status_ref() {
        int start = params.layout.status_start;
        int end = params.layout.output_start;
        hp -= basic_use;
        SpiralToken s(std::clamp(int(hp), 0, 127), 7, 1);

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
        pro_1 = params.layout.program_start;
        stop = false;

    }

    void new_his() {
        creat_his = true;
        if(params.tree_segmented_enabled){
            segment_pages_his=segment_pages;
            segment_used_his=segment_used;
        }
        memory_his = memory;
        val_reg_his = val_reg;
        max_hp_his = hp;
        max_hp_age_his = age;
    }

    void copy_hamu(const Hamster& h2) {
        if(h2.params.tree_id_bits>5 && !h2.creat_his)
            throw std::invalid_argument("Wide tree donor requires a published snapshot");
        if (params.op_order != h2.params.op_order || params.op_lvl != h2.params.op_lvl ||
            params.stable_work_bits != h2.params.stable_work_bits ||
            // A snapshot must not reinterpret 9-bit rows or TREE_ACTION's
            // capacity-dependent action-slot offset as another tree layout.
            // Capacity migration requires a separate, explicit transaction.
            params.tree_start != h2.params.tree_start ||
            params.tree_capacity != h2.params.tree_capacity ||
            params.tree_id_bits != h2.params.tree_id_bits ||
            params.tree_segmented_enabled != h2.params.tree_segmented_enabled ||
            params.tree_reject_mask_enabled != h2.params.tree_reject_mask_enabled ||
            params.tree_confirm_three_bits_enabled != h2.params.tree_confirm_three_bits_enabled ||
            params.layout.work_start != h2.params.layout.work_start ||
            params.layout.program_start != h2.params.layout.program_start ||
            val_reg.size() != h2.val_reg_his.size())
            throw std::invalid_argument("Incompatible snapshot layout");
        if (h2.memory_his.size() > 1048576 ||
            h2.memory_his.size() < static_cast<size_t>(params.layout.program_start))
            throw std::invalid_argument("Invalid snapshot capacity");
        if(params.tree_segmented_enabled &&
           (h2.segment_pages_his.size()!=segment_pages.size() ||
            h2.segment_used_his<0 || h2.segment_used_his>params.tree_capacity))
            throw std::invalid_argument("Invalid segmented snapshot");
        params.layout.total_size = static_cast<int>(h2.memory_his.size());
        memory.resize(params.layout.total_size, false);
        memory_his.resize(params.layout.total_size, false);
        written.resize(params.layout.total_size, false);
        read_seen.resize(params.layout.total_size, false);
        for(int i= params.layout.work_start;i<params.layout.total_size;i++){
            memory[i] = h2.memory_his[i];
		}
        //memory = h2.memory_his;
        for (int i = 0; i < h2.val_reg_his.size(); i++) {
            val_reg[i] = h2.val_reg_his[i];
            //val_reg = h2.val_reg_his;
        }
        if(params.tree_segmented_enabled){
            if(h2.segment_pages_his.size()!=segment_pages.size() ||
               h2.segment_used_his<0 || h2.segment_used_his>params.tree_capacity)
                throw std::invalid_argument("Invalid segmented snapshot");
            segment_pages=h2.segment_pages_his;
            segment_used=h2.segment_used_his;
            segment_pages_his=segment_pages;
            segment_used_his=segment_used;
            rebuild_segment_first_free_id();
            invalidate_segment_index();
        }
        // Rebuild non-hereditary caches from the inherited canonical rows.
        invalidate_tree_index();
        // An archive must itself be a valid snapshot donor.
        memory_his = memory;
        val_reg_his = val_reg;
        creat_his = h2.creat_his;
    }

    void change_hamu(int r) {
        invalidate_tree_index();
        for (int i = params.layout.work_start; i < memory.size(); i++) {
            if (rand() % r == 1) {
                memory[i] = !memory[i];
            }
        }

    }

    void use_hp() {
        float cost = float(std::max(0, executed_steps)) / float(params.unit_cost_per);
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
    // Last output-area bit is reserved for VM control, never answer data.
    const int control_bit=h.params.layout.work_start-1;
    if (out_data_start + p.answer.bits.size() > static_cast<size_t>(control_bit))
        return false;
    // Fresh output and explicit write coverage prevent inherited guesses.
    for (int i = 0; i < p.answer.bits.size(); ++i) {
        if (!h.written[out_data_start + i] ||
            p.answer.bits[i] != h.memory[out_data_start + i]) {
            return false;
        }
    }
    for (int addr = out_base; addr < h.params.layout.work_start; ++addr)
        if (addr!=control_bit &&
            h.written[addr] && (addr < out_data_start ||
            addr >= out_data_start + static_cast<int>(p.answer.bits.size()))) return false;
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
    const int width = h.params.op_order + h.params.op_lvl;
    if (h.stop) return;
    if (h.pro_1 < h.params.layout.program_start || h.pro_2 < h.pro_1 ||
        h.pro_2 >= static_cast<int>(h.memory.size())) { h.stop = true; return; }
    // One question is a transaction for writable memory when strict INSERT
    // runs out of work space. Preserve the blocked flag and read trace.
    const int writable_start=h.params.layout.output_start;
    const int writable_end=h.params.layout.program_start;
    const std::vector<bool> memory_before(h.memory.begin()+writable_start,
                                           h.memory.begin()+writable_end);
    const std::vector<bool> written_before(h.written.begin()+writable_start,
                                            h.written.begin()+writable_end);
    const auto registers_before=h.val_reg;
    const int segment_used_before=h.segment_used;
    const int segment_first_free_before=h.segment_first_free_id;
    std::vector<std::pair<int,uint32_t>> segment_action_undo;
    // Includes reused holes: high-watermark-only rollback is insufficient.
    std::vector<std::pair<int,uint32_t>> segment_insert_undo;
    // A window has its own cursor. SET_PTR1 can change the next window now or
    // when the current window reaches its end. All windows share one step budget.
    auto order_at = [&](int ordinal) {
        if (ordinal < 0) return -1;
        return h.params.op_order;
    };
    auto start_at = [&](int ordinal) {
        if(ordinal<0)return -1;
        const long long at=static_cast<long long>(h.params.layout.program_start)
                           +static_cast<long long>(ordinal)*width;
        return at<=static_cast<long long>(h.memory.size())?int(at):-1;
    };
    auto ordinal_at = [&](int address, bool end_position) {
        const long long offset=static_cast<long long>(address)-h.params.layout.program_start
                              -(end_position?width-1:0);
        if(offset<0||offset%width)return -1;
        const long long ordinal=offset/width;
        return ordinal<=INT_MAX &&
               static_cast<long long>(h.params.layout.program_start)+(ordinal+1)*width<=
                   static_cast<long long>(h.memory.size())?int(ordinal):-1;
    };
    auto window_count = [&](int from,int to) {
        const int initial=ordinal_at(from,false);
        if(initial<0)return -1;
        return (to-from+1)/width;
    };
    int first = h.pro_1;
    int end = h.pro_2;
    int count = window_count(first,end);
    if(count<0){h.stop=true;return;}
    int jump_mode = 0; // 0=after this window, 1=immediate
    bool pending = false;
    auto token = [&](int i, int& value) {
        if (i < 0 || i >= count) return false;
        const int ordinal=ordinal_at(first,false)+i;
        const int base=start_at(ordinal),n=order_at(ordinal);
        if(base<0||n<4||n>16||base+n+h.params.op_lvl-1>end)return false;
        value = 0;
        for (int j = 0; j < n; ++j)
            value = (value << 1) | h.memory[base + j];
        for (int j = n; j < n+h.params.op_lvl; ++j)
            if (h.memory[base + j]) return false;
        return true;
    };
    auto put = [&](int address, bool value) {
        if (h.writable(address)) {
            if (h.tree_index_valid && !h.tree_index_mutation_guard &&
                address>=h.params.tree_start &&
                address<h.params.tree_start+
                        h.params.tree_capacity*(h.params.tree_id_bits+7) &&
                (address-h.params.tree_start)%(h.params.tree_id_bits+7)<h.params.tree_id_bits+4)
                h.invalidate_tree_index();
            h.memory[address] = value; h.written[address] = true;
        }
    };
    for (int i = 0;;) {
        if (i >= count) {
            if (!pending) return;
            first = h.pro_1;
            end = h.pro_2;
            if (first < h.params.layout.program_start || first > end ||
                end >= static_cast<int>(h.memory.size())) { h.stop = true; return; }
            count = window_count(first,end);
            if(count<0){h.stop=true;return;}
            pending = false;
            i = 0;
            continue;
        }
        if (h.executed_steps >= h.step_limit) {
            h.budget_exhausted = true; h.stop = true; return;
        }
        ++h.executed_steps;
        int code = 0, param = 0;
        const int op_ordinal=ordinal_at(first,false)+i;
        if (!token(i, code) || code > 31 || (code >= 16 && order_at(op_ordinal) < 5)) { ++i; continue; }
        const auto op = static_cast<SpiralOp>(code);
        if (op == SpiralOp::OUT_AREA) { h.stop = true; return; }
        if (!token(i + 1, param)) { ++i; continue; }
        const int param_order=order_at(op_ordinal+1);
        const int sign = 1 << (param_order - 1);
        const int delta = (param & sign) ? param - sign : -param;
        bool jump_now = false;
        switch (op) {
        case SpiralOp::TREE_ACTION: {
            if(h.params.tree_segmented_enabled){
                const int bits=h.params.tree_id_bits;
                // Params 0/1 retain the legacy 2-bit confirmed answer ABI.
                // Params 2/3 are an opt-in eight-candidate failure memory:
                // candidate = register[bits+1..bits+3], MSB first.
                // 2=read rejected bit, 3=mark candidate rejected (idempotent).
                // result register[bits]=rejected; [bits+4]=node exists.
                // Candidate bits are preserved; this does not claim a correct answer.
                // Extended confirmed answer ABI (opt-in only): param 4=read,
                // 5=commit. Low two bits remain in row[2:3], high bit in
                // row[31]. Input candidate is register[bits+1..bits+3].
                // Output: [bits]=confirmed, [bits+1..bits+3]=answer,
                // [bits+4]=node exists. Never reinterpret legacy param 0/1.
                if(param==4 || param==5){
                    if(!h.params.tree_confirm_three_bits_enabled ||
                       h.val_reg.size()<std::size_t(bits+5))break;
                    int id=0;
                    for(int b=0;b<bits;++b)id=(id<<1)|int(h.val_reg[b]);
                    const uint32_t row=h.segment_row(id);
                    const bool exists=(row&1u)!=0;
                    if(exists && param==5){
                        const unsigned answer=(unsigned(h.val_reg[bits+1])<<2)|
                            (unsigned(h.val_reg[bits+2])<<1)|unsigned(h.val_reg[bits+3]);
                        const uint32_t replacement=(row&~(14u|(1u<<31)))|
                            ((4u|(answer&3u))<<1)|((answer&4u)?(1u<<31):0u);
                        if(replacement!=row){
                            segment_action_undo.emplace_back(id,row);
                            h.segment_row_ref(id)=replacement;
                        }
                    }
                    const uint32_t state=h.segment_row(id);
                    const bool confirmed=exists && (state&8u)!=0;
                    const unsigned answer=((state>>31)&1u)<<2 | ((state>>1)&3u);
                    h.val_reg[bits]=confirmed;
                    for(int b=0;b<3;++b)h.val_reg[bits+1+b]=confirmed && ((answer>>(2-b))&1u);
                    h.val_reg[bits+4]=exists;
                    break;
                }
                if(param>=2){
                    if(!h.params.tree_reject_mask_enabled || param>3 ||
                       h.val_reg.size()<std::size_t(bits+5))break;
                    int id=0;
                    for(int b=0;b<bits;++b)id=(id<<1)|int(h.val_reg[b]);
                    const uint32_t row=h.segment_row(id);
                    const bool exists=(row&1u)!=0;
                    unsigned candidate=0;
                    for(int b=bits+1;b<bits+4;++b)
                        candidate=(candidate<<1)|unsigned(h.val_reg[b]);
                    if(exists&&param==3){
                        const uint32_t bit=uint32_t(1u)<<(23+candidate);
                        if(!(row&bit)){
                            segment_action_undo.emplace_back(id,row);
                            h.segment_row_ref(id)=row|bit;
                        }
                    }
                    h.val_reg[bits]=exists &&
                        ((h.segment_row(id)>>(23+candidate))&1u);
                    h.val_reg[bits+4]=exists;
                    break;
                }
                if(h.val_reg.size()<std::size_t(bits+3)||param>1)break;
                int id=0;
                for(int b=0;b<bits;++b)id=(id<<1)|int(h.val_reg[b]);
                const uint32_t row=h.segment_row(id);
                if(!(row&1u)){
                    h.val_reg[bits]=h.val_reg[bits+1]=h.val_reg[bits+2]=false;
                    break;
                }
                if(param==1){
                    segment_action_undo.emplace_back(id,row);
                    const unsigned action=4u|(unsigned(h.val_reg[bits+1])<<1)|unsigned(h.val_reg[bits+2]);
                    h.segment_row_ref(id)=(row&~(14u | (h.params.tree_confirm_three_bits_enabled ? (1u<<31) : 0u)))|(action<<1);
                }
                const unsigned state=(h.segment_row(id)>>1)&7u;
                h.val_reg[bits]=(state&4u)!=0;
                h.val_reg[bits+1]=(state&4u)!=0 && (state&2u)!=0;
                h.val_reg[bits+2]=(state&4u)!=0 && (state&1u)!=0;
                break;
            }
            // Versioned tree row: [live][parent bits][3 key bits]; action
            // slots follow all rows in legacy mode; wide rows store actions
            // inline to keep offsets invariant when capacity grows.
            const int base=h.params.tree_start,cap=h.params.tree_capacity;
            const int bits=h.params.tree_id_bits;
            const int row_bits=(bits>5?bits+7:bits+4);
            const bool configured=base>=h.params.layout.work_start &&
                cap>0 && cap<=(1<<bits)-1 &&
                base>=h.params.layout.program_start-h.params.stable_work_bits &&
                h.params.stable_work_bits>=cap*(row_bits+(bits>5?0:3)) &&
                base+cap*(row_bits+(bits>5?0:3))<=h.params.layout.program_start &&
                h.val_reg.size()>=static_cast<std::size_t>(bits+3);
            if(!configured||param>1)break;
            int id=0;
            for(int b=0;b<bits;++b)id=(id<<1)|int(h.val_reg[b]);
            const bool exists=id>0&&id<=cap&&h.memory[base+(id-1)*row_bits];
            const int slot=(bits>5?base+(id-1)*row_bits+bits+4
                                    :base+cap*row_bits+(id-1)*3);
            if(!exists){
                h.val_reg[bits]=false;h.val_reg[bits+1]=false;h.val_reg[bits+2]=false;
                break;
            }
            if(param==1){
                const bool high=h.val_reg[bits+1],low=h.val_reg[bits+2];
                put(slot+1,high);put(slot+2,low);put(slot,true);
            }
            const bool committed=h.memory[slot];
            h.val_reg[bits]=committed;
            h.val_reg[bits+1]=committed&&h.memory[slot+1];
            h.val_reg[bits+2]=committed&&h.memory[slot+2];
            break;
        }
        case SpiralOp::TREE_FIND:
        case SpiralOp::TREE_ADD:
        case SpiralOp::TREE_FIND_REG:
        case SpiralOp::TREE_ADD_REG: {
            if(h.params.tree_segmented_enabled){
                const int bits=h.params.tree_id_bits,cap=h.params.tree_capacity;
                const bool from_reg=op==SpiralOp::TREE_FIND_REG||op==SpiralOp::TREE_ADD_REG;
                if(h.val_reg.size()<std::size_t(bits+(from_reg?4:1)))break;
                int key=param;
                if(from_reg){
                    key=0;for(int b=bits+1;b<bits+4;++b)key=(key<<1)|int(h.val_reg[b]);
                }
                if(key>7)break;
                int parent=0;for(int b=0;b<bits;++b)parent=(parent<<1)|int(h.val_reg[b]);
                const bool parent_exists=parent==0 ||
                    (parent<=h.segment_used && (h.segment_row(parent)&1u));
                int found=parent_exists?h.segment_find(parent,key):0;
                if(!found&&parent_exists&&(op==SpiralOp::TREE_ADD||op==SpiralOp::TREE_ADD_REG)){
                    if(h.segment_first_free_id>cap){
                        h.tree_capacity_blocked=true;h.stop=true;
                        // Atomic guest transaction: roll back only rows touched
                        // by tree opcodes, without copying the entire tree.
                        for(auto it=segment_action_undo.rbegin();it!=segment_action_undo.rend();++it)
                            h.segment_row_ref(it->first)=it->second;
                        for(auto it=segment_insert_undo.rbegin();it!=segment_insert_undo.rend();++it)
                            h.segment_row_ref(it->first)=it->second;
                        h.segment_used=segment_used_before;
                        h.segment_first_free_id=segment_first_free_before;
                        h.invalidate_segment_index();
                        std::copy(memory_before.begin(),memory_before.end(),
                                  h.memory.begin()+writable_start);
                        std::copy(written_before.begin(),written_before.end(),
                                  h.written.begin()+writable_start);
                        h.val_reg=registers_before;
                        for(int b=0;b<=bits;++b)h.val_reg[b]=false;
                        return;
                    }
                    // Lowest free ID wins. The cursor advances monotonically
                    // across occupied rows, so dense growth is amortized O(1).
                    found=h.segment_first_free_id;
                    if(found>h.segment_used)++h.segment_used;
                    segment_insert_undo.emplace_back(found,h.segment_row_ref(found));
                    h.segment_row_ref(found)=(uint32_t(parent)<<7)|(uint32_t(key)<<4)|1u;
                    int next=found+1;
                    while(next<=h.segment_used && (h.segment_row(next)&1u))++next;
                    h.segment_first_free_id=next;
                    if(h.segment_edge_index_valid)
                        h.segment_edge_index.emplace(Hamster::segment_edge(parent,key),found);
                }
                for(int b=0;b<bits;++b)h.val_reg[b]=(found>>(bits-1-b))&1;
                h.val_reg[bits]=found!=0;
                break;
            }
            const int base=h.params.tree_start,cap=h.params.tree_capacity;
            const int bits=h.params.tree_id_bits;
            const int row_bits=(bits>5?bits+7:bits+4);
            int lookup_key=param;
            const bool key_in_register=op==SpiralOp::TREE_FIND_REG||op==SpiralOp::TREE_ADD_REG;
            if(key_in_register && h.val_reg.size()>=static_cast<std::size_t>(bits+4)) {
                lookup_key=0;
                for(int b=bits+1;b<bits+4;++b)
                    lookup_key=(lookup_key<<1)|int(h.val_reg[b]);
            }
            const bool configured=base>=h.params.layout.work_start &&
                cap>0 && cap<=(1<<bits)-1 &&
                h.params.stable_work_bits>=cap*row_bits &&
                base>=h.params.layout.program_start-h.params.stable_work_bits &&
                base+cap*row_bits<=h.params.layout.program_start &&
                lookup_key<=7 &&
                h.val_reg.size()>=static_cast<std::size_t>(bits+(key_in_register?4:1));
            if(!configured)break;
            int parent=0;
            for(int bit=0;bit<bits;++bit)parent=(parent<<1)|int(h.val_reg[bit]);
            bool parent_exists=parent==0;
            if(parent>0&&parent<=cap)parent_exists=h.memory[base+(parent-1)*row_bits];
            int found=0,free_id=0;
            const bool indexed=bits>5 && h.params.tree_index_enabled;
            const unsigned long long index_key=
                (static_cast<unsigned long long>(parent)<<3)|lookup_key;
            if(parent_exists && indexed) {
                h.rebuild_tree_index_if_needed();
                ++h.tree_index_lookups;
                found=h.indexed_tree_find(static_cast<unsigned>(index_key));
                if(h.tree_first_free_id<=cap)free_id=h.tree_first_free_id;
            } else if(parent_exists) for(int id=1;id<=cap;++id) {
                ++h.tree_lookup_rows_examined;
                const int row=base+(id-1)*row_bits;
                if(!h.memory[row]){if(!free_id)free_id=id;continue;}
                int p=0,key=0;
                for(int b=1;b<=bits;++b)p=(p<<1)|int(h.memory[row+b]);
                for(int b=bits+1;b<bits+4;++b)key=(key<<1)|int(h.memory[row+b]);
                if(p==parent&&key==lookup_key){found=id;break;}
            }
            if(!found&&parent_exists&&
               (op==SpiralOp::TREE_ADD||op==SpiralOp::TREE_ADD_REG)&&free_id) {
                found=free_id;
                const bool update_index=indexed && h.tree_index_valid;
                if(update_index) h.tree_index_mutation_guard=true;
                const int row=base+(found-1)*row_bits;
                for(int b=0;b<bits;++b)put(row+1+b,(parent>>(bits-1-b))&1);
                for(int b=0;b<3;++b)put(row+bits+1+b,(lookup_key>>(2-b))&1);
                const int slot=(bits>5?base+(found-1)*row_bits+bits+4
                                        :base+cap*row_bits+(found-1)*3);
                if(h.params.stable_work_bits>=cap*(row_bits+(bits>5?0:3)) &&
                   base+cap*(row_bits+(bits>5?0:3))<=h.params.layout.program_start)
                    put(slot,false);
                put(row,true); // publish only after writing the full parent/key
                if(update_index) {
                    h.tree_index_mutation_guard=false;
                    // put() deliberately invalidates on arbitrary tree writes;
                    // this single verified tree insertion can restore the cache.
                    h.indexed_tree_put(static_cast<unsigned>(index_key),found);
                    if(h.tree_first_free_id==found) {
                        int next=found+1;
                        while(next<=cap) {
                            ++h.tree_lookup_rows_examined;
                            if(!h.memory[base+(next-1)*row_bits])break;
                            ++next;
                        }
                        h.tree_first_free_id=next;
                    }
                    h.tree_index_valid=true;
                    ++h.tree_index_updates;
                }
            }
            // Wide mode treats a guest invocation as an atomic tree-growth
            // transaction if allocation fails. A path may require multiple
            // TREE_ADD instructions, so publishing its prefix alone would
            // waste resources and break retries. Legacy mode stays unchanged.
            if(!found && parent_exists &&
               (op==SpiralOp::TREE_ADD||op==SpiralOp::TREE_ADD_REG)&&
               bits>5 && !free_id) {
                h.tree_capacity_blocked=true;
                h.stop=true;
                h.invalidate_tree_index(); // the whole guest transaction rolls back
                std::copy(memory_before.begin(),memory_before.end(),
                          h.memory.begin()+writable_start);
                std::copy(written_before.begin(),written_before.end(),
                          h.written.begin()+writable_start);
                h.val_reg=registers_before;
                for(int b=0;b<bits;++b)h.val_reg[b]=false;
                h.val_reg[bits]=false;
                return;
            }
            for(int b=0;b<bits;++b)h.val_reg[b]=(found>>(bits-1-b))&1;
            h.val_reg[bits]=found!=0;
            break;
        }
        case SpiralOp::XOR_REG:
            for(int j=0;j<param && h.val_ptr+j+1<int(h.val_reg.size());++j)
                h.val_reg[h.val_ptr+j]=h.val_reg[h.val_ptr+j]!=h.val_reg[h.val_ptr+j+1];
            break;
        case SpiralOp::SWAP_PTR:
            std::swap(h.ptr,h.secondary_ptr);
            break;
        case SpiralOp::SWAP_OUTPUT_PTR:
            std::swap(h.ptr,h.output_ptr);
            break;
        case SpiralOp::JUMP_MODE:
            if (param == 0 || param == 1) jump_mode = param;
            break;
        case SpiralOp::SET_AREA:
            switch (param % 8) {
            case 0: h.ptr = h.params.layout.input_start; break;
            case 1: h.ptr = h.params.layout.status_start; break;
            case 2: h.ptr = h.params.layout.output_start; break;
            case 3: h.ptr = h.params.layout.work_start; break;
            case 4: h.ptr = std::min(h.params.layout.program_start - 1,
                                    h.params.layout.work_start + 10 * width); break;
            case 5: h.ptr = h.pro_1; break;
            case 6: h.ptr = h.pro_2; break;
            case 7: h.stop = true; break;
            }
            break;
        case SpiralOp::MOVE_PTR:
            h.ptr = std::clamp(h.ptr + delta * width, 0, static_cast<int>(h.memory.size()) - 1);
            break;
        case SpiralOp::SMOVE_PTR:
            h.ptr = std::clamp(h.ptr + delta, 0, static_cast<int>(h.memory.size()) - 1);
            break;
        case SpiralOp::MOVE_VAL_PTR:
            h.val_ptr = std::clamp(h.val_ptr + delta, 0, static_cast<int>(h.val_reg.size()) - 1);
            break;
        case SpiralOp::JUMP_IF_1:
        case SpiralOp::JUMP_IF_LOCAL:
        case SpiralOp::JUMP_IF_FORWARD_WIDE:
            // A false predicate consumes the pair and leaves the window intact.
            if (h.val_ptr >= static_cast<int>(h.val_reg.size()) || !h.val_reg[h.val_ptr]) break;
            [[fallthrough]];
        case SpiralOp::JUMP_LOCAL:
        case SpiralOp::JUMP_BACK:
        case SpiralOp::JUMP_BACK_WIDE:
        case SpiralOp::JUMP_FORWARD_WIDE:
        case SpiralOp::SET_PTR1:
            {const int target=(op == SpiralOp::JUMP_BACK ? op_ordinal-param :
                               op == SpiralOp::JUMP_BACK_WIDE ? op_ordinal-2*param :
                               op == SpiralOp::JUMP_IF_FORWARD_WIDE ? op_ordinal+2*param :
                               op == SpiralOp::JUMP_FORWARD_WIDE ? op_ordinal+2*param :
                               (op == SpiralOp::JUMP_IF_LOCAL || op == SpiralOp::JUMP_LOCAL) ? op_ordinal+delta :
                               ordinal_at(h.pro_1,false)+delta);
             const int address=start_at(target);
             if(target<0||address<h.params.layout.program_start||order_at(target)<4||
                address+order_at(target)+h.params.op_lvl>static_cast<int>(h.memory.size())){h.stop=true;break;}
             h.pro_1=address;}
            // Targets are word-aligned because the displacement is in words.
            if (h.pro_1 != first) {
                if (jump_mode) jump_now = true;
                else pending = true;
            }
            break;
        case SpiralOp::SET_PTR2:
            {const int target=ordinal_at(h.pro_2,true)+delta;
             const int address=start_at(target),n=order_at(target);
             if(target<0||address<h.params.layout.program_start||n<4||n>16||
                address+n+h.params.op_lvl>static_cast<int>(h.memory.size())){h.stop=true;break;}
             h.pro_2=address+n+h.params.op_lvl-1;}
            break;
        case SpiralOp::READ:
        case SpiralOp::WRITE_VAL:
        case SpiralOp::XOR:
        case SpiralOp::AND:
        case SpiralOp::OR:
            for (int j = 0; j < param &&
                    h.ptr + j < static_cast<int>(h.memory.size()) &&
                    h.val_ptr + j < static_cast<int>(h.val_reg.size()); ++j) {
                const int address = h.ptr + j;
                const bool reg = h.val_reg[h.val_ptr + j];
                if (op == SpiralOp::READ) {
                    h.val_reg[h.val_ptr + j] = h.memory[address];
                    h.read_seen[address] = true;
                } else if (op == SpiralOp::WRITE_VAL) put(address, reg);
                else if (op == SpiralOp::XOR) put(address, h.memory[address] != reg);
                else if (op == SpiralOp::AND) put(address, h.memory[address] && reg);
                else put(address, h.memory[address] || reg);
            }
            break;
        case SpiralOp::WRITE_0:
        case SpiralOp::WRITE_1:
            for (int j = 0; j < param && h.ptr < static_cast<int>(h.memory.size()); ++j)
                put(h.ptr++, op == SpiralOp::WRITE_1);
            break;
        case SpiralOp::INSERT:
        case SpiralOp::DELETE: {
            // Work area only. VAG exchanges the displaced bits; size stays fixed.
            const int end = h.params.layout.program_start-h.params.stable_work_bits;
            if (h.ptr < h.params.layout.work_start || h.ptr >= end) break;
            const int n = std::min({param, end - h.ptr,
                                   static_cast<int>(h.val_reg.size()) - h.val_ptr});
            std::vector<bool> incoming(n), outgoing(n);
            for (int j = 0; j < n; ++j) {
                incoming[j] = h.val_reg[h.val_ptr + j];
                outgoing[j] = h.memory[op == SpiralOp::INSERT ? end - n + j : h.ptr + j];
            }
            // Never discard a live bit at the end of the work area. An
            // explicit blocked result is safer than an unnoticed VAG spill.
            if (h.params.strict_work_insert && op == SpiralOp::INSERT &&
                std::any_of(outgoing.begin(),outgoing.end(),[](bool bit){return bit;})) {
                h.work_insert_blocked = true;
                h.stop = true;
                h.invalidate_tree_index();
                std::copy(memory_before.begin(),memory_before.end(),
                          h.memory.begin()+writable_start);
                std::copy(written_before.begin(),written_before.end(),
                          h.written.begin()+writable_start);
                h.val_reg=registers_before;
                return;
            }
            if (op == SpiralOp::INSERT) {
                for (int j = end - 1; j >= h.ptr + n; --j) put(j, h.memory[j - n]);
                for (int j = 0; j < n; ++j) put(h.ptr + j, incoming[j]);
            } else {
                for (int j = h.ptr; j < end - n; ++j) put(j, h.memory[j + n]);
                for (int j = 0; j < n; ++j) put(end - n + j, incoming[j]);
            }
            for (int j = 0; j < n; ++j) h.val_reg[h.val_ptr + j] = outgoing[j];
            break;
        }
        default: break;
        }
        if (jump_now) {
            first = h.pro_1;
            end = h.pro_2;
            if (first < h.params.layout.program_start || first > end ||
                end >= static_cast<int>(h.memory.size())) { h.stop = true; return; }
            count = window_count(first,end);
            if(count<0){h.stop=true;return;}
            pending = false;
            i = 0;
            continue;
        }
        i += 2;
        if (h.stop) return;
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


#ifdef HAMU_LEGACY_MAIN
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

#endif // HAMU_LEGACY_MAIN: use hamu_experiment.cpp for the reproducible experiment.

