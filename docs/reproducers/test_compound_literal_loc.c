struct Point {
    int x;
    int y;
};

void use(struct Point *p) {}

void test_pt(int a, int b) {
    struct Point p;
    p = (struct Point){
        .x = a,
        .y = b
    };
    use(&p);
}

int main(void) {
    test_pt(5, 10);
    return 0;
}
