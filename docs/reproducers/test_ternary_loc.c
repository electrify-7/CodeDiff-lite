int test_tern(int a, int b, int c) {
    int x = a ?
        b :
        c;
    return x;
}

int main(void) {
    test_tern(0, 2, 3);
    return 0;
}
