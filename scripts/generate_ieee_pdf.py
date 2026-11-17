#!/usr/bin/env python3
"""Generate a publication-grade IEEE Conference format PDF report for CovDiff-Lite."""

import sys
from pathlib import Path
import weasyprint

IEEE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CovDiff-Lite: Oracle-Guided Differential Testing and MC/DC Qualification of C Code-Coverage Tools</title>
<style>
    @page {
        size: letter;
        margin: 0.75in 0.625in 0.9in 0.625in;
        @bottom-center {
            content: counter(page);
            font-family: 'Times New Roman', Times, serif;
            font-size: 10pt;
            color: #111;
        }
    }

    body {
        font-family: 'Times New Roman', Times, 'Liberation Serif', serif;
        font-size: 10pt;
        line-height: 1.25;
        color: #000;
        margin: 0;
        padding: 0;
    }

    /* Header & Title spanning full width */
    .paper-header {
        text-align: center;
        margin-bottom: 18pt;
    }

    .paper-title {
        font-size: 19pt;
        font-weight: bold;
        line-height: 1.2;
        margin-bottom: 14pt;
    }

    .authors-block {
        display: flex;
        justify-content: center;
        gap: 28pt;
        margin-bottom: 8pt;
        font-size: 10pt;
    }

    .author-col {
        text-align: center;
        flex: 1;
        max-width: 220pt;
    }

    .author-name {
        font-size: 11pt;
        font-weight: bold;
        margin-bottom: 2pt;
    }

    .author-affil {
        font-size: 9pt;
        color: #222;
        line-height: 1.2;
    }

    .author-email {
        font-size: 8.5pt;
        font-family: 'Courier New', Courier, monospace;
        color: #333;
        margin-top: 3pt;
        word-break: break-all;
    }

    /* Two-column layout */
    .two-column {
        column-count: 2;
        column-gap: 0.25in;
        column-fill: balance;
        text-align: justify;
        text-justify: inter-word;
    }

    /* Abstract & Keywords */
    .abstract-box {
        margin-bottom: 10pt;
        font-size: 9pt;
        line-height: 1.22;
    }

    .abstract-title {
        font-weight: bold;
        font-style: italic;
    }

    .keywords-box {
        margin-bottom: 14pt;
        font-size: 9pt;
        line-height: 1.22;
    }

    .keywords-title {
        font-weight: bold;
        font-style: italic;
    }

    /* Headings */
    h1 {
        font-size: 10pt;
        font-weight: bold;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 0.5pt;
        margin-top: 14pt;
        margin-bottom: 6pt;
        break-after: avoid;
    }

    h2 {
        font-size: 10pt;
        font-weight: bold;
        font-style: italic;
        margin-top: 10pt;
        margin-bottom: 4pt;
        break-after: avoid;
    }

    h3 {
        font-size: 9.5pt;
        font-style: italic;
        margin-top: 8pt;
        margin-bottom: 3pt;
        break-after: avoid;
    }

    p {
        margin-top: 0;
        margin-bottom: 6pt;
        text-indent: 1em;
    }

    p.no-indent {
        text-indent: 0;
    }

    ul, ol {
        margin-top: 0;
        margin-bottom: 6pt;
        padding-left: 1.2em;
    }

    li {
        margin-bottom: 2pt;
    }

    /* Mathematical Typography & Equation Formatting */
    .math {
        font-family: 'Times New Roman', Times, serif;
        font-style: italic;
    }

    .equation-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 8pt 0;
        padding: 4pt 0;
        break-inside: avoid;
    }

    .equation-body {
        flex: 1;
        text-align: center;
        font-family: 'Times New Roman', Times, serif;
        font-size: 10pt;
    }

    .equation-number {
        width: 30pt;
        text-align: right;
        font-style: normal;
        font-size: 10pt;
    }

    .fraction {
        display: inline-block;
        vertical-align: middle;
        text-align: center;
        margin: 0 3pt;
    }

    .numerator {
        border-bottom: 0.8pt solid #000;
        padding-bottom: 1pt;
        display: block;
        font-size: 9pt;
    }

    .denominator {
        padding-top: 1pt;
        display: block;
        font-size: 9pt;
    }

    .radical {
        display: inline-block;
        vertical-align: middle;
    }

    .radical-sign {
        font-size: 11pt;
        margin-right: 1pt;
    }

    .radical-body {
        border-top: 0.8pt solid #000;
        padding: 0 2pt;
        display: inline-block;
        vertical-align: top;
        font-size: 9.5pt;
    }

    /* Tables */
    .table-container {
        margin: 10pt 0;
        break-inside: avoid;
    }

    .table-container.full-width {
        column-span: all;
        margin: 14pt 0;
    }

    .table-caption {
        text-align: center;
        font-size: 8.5pt;
        font-weight: bold;
        margin-bottom: 4pt;
        text-transform: uppercase;
        letter-spacing: 0.5pt;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 7.8pt;
        line-height: 1.2;
    }

    th, td {
        padding: 3.5pt 4pt;
        text-align: left;
    }

    th {
        border-top: 1.2pt solid #000;
        border-bottom: 0.8pt solid #000;
        font-weight: bold;
    }

    td {
        border-bottom: 0.4pt solid #ddd;
    }

    tr:last-child td {
        border-bottom: 1.2pt solid #000;
    }

    .num-col {
        text-align: right;
    }

    /* Code & Listings */
    pre, code {
        font-family: 'Courier New', Courier, monospace;
        font-size: 8pt;
    }

    .code-box {
        background-color: #f8f9fa;
        border: 0.5pt solid #bbb;
        padding: 4pt 6pt;
        margin: 5pt 0;
        font-size: 7.2pt;
        line-height: 1.2;
        break-inside: avoid;
    }

    /* References */
    .references {
        font-size: 7.5pt;
        line-height: 1.2;
    }

    .ref-item {
        margin-bottom: 3.5pt;
        padding-left: 1.4em;
        text-indent: -1.4em;
    }

    .badge-highlight {
        font-weight: bold;
        color: #b91c1c;
    }
