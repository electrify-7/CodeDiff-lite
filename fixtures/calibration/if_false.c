#include <stdio.h>

int main(void) {
    int x = -2;
    int result = 0;
    if (x > 0) {
        result = 10; // @cov then 0
    } else {
        result = 20; // @cov else 1
    }
    printf("%d\n", result); // @cov output 1
    return 0; // @cov return 1
}
