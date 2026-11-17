#include <stdio.h>

// Candidate C: Backward goto loop leaks loop iteration counter to closing brace
// The "Return Paradox":
// - Without `return;`, llvm-cov reports the closing brace with count 1.
// - Simply adding `return;` causes llvm-cov to report the closing brace with count 1,000,000!
int test_goto_leak(int n) {
    int i = 0;
loop:
    i++;
    if (i < n)
        goto loop;
    return i;
}

int main(void) {
    test_goto_leak(100);
    return 0;
}