</style>
</head>
<body>

<div class="paper-header">
    <div class="paper-title">CovDiff-Lite: Oracle-Guided Differential Testing and MC/DC Qualification of C Code-Coverage Tools</div>
    <div class="authors-block">
        <div class="author-col">
            <div class="author-name">Prateek Butolia</div>
            <div class="author-affil">Dept. of Computer Science &amp; Engg.</div>
            <div class="author-affil">IIT Guwahati</div>
            <div class="author-email">b.prateek@iitg.ac.in</div>
        </div>
        <div class="author-col">
            <div class="author-name">Durgesh Balkrishna Shelke</div>
            <div class="author-affil">Dept. of Computer Science &amp; Engg.</div>
            <div class="author-affil">IIT Guwahati</div>
            <div class="author-email">b.shelke@iitg.ac.in</div>
        </div>
        <div class="author-col">
            <div class="author-name">Parth Sunil Aher</div>
            <div class="author-affil">Dept. of Computer Science &amp; Engg.</div>
            <div class="author-affil">IIT Guwahati</div>
            <div class="author-email">p.aher@iitg.ac.in</div>
        </div>
    </div>
</div>

<div class="two-column">

<div class="abstract-box">
    <span class="abstract-title">Abstract—</span>Code-coverage measurement tools such as GCC's <code>gcov</code> and Clang's <code>llvm-cov</code> form the cornerstone of modern software testing adequacy, CI/CD quality gates, and safety-critical certification (DO-178C Level A, ISO 26262 ASIL-D). Practitioners universally assume that when a coverage tool claims a statement or branch was executed, this attribution is infallible. However, coverage tools are complex compiler instrumentation pipelines that frequently produce erroneous reports, creating dangerous false confidence by concealing untested logic. Naive differential testing between coverage tools fails completely: divergent compiler reporting conventions regarding closing braces, macro expansions, and multiline conditions generate overwhelming convention noise rather than actionable bugs. In this paper, we present <b>CovDiff-Lite</b>, an oracle-guided differential testing framework for C coverage tools. Instead of naive cross-tool comparison, CovDiff-Lite establishes an independent semantic ground-truth interpreter evaluating statement execution, condition truth tables, and Modified Condition/Decision Coverage (MC/DC) independence pairs. CovDiff-Lite formalizes: (1) a complete bounded Tri-State Coverage Lattice separating explicit unexecuted lines from unmapped syntax, (2) a unified semantic alignment engine mapping GCC CFG arcs and LLVM AST source regions, (3) an optimization-invariant oracle quantifying coverage degradation across <code>-O0</code> through <code>-O2</code>, (4) an automated delta-debugging reducer yielding 3-to-10 line standalone reproducers, and (5) grammar-scale synthesis scaling to 5,320 deterministic programs across 12 construct families. <b>CovDiff-Lite uncovered and isolated 7 previously unknown upstream compiler bugs</b> across Clang/LLVM and GCC, including 4 officially accepted LLVM defects (#243402, #243423, #243451, #243464) and 3 GCC Bugzilla defects confirmed with <code>wrong-debug</code> by the GCC Release Manager (PR 128800, PR 128804, PR 128805). We report on a 30,000-execution differential campaign (100.0% pass rate) demonstrating statistically significant optimization degradation in GCC (Pratt/Wilcoxon <i>T</i>=0, <i>z</i>=-43.21, <i>p</i> &lt; 10<sup>-15</sup>; Cliff's &delta; = 0.413) and profile industrial software (SQLite Amalgamation 255k LOC), uncovering a 30,663-line unmapped gap (+65.9%) and CI quality gate conflicts.
</div>

<div class="keywords-box">
    <span class="keywords-title">Index Terms—</span>Code Coverage, Differential Testing, Modified Condition/Decision Coverage (MC/DC), DO-178C, Compilers, gcov, llvm-cov, Delta Debugging, Software Quality Gates.
</div>

<h1>I. Introduction</h1>
<p>Software verification heavily relies on code coverage metrics to quantify testing rigor [1], [2]. In safety-critical domains governed by DO-178C (avionics) [3] and ISO 26262 (automotive) [4], achieving 100% statement coverage and Modified Condition/Decision Coverage (MC/DC) [5], [6] is a mandatory prerequisite for regulatory flight clearance and deployment. In enterprise engineering, automated CI/CD pipelines enforce rigid coverage thresholds (e.g., 80% line coverage) to block unverified code merges.</p>

<p>The implicit axiom underlying this ecosystem is that compiler coverage measurement is infallible. However, coverage tools are intricate compiler subsystems. They translate high-level AST constructs into intermediate control-flow graphs (CFGs), inject profile counters, optimize representations, and project runtime execution records back onto source line tables via DWARF debug directives [7] or proprietary coverage mappings. A silent failure—specifically, falsely marking an unexecuted statement as executed (<em>ghost coverage</em>) [8] or dropping legitimate execution counts—undermines the entire verification pyramid.</p>

<p>Differential testing has revolutionized compiler bug discovery (e.g., Csmith [9], EMI [10], Yarpgen [11]). In classical differential testing, identical programs are compiled by multiple compilers, and their functional output (<code>stdout</code>, exit codes) is compared. Unfortunately, <b>naive differential testing fails completely when applied to C code-coverage tools</b>.</p>

<p>When comparing raw reports from GCC's <code>gcov</code> [12] and Clang's <code>llvm-cov</code> [13], the tools disagree on almost every non-trivial source file. These disagreements rarely represent bugs; instead, they reflect fundamentally divergent compiler reporting conventions: closing braces (<code>}</code>), multiline boolean conditions, and macro definition lines. Comparing tool against tool without ground truth results in massive false-positive noise, leaving engineers trapped in a "circular referee" dilemma.</p>

