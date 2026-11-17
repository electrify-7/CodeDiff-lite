int test_dispatch(int op) {
    static void *targets[] = { &&op_exit, &&op_unreached };
    goto *targets[op];

op_unreached:
    return 1;
op_exit:
    return 0;
}

int main(void) {
    return test_dispatch(0);
}
