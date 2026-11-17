#include <stdio.h>

int eval(int x) {
    int res = _Generic(x,
        int: 
            x + 10,
        float: 
            (
                printf("Float branch executed!\n"),
                x * 100
            ),
        double: 
            (
                printf("Double branch executed!\n"),
                x * 1000
            )
    );
    return res;
}

int main(void) {
    eval(1);
    return 0;
}
