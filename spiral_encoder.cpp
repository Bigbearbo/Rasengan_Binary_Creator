#include <iostream>
#include <vector>
using namespace std;

int test_n = 10; // 要產生幾組螺旋語編碼 // Number of spiral codes to generate
vector<vector<char>> c(test_n); // 儲存每個數字的編碼 // Stores each number's spiral code
int level = 1;  // 目前階層 // Current level
int up = 1;     // 下一次升階的臨界點 // Threshold for next level upgrade

// 螺旋語加法函式（進位演算法）
// Spiral number increment function (handles carry)
void add(vector<char> &code) {
    int side = code.size() % 2;
    int i = 0;
    int direction;

    if (!side) {
        // 偶數長度：從左往右加 // Even length: increment from left
        i = 0;
        direction = 1;
    } else {
        // 奇數長度：從右往左加 // Odd length: increment from right
        i = code.size() - 2;
        direction = -1;
    }

    // 加一並處理進位 // Add and handle carry
    code[i] += 1;
    while (code[i] == '2') {
        code[i] = '0';
        i = i + direction;

        // 防止越界：若 i 超出範圍，補一個 '1' // Prevent out-of-bound
        if (i < 0 || i >= (int)code.size()) {
            code.insert(direction > 0 ? code.begin() : code.end(), '1');
            break;
        }
        code[i] += 1;
    }
}

// 輸出位元 // Print bit vector
void print_bits(const vector<char>& bits) {
    for (char ch : bits) cout << ch;
    cout << endl;
}

int main() {
    // 初始編碼：'10' 表示 1 階的 0 // Initial code: '10' is level 1, value 0
    c[0].push_back('1');
    c[0].push_back('0');

    for (int i = 0; i < test_n; i++) {
        if (i > 0) {
            c[i] = c[i - 1]; // 複製前一組 // Copy previous code
            add(c[i]);       // 加一 // Increment
        }

        // 升階處理 // Level upgrade handling
        if (i == up) {
            level += 1;
            up = (up + 1) * 2 - 1;

            cout << "【升階 Upgrade】到第 " << level << " 階，從 0 到 " << i << " 皆補 0 升階位元\n";
            for (int j = 0; j <= i; j++) {
                c[j].push_back('0'); // 升階時在後面加 0 // Add level suffix
                cout << j << " 階: " << level << " 編碼 code: ";
                print_bits(c[j]);
                cout << endl;
            }
        } else {
            cout << i << " 階: " << level << " 編碼 code: ";
            print_bits(c[i]);
            cout << endl;
        }
    }

    cout << "螺旋語產生完成 Spiral code generation complete." << endl;
    return 0;
}
