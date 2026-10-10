#include <stdio.h>

#define EARLY_RETURN \
    if (b) \
        return;

static int count;
static int barrier;

static void foo(int a, int b) {
    do {
        if (a)
            return;
        barrier++;
        EARLY_RETURN;
        count++; // @id following_statement
    } while (0);
}

int main(void) {
    foo(1, 0);
    foo(1, 0);
    foo(1, 0);
    foo(0, 1);
    foo(0, 1);
    foo(0, 0);
    printf("%d\n", count);
    return 0;
}
