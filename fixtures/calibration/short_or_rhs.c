#include <stdio.h>

static int calls = 0;

static int rhs(void) {
    calls++; // @cov rhs_calls 1
    return 1; // @cov rhs_return 1
}

int main(void) {
    int left = 0;
    int result = 0;
    if (left || rhs()) {
        result = 7; // @cov then 1
    } else {
        result = 9; // @cov else 0
    }
    printf("%d %d\n", result, calls); // @cov output 1
    return 0; // @cov return 1
}
