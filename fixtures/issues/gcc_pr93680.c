#include <stdio.h>

static int f(int s, int n) {
    int p = 0;
    switch (s) {
    case 0: // @id selected_case
        do { p++; } while (--n);
        return p; // @id selected_return
    case 1:
        do { p++; } while (--n);
        return p;
    default:
        return 0;
    }
}

int main(void) {
    int result = f(0, 3);
    printf("%d\n", result);
    return 0;
}
