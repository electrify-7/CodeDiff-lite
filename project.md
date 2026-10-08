# Final Course Project Proposal

**Project status:** Proposal and planning only. Required written project approval has not yet been recorded. Begin implementation only after receiving that approval.

## Title

**CovDiff-Lite: Oracle-Guided Differential Testing of C Code-Coverage Tools**

## The problem

Developers trust coverage tools such as `gcov` and `llvm-cov` to decide whether their tests adequately exercise a program. However, these tools can disagree or produce incorrect reports.

Merely finding a disagreement is insufficient because some differences are caused by legitimate reporting conventions. We therefore need a controlled oracle—a known description of what should execute—to determine whether a result is expected or suspicious.

## Our goal

Build an automated system that:

> Generates deterministic C programs with known expected coverage, executes them using GCC/`gcov` and Clang/`llvm-cov`, compares their reports against the expected result, and produces understandable, reproducible examples of suspicious coverage behaviour.

In short, we are **testing the tools that measure testing**.

## Research question

> How reliably do `gcov` and `llvm-cov` report line and branch coverage for common C control-flow constructs, and can a template-derived oracle distinguish probable reporting errors from harmless convention differences?

## What we will build

### 1. Reproducible environment

Create an Ubuntu Docker image with pinned versions of:

- GCC and `gcov`
- Clang and `llvm-cov`
- Python for automation

### 2. C program generator

Generate small deterministic programs containing:

- `if`/`else`
- loops
- `switch` statements
- short-circuit Boolean expressions
- multiline conditions
- ternary expressions
- macros
- constant conditions

Each template will also produce a manifest specifying which lines and branch outcomes are expected to execute.

### 3. Coverage runners

For every generated program:

1. Compile and execute it with GCC coverage instrumentation.
2. Collect the `gcov` JSON report.
3. Compile and execute it with Clang coverage instrumentation.
4. Collect the `llvm-cov` JSON report.
5. Verify that both compiled programs produce the same functional output.

### 4. Common coverage representation

Convert both reports into a normalized format such as:

```json
{
  "lines": {
    "8": {"expected": 1, "gcov": 1, "llvm-cov": 1},
    "9": {"expected": 0, "gcov": 0, "llvm-cov": 1}
  },
  "branches": []
}
```

### 5. Discrepancy analyser

Classify each result as:

- complete agreement;
- known reporting-convention difference;
- unstable or non-reproducible result;
- probable incorrect coverage report;
- unresolved disagreement requiring manual inspection.

Every suspicious case will be rerun to confirm that it is stable.

### 6. Visual report

Create a dashboard or static HTML report showing:

- the generated C source;
- expected coverage;
- `gcov` coverage;
- `llvm-cov` coverage;
- highlighted mismatching lines and branches;
- compiler and tool versions;
- commands needed to reproduce the result.

### 7. Test-case reduction

If time permits, automatically simplify a suspicious program while preserving its discrepancy. The result should be a small reproducer suitable for reporting to GCC or LLVM maintainers.

## Evaluation

Run the framework on approximately **200–500 deterministic C programs**.

Measure:

- number of programs generated;
- compilation and execution success rate;
- number of comparable lines and branches;
- number of raw disagreements;
- number explained by known conventions;
- number of stable unexplained disagreements;
- number of documented issues successfully reproduced;
- average analysis time per program;
- reduction in reproducer size, if reduction is implemented.

We will also include at least **two documented coverage-tool problem patterns** to demonstrate that the framework can identify known incorrect behaviour.

## Expected outcome

At the end, we should have:

- a reproducible Docker environment;
- a deterministic C-program generator;
- an expected-coverage oracle;
- automated `gcov` and `llvm-cov` runners;
- JSON parsers and a normalized coverage model;
- a discrepancy classifier;
- a dataset of 200–500 experimental cases;
- reproduction of at least two documented discrepancies;
- a visual comparison dashboard;
- a final empirical analysis of when and why the tools disagree;
- minimized reproducers for important cases, where possible.

Finding a previously unknown GCC or LLVM bug would be an excellent bonus, but it is **not required for project success**.

## Scope boundaries

To keep the project achievable, the core version will not include:

- MC/DC coverage;
- C++;
- large Debian packages;
- multithreaded or nondeterministic programs;
- optimized builds beyond `-O0`;
- more than two coverage tools;
- automatic submission of upstream bug reports.

Branch coverage and automatic reduction can be reduced to stretch goals if time becomes tight. The essential project is deterministic generation, line coverage comparison, oracle checking, and visual reporting.

## Three-week execution plan

### Week 1 — Coverage pipeline

- Build the Docker environment.
- Create several handwritten C fixtures.
- Run both coverage tools.
- Parse their JSON reports.
- Define the normalized coverage format.
- Reproduce one documented discrepancy.

### Week 2 — Automated testing

- Implement the template-based C generator.
- Generate expected-coverage manifests.
- Build the comparison and classification engine.
- Add repeatability checks.
- Add automated tests for the framework.

### Week 3 — Evaluation and showcase

- Run the 200–500-program experiment.
- Inspect unexplained disagreements.
- Add reduction if time permits.
- Build the visual report.
- Produce result tables and graphs.
- Prepare the final demonstration and report.

## Definition of done

The project is complete when one command can:

```text
Generate programs
    → run gcov and llvm-cov
    → normalize their reports
    → compare them with expected coverage
    → classify discrepancies
    → generate a visual results page
```

The final demonstration should show one normal case and one discrepancy case from generation through the final highlighted report.

Begin implementation only after receiving the required written project approval.
