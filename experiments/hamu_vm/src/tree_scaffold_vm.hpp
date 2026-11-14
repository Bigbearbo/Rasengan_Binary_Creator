#pragma once
#include <vector>

// Fixed n=3 question: 01 | category | operator | data. The guest reads both
// keys and adds missing nodes; TREE_ADD_REG is idempotent on existing paths.
// The tree starts at its implicit root. No meaning or action is installed.
inline std::vector<int> tree_scaffold_question_program(){
    return {16,1,
            0,0,14,18,8,22,4,3,31,0, // read category -> add under root
            8,1,18,20,15,0,          // stop when root table was full
            0,0,14,22,8,17,4,3,31,0, // read operator -> add under category
            15,0};
}