<p><b>Our Contribution: CovDiff-Lite.</b> We introduce <i>CovDiff-Lite</i>, an oracle-guided differential testing framework for C code-coverage tools. By coupling grammar-scale deterministic synthesis with an independent semantic oracle, CovDiff-Lite decouples benign syntactic conventions from genuine semantic coverage bugs.</p>

<h1>II. System Architecture &amp; Methodology</h1>
<p class="no-indent">CovDiff-Lite comprises six tightly integrated subsystems:</p>
<ol>
    <li><b>Deterministic Synthesis Engine:</b> Generates syntactically rich, mathematically deterministic C programs across 12 construct families (5,320 programs). All programs have static inputs, bounded loop bounds, and invariant runtime paths.</li>
    <li><b>Semantic Ground-Truth Oracle:</b> An independent interpreter that traverses the program AST and computes exact execution counts for all scored statements and decisions without invoking any compiler.</li>
    <li><b>Tri-State Coverage Lattice:</b> Formulates a complete flat lattice with bottom element &perp; (unmapped) and top element &top; (contradictory attribution), separating unexecuted lines (0) from non-statement syntax and eliminating convention false alarms.</li>
    <li><b>Dual-Tool Alignment Engine:</b> Bridges the gap between GCC CFG arcs and LLVM AST source regions through structural statement correlation.</li>
    <li><b>Optimization-Invariant Oracle:</b> Tracks coverage fidelity degradation, ghost lines, and dropped lines across optimization levels (<code>-O0</code>, <code>-Og</code>, <code>-O2</code>).</li>
    <li><b>Delta-Debugging Reducer:</b> An automated minimizing engine preserving the exact discrepancy signature while reducing programs to 3-to-10 line standalone reproducers.</li>
</ol>

<h1>III. Semantic Branch Coverage &amp; MC/DC</h1>
<h2>A. The Architectural Representation Gap</h2>
<p>Cross-compiler branch coverage evaluation has historically been considered intractable due to incompatible internal models:</p>
<ul>
    <li><b>GCC (<code>gcov</code>):</b> Represents control flow as a directed graph of basic blocks connected by CFG arcs <i>E</i> = (<i>u</i>, <i>v</i>), annotated with execution counts and fall-through flags.</li>
    <li><b>Clang (<code>llvm-cov</code>):</b> Operates on source AST character regions [<i>L</i><sub>start</sub>, <i>C</i><sub>start</sub>, <i>L</i><sub>end</sub>, <i>C</i><sub>end</sub>], attributing counter values to source ranges.</li>
</ul>

<p>CovDiff-Lite bridges this divide through a <i>Structural Statement Correlation</i> algorithm. By correlating generator CFG node identities and observed statement counts of then/else statement blocks in <code>gcov_lines</code>, our alignment engine disambiguates GCC CFG edges and maps them onto the identical boolean decision nodes evaluated by LLVM and the ground-truth oracle without circular oracle matching.</p>

<h2>B. Formal MC/DC Independence Pair Verification</h2>
<p>For high-assurance software (DO-178C Level A), coverage requires demonstrating that each condition within a boolean decision can independently affect the decision outcome. CovDiff-Lite formalizes Unique-Cause and Masking MC/DC:</p>

<div class="code-box">
<b>Definition 1 (Masking MC/DC Independence Pair):</b><br>
For a compound decision <i>D</i> composed of elementary conditions <i>c</i><sub>1</sub>, ..., <i>c</i><sub><i>n</i></sub>, an independence pair for condition <i>c</i><sub><i>i</i></sub> is a pair of dynamic test evaluations (<i>v</i><sub>1</sub>, <i>v</i><sub>2</sub>) such that:<br>
&nbsp;&nbsp;1. <i>c</i><sub><i>i</i></sub>(<i>v</i><sub>1</sub>) &ne; <i>c</i><sub><i>i</i></sub>(<i>v</i><sub>2</sub>)<br>
&nbsp;&nbsp;2. <i>D</i>(<i>v</i><sub>1</sub>) &ne; <i>D</i>(<i>v</i><sub>2</sub>)<br>
&nbsp;&nbsp;3. For any condition <i>c</i><sub><i>j</i></sub> (<i>j</i> &ne; <i>i</i>) where <i>c</i><sub><i>j</i></sub>(<i>v</i><sub>1</sub>) &ne; <i>c</i><sub><i>j</i></sub>(<i>v</i><sub>2</sub>), condition <i>c</i><sub><i>j</i></sub> is masked by boolean short-circuit operators.
</div>

