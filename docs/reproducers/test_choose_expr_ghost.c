#include <stdio.h>

// Candidate: __builtin_choose_expr unchosen alternative ghost coverage
// and phantom branch counter generation in llvm-cov.
//
// In GNU C, __builtin_choose_expr(const_exp, exp1, exp2) evaluates only
// the chosen expression; the unchosen expression is discarded at compile time.
//
// Defect: CoverageMappingGen.cpp has no VisitChooseExpr, so it visits both
// expressions, reporting ghost execution and synthesizing phantom branch counters.
int test_choose(int x) {
    int res = __builtin_choose_expr(
        1,
        x + 10,
        (
            printf("Unchosen ghost printf!\n"),
            x > 0 ? x * 100 : x * 200
        )
    );
    return res;
}

int main(void) {
    test_choose(5);
    return 0;
}
