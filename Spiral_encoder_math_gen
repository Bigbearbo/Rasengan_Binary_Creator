#include <vector>
#include <iostream>
#include <stdexcept>
#include <cstdlib>
#include <ctime>

struct SpiralToken {
    int value;
    int order;
    int level;
    std::vector<bool> bits;

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

struct Problem {
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

        SpiralToken A(a, order, level);
        SpiralToken B(b, order, level);
        SpiralToken R(result, order, level);
        SpiralToken Op(op, order, level);
        SpiralToken End(END_CODE, order, level);

        std::vector<SpiralToken> q;
        q.push_back(A);
        q.push_back(Op);
        if (op == 12 || op == 11) q.push_back(B);
        q.push_back(End);

        std::string readable = std::to_string(a) + " " + opStr;
        if (op == 12 || op == 11) readable += " " + std::to_string(b);
        readable += " 。→ " + std::to_string(result);

        return Problem{q, R, readable};
    }
}

int main() {
    srand(time(0));
    int order = 4, level = 1;
    std::vector<Problem> problems;

    for (int i = 0; i < 10; ++i) {
        Problem p = generateOneProblem(order, level);
        problems.push_back(p);

        std::cout << "可讀題目：" << p.readable << std::endl;
        std::cout << "題目螺旋碼：" << std::endl;
        for (auto& token : p.question) token.print();
        std::cout << "答案螺旋碼：" << std::endl;
        p.answer.print();
        std::cout << "-----------------------------\n";
    }

    return 0;
}