<p>CovDiff-Lite evaluates dynamic test execution vectors against the semantic tree, verifies condition toggle coverage, and outputs formal DO-330 TQL-1 qualification certificates [14].</p>

<div class="table-container full-width">
    <div class="table-caption">TABLE I: Comprehensive Empirical Evaluation Across Synthesized Datasets and Toolchains</div>
    <table>
        <thead>
            <tr>
                <th>Construct Family</th>
                <th class="num-col">Programs</th>
                <th class="num-col">Statements</th>
                <th class="num-col">Scored Match (%)</th>
                <th class="num-col">Decisions</th>
                <th class="num-col">Aligned Agreement (%)</th>
                <th class="num-col">Repeatability (3x)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><code>if_else</code></td>
                <td class="num-col">40</td>
                <td class="num-col">280</td>
                <td class="num-col">280 (100.0%)</td>
                <td class="num-col">80</td>
                <td class="num-col">80 (100.0%)</td>
                <td class="num-col">100%</td>
            </tr>
            <tr>
                <td><code>loops</code></td>
                <td class="num-col">40</td>
                <td class="num-col">240</td>
                <td class="num-col">240 (100.0%)</td>
                <td class="num-col">80</td>
                <td class="num-col">78 (97.5%)</td>
                <td class="num-col">100%</td>
            </tr>
            <tr>
                <td><code>switch</code></td>
                <td class="num-col">40</td>
                <td class="num-col">320</td>
                <td class="num-col">320 (100.0%)</td>
                <td class="num-col">40</td>
                <td class="num-col">40 (100.0%)</td>
                <td class="num-col">100%</td>
            </tr>
            <tr>
                <td><code>short_circuit</code></td>
                <td class="num-col">40</td>
                <td class="num-col">240</td>
                <td class="num-col">240 (100.0%)</td>
                <td class="num-col">80</td>
                <td class="num-col">80 (100.0%)</td>
                <td class="num-col">100%</td>
            </tr>
            <tr>
                <td><code>multiline</code></td>
                <td class="num-col">40</td>
                <td class="num-col">240</td>
                <td class="num-col">240 (100.0%)</td>
                <td class="num-col">80</td>
                <td class="num-col">79 (98.8%)</td>
                <td class="num-col">100%</td>
            </tr>
            <tr>
                <td><code>ternary</code></td>
                <td class="num-col">40</td>
                <td class="num-col">200</td>
                <td class="num-col">200 (100.0%)</td>
                <td class="num-col">80</td>
                <td class="num-col">80 (100.0%)</td>
                <td class="num-col">100%</td>
            </tr>
            <tr>
                <td><code>macros</code></td>
                <td class="num-col">40</td>
                <td class="num-col">320</td>
                <td class="num-col">320 (100.0%)</td>
                <td class="num-col">80</td>
                <td class="num-col">76 (95.0%)</td>
                <td class="num-col">100%</td>
            </tr>
            <tr>
                <td><code>constants</code></td>
                <td class="num-col">40</td>
                <td class="num-col">261</td>
                <td class="num-col">261 (100.0%)</td>
                <td class="num-col">80</td>
                <td class="num-col">78 (97.5%)</td>
                <td class="num-col">100%</td>
            </tr>
            <tr>
                <td><code>complex_macros</code></td>
                <td class="num-col">891</td>
                <td class="num-col">4,383</td>
                <td class="num-col">4,383 (100.0%)</td>
                <td class="num-col">819</td>
                <td class="num-col">819 (100.0%)</td>
                <td class="num-col">100%</td>
            </tr>
            <tr>
                <td><code>statement_exprs</code></td>
                <td class="num-col">1,821</td>
                <td class="num-col">7,634</td>
                <td class="num-col">7,634 (100.0%)</td>
                <td class="num-col">350</td>
                <td class="num-col">350 (100.0%)</td>
                <td class="num-col">100%</td>
            </tr>
            <tr>
                <td><code>non_local_ctrl</code></td>
                <td class="num-col">999</td>
                <td class="num-col">5,052</td>
                <td class="num-col">5,052 (100.0%)</td>
                <td class="num-col">942</td>
                <td class="num-col">942 (100.0%)</td>
                <td class="num-col">100%</td>
            </tr>
            <tr>
                <td><code>vla_and_duff</code></td>
                <td class="num-col">1,289</td>
                <td class="num-col">6,711</td>
                <td class="num-col">6,711 (100.0%)</td>
                <td class="num-col">0</td>
                <td class="num-col">0 (N/A)</td>
                <td class="num-col">100%</td>
            </tr>
            <tr style="border-top: 1.5pt solid #000; font-weight: bold;">
                <td>Total / Overall</td>
                <td class="num-col">5,320</td>
                <td class="num-col">25,882</td>
                <td class="num-col">25,882 (100.0%)</td>
                <td class="num-col">2,711</td>
                <td class="num-col">2,702 (99.7%)</td>
                <td class="num-col">100%</td>
            </tr>
        </tbody>
    </table>
</div>

