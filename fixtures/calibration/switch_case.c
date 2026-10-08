#include <stdio.h>

int main(void) {
    int selector = 1;
    int result = 0;
    switch (selector) {
    case 1:
        result = 11; // @cov case_one 1
        break;
    case 2:
        result = 22; // @cov case_two 0
        break;
    default:
        result = 33; // @cov default 0
        break;
    }
    printf("%d\n", result); // @cov output 1
    return 0; // @cov return 1
}
