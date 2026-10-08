#include <stdio.h>

int main(void) {
    int limit = 0;
    int i = 0;
    int result = 0;
    while (i < limit) {
        result += 2; // @cov body 0
        i++; // @cov increment 0
    }
    printf("%d\n", result); // @cov output 1
    return 0; // @cov return 1
}