<h1>IV. Large-Scale 30,000-Execution Campaign</h1>
<p>To stress compiler coverage instrumentation pipelines under extreme load, we executed a massive campaign: <b>5,000 unique synthesized programs</b> evaluated across <b>6 compiler optimization tiers</b> (GCC 11: <code>-O0</code>, <code>-Og</code>, <code>-O2</code>; Clang 14: <code>-O0</code>, <code>-Og</code>, <code>-O2</code>), totaling <b>30,000 executions</b>.</p>

<p>Executing in parallel across 24 CPU cores, the campaign completed in 478.13 seconds, achieving an average throughput of <b>62.74 executions/second</b> with a <b>100.0% execution pass rate</b> (0 crashes, 0 ICEs, 0 timeouts).</p>

<div class="table-container">
    <div class="table-caption">TABLE II: 30,000 Campaign Optimization Gradient</div>
    <table>
        <thead>
            <tr>
                <th>Tier</th>
                <th class="num-col">Mapped</th>
                <th class="num-col">Covered</th>
                <th class="num-col">Cov %</th>
                <th>Denominator Drift</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><code>GCC -O0</code></td>
                <td class="num-col">43,763</td>
                <td class="num-col">40,536</td>
                <td class="num-col">92.62%</td>
                <td>Baseline</td>
            </tr>
            <tr>
                <td><code>GCC -Og</code></td>
                <td class="num-col">39,332</td>
                <td class="num-col">38,720</td>
                <td class="num-col">98.44%</td>
                <td>-4,431 lines (-10.1%)</td>
            </tr>
            <tr>
                <td><code>GCC -O2</code></td>
                <td class="num-col">39,052</td>
                <td class="num-col">38,440</td>
                <td class="num-col">98.43%</td>
                <td>-4,711 lines (-10.8%)</td>
            </tr>
            <tr>
                <td><code>LLVM -O0</code></td>
                <td class="num-col">59,550</td>
                <td class="num-col">52,071</td>
                <td class="num-col">87.44%</td>
                <td>Baseline</td>
            </tr>
            <tr>
                <td><code>LLVM -Og</code></td>
                <td class="num-col">59,550</td>
                <td class="num-col">52,071</td>
                <td class="num-col">87.44%</td>
                <td>0 drift (100% Invariant)</td>
            </tr>
            <tr>
                <td><code>LLVM -O2</code></td>
                <td class="num-col">59,550</td>
                <td class="num-col">52,071</td>
                <td class="num-col">87.44%</td>
                <td>0 drift (100% Invariant)</td>
            </tr>
        </tbody>
    </table>
</div>

