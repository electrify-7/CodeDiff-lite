int f(int a) {
    int res = ({
        if (a) return 42;
        0;
    });
    return res;
}

int main(void) {
    return f(1) != 42;
}
