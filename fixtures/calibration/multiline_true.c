#include <stdio.h>

int main(void) {
    int a = 1;
    int b = 2;
    int result = 0;
    if (
        a > 0 &&
        b > 0
    ) {
        result = 12; // @cov then 1
    } else {
        result = 34; // @cov else 0
    }
    printf("%d\n", result); // @cov output 1
    return 0; // @cov return 1
}
