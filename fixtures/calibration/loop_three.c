#include <stdio.h>

int main(void) {
    int limit = 3;
    int result = 0;
    for (int i = 0; i < limit; i++) {
        result += 2; // @cov body 3
    }
    printf("%d\n", result); // @cov output 1
    return 0; // @cov return 1
}
