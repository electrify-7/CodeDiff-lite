#include <stdio.h>

int main(void) {
    int result = 0;
    if (1) {
        result = 10; // @cov then 1
    } else {
        result = 20; // @cov else 0 elided
    }
    printf("%d\n", result); // @cov output 1
    return 0; // @cov return 1
}
