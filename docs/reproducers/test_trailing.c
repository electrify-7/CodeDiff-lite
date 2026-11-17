int test(const char *a, const char *b) {
    if (a == 0 ||
        b == 0) {
        return 1;
    }
    return 0;
}

int main(void) {
    test("x", "y");
    return 0;
}
