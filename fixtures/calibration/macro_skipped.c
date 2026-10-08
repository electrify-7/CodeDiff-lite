#include <stdio.h>

#define ADD(target, value) do { (target) += (value); } while (0)

int main(void) {
    int enabled = 0;
    int result = 0;
    if (enabled) {
        ADD(result, 5); // @cov invocation 0
    }
    printf("%d\n", result); // @cov output 1
    return 0; // @cov return 1
}
