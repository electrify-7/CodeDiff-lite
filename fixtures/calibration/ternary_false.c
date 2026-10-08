#include <stdio.h>

int main(void) {
    int selector = 0;
    int result = selector ? 11 : 22; // @cov selection 1
    printf("%d\n", result); // @cov output 1
    return 0; // @cov return 1
}
