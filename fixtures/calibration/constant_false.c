#include <stdio.h>

int main(void) {
    int result = 0;
    if (0) {
        result = 10; // @cov then 0 elided
    } else {
        result = 20; // @cov else 1
    }
    printf("%d\n", result); // @cov output 1
    return 0; // @cov return 1
}