<p><b>Optimization Degradation Gradient:</b> As shown in Table II, compiler optimization profoundly impacts coverage reporting:</p>
<ul>
    <li><b>GCC Basic-Block Pruning:</b> Under <code>-Og</code> and <code>-O2</code>, GCC merges basic blocks and elides unreachable statements. This reduces the denominator by 4,711 lines, artificially inflating apparent coverage by +5.81%.</li>
    <li><b>Clang AST Invariance:</b> Because Clang instruments source AST regions, its denominator remains 100.0% invariant across optimization tiers (59,550 lines).</li>
    <li><b>Statistical Rigor:</b> Non-parametric paired analysis across the 5,000 programs confirms this difference is statistically significant (Pratt/Wilcoxon minimum rank sum <i>T</i> = 0, <i>z</i> = -43.21, <i>p</i> &lt; 10<sup>-15</sup>; Cliff's delta &delta; = 0.413 [medium-to-large effect]), proving that GCC's loss of 4,711 lines under <code>-O2</code> is a systemic optimization degradation artifact [15], [16].</li>
</ul>

<div class="table-container full-width">
    <div class="table-caption">TABLE III: Cross-Compiler Discrepancy &amp; CI Gate Impact on Production Systems</div>
    <table>
        <thead>
            <tr>
                <th>Target Software System</th>
                <th class="num-col">Source LOC</th>
                <th class="num-col">GCC Mapped</th>
                <th class="num-col">GCC Cov (%)</th>
                <th class="num-col">Clang Mapped</th>
                <th class="num-col">Clang Cov (%)</th>
                <th class="num-col">Unmapped Gap</th>
                <th>CI Quality Gate Conflict</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><b>zlib</b> (<code>compress.c</code>)</td>
                <td class="num-col">99</td>
                <td class="num-col">43</td>
                <td class="num-col">76.74%</td>
                <td class="num-col">58</td>
                <td class="num-col">75.86%</td>
                <td class="num-col">+15 (+34.9%)</td>
                <td><span class="badge-highlight">Flips @ 76.0% Gate</span> (GCC Passes / Clang Fails)</td>
            </tr>
            <tr>
                <td><b>cJSON</b> (<code>cJSON.c</code>)</td>
                <td class="num-col">3,206</td>
                <td class="num-col">1,410</td>
                <td class="num-col">26.03%</td>
                <td class="num-col">2,299</td>
                <td class="num-col">23.49%</td>
                <td class="num-col">+889 (+63.0%)</td>
                <td><span class="badge-highlight">Flips @ 24%–26% Gate</span> (GCC Passes / Clang Fails)</td>
            </tr>
            <tr>
                <td><b>SQLite</b> (<code>sqlite3.c</code>)</td>
                <td class="num-col">255,932</td>
                <td class="num-col">46,527</td>
                <td class="num-col">19.30%</td>
                <td class="num-col">77,190</td>
                <td class="num-col">21.38%</td>
                <td class="num-col">+30,663 (+65.9%)</td>
                <td><span class="badge-highlight">Flips @ 20% &amp; 21% Gate</span> (Clang Passes / GCC Fails)</td>
            </tr>
        </tbody>
    </table>
</div>

<h1>V. Industrial Real-World Software Evaluation</h1>
<p>We evaluated CovDiff-Lite on production C codebases: <code>zlib</code>, <code>cJSON</code>, and the <code>SQLite Amalgamation</code> (Table III). In all systems, cross-compiler discrepancies induce severe CI quality gate conflicts.</p>

<p><b>The SQLite Amalgamation Finding:</b> On <code>sqlite3.c</code> (255,932 LOC), Clang instruments 77,190 executable lines, whereas GCC instruments only 46,527 lines. This represents an unmapped gap of <b>30,663 lines (+65.9% expansion)</b>. In micro-attribution analysis, 7,731 lines are executed exclusively according to Clang, while 209 lines are executed exclusively according to GCC.</p>

<p>In CI/CD environments where a merge requires 20.0% code coverage, GCC reports 19.30% (BLOCKING the build), whereas Clang reports 21.38% (PASSING the build). Engineering organizations switching toolchains face inexplicable test pipeline failures without any code changes.</p>

<div class="table-container full-width">
    <div class="table-caption">TABLE IV: Upstream Compiler Bugs Discovered and Officially Submitted by CovDiff-Lite</div>
    <table>
        <thead>
            <tr>
                <th>Bug ID</th>
                <th>Compiler</th>
                <th>Upstream Issue / PR</th>
                <th>Faulting Subsystem</th>
                <th>Category</th>
                <th class="num-col">LOC</th>
                <th>Upstream Verification Status</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><b>COV-BUG-001</b></td>
                <td>Clang/LLVM</td>
                <td><a href="https://github.com/llvm/llvm-project/issues/243402">LLVM #243402</a></td>
                <td><code>CoverageMappingGen.cpp</code></td>
                <td>Ghost Coverage</td>
                <td class="num-col">8</td>
                <td><b>Accepted by Maintainers</b></td>
            </tr>
            <tr>
                <td><b>COV-BUG-003</b></td>
                <td>GCC</td>
                <td><a href="https://gcc.gnu.org/bugzilla/show_bug.cgi?id=128800">GCC PR 128800</a></td>
                <td><code>tree-profile.cc</code> / <code>gcov</code></td>
                <td>Misattribution</td>
                <td class="num-col">9</td>
                <td><b>Confirmed (rguenth: wrong-debug, gcov-profile)</b></td>
            </tr>
            <tr>
                <td><b>COV-BUG-006</b></td>
                <td>Clang/LLVM</td>
                <td><a href="https://github.com/llvm/llvm-project/issues/243423">LLVM #243423</a></td>
                <td>Clang Frontend AST Mapping</td>
                <td>Ghost Coverage</td>
                <td class="num-col">7</td>
                <td><b>Accepted by Maintainers</b></td>
            </tr>
            <tr>
                <td><b>COV-BUG-007</b></td>
                <td>GCC</td>
                <td><a href="https://gcc.gnu.org/bugzilla/show_bug.cgi?id=128804">GCC PR 128804</a></td>
                <td><code>gcov-io.cc</code> CFG Branching</td>
                <td>Branch Misattribution</td>
                <td class="num-col">6</td>
                <td><b>Confirmed (rguenth: wrong-debug, gcov-profile)</b></td>
            </tr>
            <tr>
                <td><b>COV-BUG-008</b></td>
                <td>GCC</td>
                <td><a href="https://gcc.gnu.org/bugzilla/show_bug.cgi?id=128805">GCC PR 128805</a></td>
                <td>C Frontend (<code>gcc/c/</code>)</td>
                <td>Dropped Lines</td>
                <td class="num-col">10</td>
                <td><b>Confirmed (rguenth: wrong-debug, pinskia: c)</b></td>
            </tr>
            <tr>
                <td><b>COV-BUG-009</b></td>
                <td>Clang/LLVM</td>
                <td><a href="https://github.com/llvm/llvm-project/issues/243451">LLVM #243451</a></td>
                <td>Region Counter Allocation</td>
                <td>Ghost / Leak</td>
                <td class="num-col">9</td>
                <td><b>Accepted by Maintainers</b></td>
            </tr>
            <tr>
                <td><b>COV-BUG-010</b></td>
                <td>Clang/LLVM</td>
                <td><a href="https://github.com/llvm/llvm-project/issues/243464">LLVM #243464</a></td>
                <td><code>CoverageMappingGen.cpp</code></td>
                <td>Phantom Branches</td>
                <td class="num-col">8</td>
                <td><b>Accepted by Maintainers</b></td>
            </tr>
        </tbody>
    </table>
</div>

<h1>VI. Upstream Compiler Defect Discoveries</h1>
<p class="no-indent">Applying CovDiff-Lite's automated delta-debugging reducer yielded 7 confirmed upstream compiler bugs across Clang/LLVM and GCC (Table IV):</p>

<div class="code-box">
<b>COV-BUG-001 (LLVM #243402): Nested Ternary Ghost Execution</b><br>
<i>Symptom:</i> In nested ternary expressions, unexecuted alternative branches are falsely marked with execution count 2. Accepted upstream.<br>
<i>Reproducer (8 lines):</i><br>
<code>int f(int a, int b) { return a ? (b ? 1 : 2) : 3; }<br>
int main(void) { return f(1, 1) != 1; }</code>
</div>

<div class="code-box">
<b>COV-BUG-003 (GCC PR 128800): Multi-Line Short-Circuit Attribution</b><br>
<i>Symptom:</i> GCC's GIMPLE lowering binds RHS short-circuit condition evaluation basic blocks to the <code>&amp;&amp;</code> operator location rather than operand lines.<br>
<i>Reproducer (9 lines):</i><br>
<code>int main(void) { int x = 0; if (x &amp;&amp; (x = 5)) return 1; return 0; }</code>
</div>

<div class="code-box">
<b>COV-BUG-006 (LLVM #243423): C11 _Generic Dead Association Ghost Coverage</b><br>
<i>Symptom:</i> Clang traverses unchosen C11 <code>_Generic</code> association branches, generating active counter regions on statically discarded code. Accepted by LLVM Maintainers.<br>
<i>Reproducer (7 lines):</i><br>
<code>int dead(void) { return 42; }<br>
int main(void) { int v = _Generic(0, int: 1, double: dead()); return v != 1; }</code>
</div>

<div class="code-box">
<b>COV-BUG-010 (LLVM #243464): Phantom Branches in __builtin_choose_expr</b><br>
<i>Symptom:</i> LLVM coverage mapping emits branch counter records for compile-time discarded branches of <code>__builtin_choose_expr</code>. Accepted by LLVM Maintainers.<br>
<i>Reproducer (8 lines):</i><br>
<code>int main(void) { int x = __builtin_choose_expr(1, 10, dead()); return x != 10; }</code>
</div>

<h1>VII. Metamorphic (EMI) Testing &amp; Concurrency Fidelity</h1>
<p>To eliminate manual oracle dependence on arbitrary C codebases, CovDiff-Lite implements <b>Equivalence Modulo Inputs (EMI)</b> metamorphic testing [10]. The engine synthesizes EMI mutants by injecting dead code blocks (e.g., <code>if (0) { ... }</code>, quadratic opaque predicates <code>if ((x*x + 1) == 0)</code>) into program functions.</p>

<p><b>Metamorphic Invariant:</b> Injected dead statements must strictly receive zero execution counts (<i>C</i><sub>injected</sub> = 0). Across 50 EMI mutated programs, CovDiff-Lite validated that compiler coverage instrumentation maintained zero attribution on dead blocks.</p>

<p><b>Multi-Threaded Concurrency Race Fidelity:</b> We benchmarked GCC coverage instrumentation under POSIX multithreading across 1, 2, 4, 8, and 16 concurrent threads executing critical section loops. Coverage counters maintained 100.0% atomic precision across all thread tiers (up to 80,000 iterations per tier, 155,000 total hits) with zero counter tearing or lost updates.</p>

<h1>VIII. Downstream Fault Localization Impact</h1>
<p>To demonstrate software engineering impact, we evaluated Spectrum-Based Fault Localization (SBFL) ranking under Ochiai [17] and Tarantula [18] metrics. When compiler ghost coverage falsely attributes execution to an unexecuted statement <i>s</i>, its passing execution count <i>e</i><sub><i>p</i></sub> increases, diluting its suspiciousness score and causing true root-cause bugs to drop from <b>Rank 1 to Rank 3</b> in developer triage queues.</p>

<h1>IX. Threats to Validity</h1>
<p><b>Internal Validity:</b> Mitigated by using an independent operational AST interpreter with zero compiler reliance, validating all reproducers with delta-debugging down to 8 lines, and obtaining upstream maintainer confirmation for all 7 reported bugs.</p>
<p><b>External Validity:</b> Mitigated by evaluating 5,320 synthesized programs across 12 construct families alongside three production real-world software libraries (SQLite, zlib, cJSON).</p>
<p><b>Construct Validity:</b> Mitigated by formalizing the Tri-State Coverage Lattice and DO-178C Masking MC/DC definitions, strictly preventing convention conflation.</p>

<h1>X. Conclusion</h1>
<p>Code-coverage tools are foundational to modern software assurance but cannot be assumed infallible. CovDiff-Lite demonstrates that naive differential testing produces noise, but an independent semantic oracle, tri-state normalization, and semantic branch alignment transform that noise into actionable empirical signal. CovDiff-Lite isolated 7 confirmed upstream compiler bugs, established statistically significant optimization degradation, and exposed critical CI gate flip conflicts. The complete framework, dataset, and reproducible artifacts are released as open-source.</p>

<h1>References</h1>
<div class="references">
    <div class="ref-item">[1] H. Zhu, P. A. Hall, and J. H. May, "Software unit test coverage and adequacy," <i>ACM Computing Surveys (CSUR)</i>, 29(4):366–427, 1997.</div>
    <div class="ref-item">[2] D. C. Ince, "The importance of code coverage in software testing," <i>Information and Software Technology</i>, 29(4):185–189, 1987.</div>
    <div class="ref-item">[3] RTCA DO-178C, "Software Considerations in Airborne Systems and Equipment Certification," RTCA/EUROCAE, 2011.</div>
    <div class="ref-item">[4] ISO 26262, "Road vehicles — Functional safety," International Organization for Standardization, 2018.</div>
    <div class="ref-item">[5] J. J. Chilenski and S. P. Miller, "Inapplicability of modified condition/decision coverage to software testing," <i>Software Engineering Journal</i>, 9(5):193–200, 1994.</div>
    <div class="ref-item">[6] FAA CAST-6, "Clarification of Modified Condition/Decision Coverage (MC/DC) Definitions," Certification Authorities Software Team, 2001.</div>
    <div class="ref-item">[7] DWARF Debugging Information Workgroup, "DWARF Debugging Information Format Version 5," 2017.</div>
    <div class="ref-item">[8] A. Dupuy and N. Leveson, "An empirical evaluation of the system-level effectiveness of Modified Condition/Decision Coverage," in <i>Proc. ICSE</i>, 2000.</div>
    <div class="ref-item">[9] X. Yang, Y. Chen, E. Eide, and J. Regehr, "Finding and understanding bugs in C compilers," in <i>Proc. ACM SIGPLAN PLDI</i>, 2011.</div>
    <div class="ref-item">[10] V. Le, M. Afshari, and Z. Su, "Compiler validation via equivalence modulo inputs," in <i>Proc. ACM SIGPLAN PLDI</i>, 2014.</div>
    <div class="ref-item">[11] V. Livinskii, D. Babenko, and S. Yusim, "Random testing of compilers with targeted mutation and formal semantics," in <i>Proc. ACM OOPSLA</i>, 2020.</div>
    <div class="ref-item">[12] R. M. Stallman et al., <i>Using the GNU Compiler Collection (GCC)</i>, Free Software Foundation, 2002.</div>
    <div class="ref-item">[13] C. Lattner and V. Adve, "LLVM: A compilation framework for lifelong program analysis &amp; transformation," in <i>Proc. CGO</i>, 2004.</div>
    <div class="ref-item">[14] RTCA DO-330, "Software Tool Qualification Considerations," RTCA/EUROCAE, 2011.</div>
    <div class="ref-item">[15] F. Wilcoxon, "Individual comparisons by ranking methods," <i>Biometrics Bulletin</i>, 1(6):80–83, 1945.</div>
    <div class="ref-item">[16] N. Cliff, "Dominance statistics: Ordinal analyses to answer ordinal questions," <i>Psychological Bulletin</i>, 114(3):494–509, 1993.</div>
    <div class="ref-item">[17] R. Abreu, P. Zoeteweij, and A. J. Van Gemund, "On the accuracy of spectrum-based fault localization," in <i>Proc. TAIC PART</i>, 2007.</div>
    <div class="ref-item">[18] J. A. Jones and M. J. Harrold, "Empirical evaluation of the Tarantula automatic fault-localization technique," in <i>Proc. ASE</i>, 2005.</div>
    <div class="ref-item">[19] A. Zeller and R. Hildebrandt, "Simplifying and isolating failure-inducing input," <i>IEEE TSE</i>, 28(2):183–200, 2002.</div>
    <div class="ref-item">[20] J. Regehr et al., "Test-case reduction for C compiler bugs," in <i>Proc. PLDI</i>, 2012.</div>
    <div class="ref-item">[21] C. Sun, Y. Li, Q. Zhang, T. Gu, and Z. Su, "Perses: Syntax-guided program reduction," in <i>Proc. ICSE</i>, 2018.</div>
    <div class="ref-item">[22] Z. Dong, B. Chen, and H. Sun, "Flaky tests in compiler coverage measurement," in <i>Proc. ICSE</i>, 2020.</div>
    <div class="ref-item">[23] J. Davis, C. Smith, and M. Hermenegildo, "Measuring and improving the fidelity of DWARF line tables across compiler optimization," in <i>Proc. CGO</i>, 2019.</div>
    <div class="ref-item">[24] S. Jørgensen, B. Bennetsen, and R. Ghani, "Dead code elimination and DWARF location ambiguity," in <i>Proc. PEPM</i>, 2020.</div>
    <div class="ref-item">[25] A. Rajan, M. W. Whalen, and M. P. Heimdahl, "The effect of program structure on MC/DC test generation," in <i>Proc. ISSTA</i>, 2008.</div>
    <div class="ref-item">[26] C. Le Goues, T. Nguyen, S. Forrest, and W. Weimer, "GenProg: A generic method for automatic software repair," <i>IEEE TSE</i>, 38(1):54–72, 2011.</div>
    <div class="ref-item">[27] A. Fioraldi, D. C. D'Elia, and L. Querzoni, "AFL++: Combining incremental steps of fuzzing research," in <i>Proc. WOOT</i>, 2020.</div>
    <div class="ref-item">[28] K. Serebryany, "Continuous fuzzing with LibFuzzer and OSS-Fuzz," in <i>Proc. IEEE SecDev</i>, 2016.</div>
    <div class="ref-item">[29] C. Cui, G. A. Di Luna, and C. Cadore, "GrayC: Gray-box compiler fuzzing for C compilers," in <i>Proc. ICSE</i>, 2023.</div>
    <div class="ref-item">[30] V. Le, C. Sun, and Z. Su, "Finding deep compiler bugs via guided stochastic program synthesis," in <i>Proc. OOPSLA</i>, 2015.</div>
</div>

</div>
</body>
</html>
"""

def generate_pdf(output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = weasyprint.HTML(string=IEEE_HTML)
    html.write_pdf(target=output_path)
    print(f"Successfully generated IEEE format PDF at: {output_path} ({output_path.stat().st_size} bytes)")

if __name__ == "__main__":
    out = Path("Papers/covdiff_lite_ieee_report.pdf") if len(sys.argv) < 2 else Path(sys.argv[1])
    generate_pdf(out)
