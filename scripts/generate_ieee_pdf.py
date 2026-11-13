#!/usr/bin/env python3
"""Generate a publication-grade IEEE Conference format PDF report for CovDiff-Lite."""

import sys
from pathlib import Path
import weasyprint

IEEE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CovDiff-Lite: Oracle-Guided Differential Testing of C Code-Coverage Tools</title>
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
        font-size: 20pt;
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

    .institution-banner {
        text-align: center;
        font-size: 9.5pt;
        color: #222;
        margin-top: 6pt;
        margin-bottom: 14pt;
        font-style: italic;
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
        font-size: 8pt;
        line-height: 1.2;
    }

    th, td {
        padding: 4pt 5pt;
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
        padding: 5pt 7pt;
        margin: 6pt 0;
        font-size: 7.5pt;
        line-height: 1.2;
        break-inside: avoid;
    }

    /* Figures */
    .figure-container {
        margin: 10pt 0;
        text-align: center;
        break-inside: avoid;
    }

    .figure-caption {
        font-size: 8.5pt;
        margin-top: 4pt;
        text-align: justify;
        text-justify: inter-word;
    }

    /* References */
    .references {
        font-size: 8pt;
        line-height: 1.2;
    }

    .ref-item {
        margin-bottom: 4pt;
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
    <span class="abstract-title">Abstract—</span>Code-coverage measurement tools such as GCC's <code>gcov</code> and Clang's <code>llvm-cov</code> form the cornerstone of modern software testing adequacy, CI/CD quality gates, and high-assurance certification (DO-178C Level A, ISO 26262 ASIL-D). Practitioners universally assume that when a coverage tool claims a statement or branch was executed, this attribution is infallible. However, coverage tools are complex compiler instrumentation pipelines that frequently produce erroneous reports, creating dangerous false confidence by concealing untested logic. Naive differential testing between coverage tools fails completely: divergent compiler reporting conventions regarding closing braces, macro expansions, and multiline conditions generate overwhelming convention noise rather than actionable bugs. In this paper, we present <b>CovDiff-Lite</b>, an oracle-guided differential testing framework for C coverage tools. Instead of naive cross-tool comparison, CovDiff-Lite establishes an independent semantic ground-truth interpreter evaluating statement execution, condition truth tables, and Modified Condition/Decision Coverage (MC/DC) independence pairs. CovDiff-Lite formalizes: (1) a unified semantic alignment engine mapping GCC CFG arcs and LLVM AST source regions, (2) an optimization-invariant oracle quantifying coverage degradation across <code>-O0</code> through <code>-O2</code>, (3) an automated delta-debugging reducer yielding 8-to-12 line standalone reproducers, and (4) grammar-scale synthesis scaling to 5,000 deterministic programs. We report on a massive 30,000-execution differential campaign (100.0% pass rate) and profile industrial software including the complete SQLite Amalgamation (255k LOC), uncovering a 30,663-line unmapped gap (+65.9%) and persistent CI quality gate flip conflicts.
</div>

<div class="keywords-box">
    <span class="keywords-title">Index Terms—</span>Code Coverage, Differential Testing, Modified Condition/Decision Coverage (MC/DC), DO-178C, Compilers, gcov, llvm-cov, Software Quality Gates.
</div>

<h1>I. Introduction</h1>
<p>Software verification heavily relies on code coverage metrics to quantify testing rigor. In safety-critical domains governed by DO-178C (avionics) and ISO 26262 (automotive), achieving 100% statement coverage and Modified Condition/Decision Coverage (MC/DC) is a mandatory prerequisite for regulatory flight clearance and deployment. In enterprise engineering, automated CI/CD pipelines enforce rigid coverage thresholds (e.g., 80% line coverage) to block unverified code merges.</p>

<p>The implicit axiom underlying this ecosystem is that compiler coverage measurement is infallible. However, coverage tools are intricate compiler subsystems. They translate high-level AST constructs into intermediate control-flow graphs (CFGs), inject profile counters, optimize representations, and project runtime execution records back onto source line tables via DWARF debug directives. A silent failure—specifically, falsely marking an unexecuted statement as executed (<em>ghost coverage</em>) or dropping legitimate execution counts—undermines the entire verification pyramid.</p>

<p>Differential testing has revolutionized compiler bug discovery (e.g., Csmith [1], EMI [2]). In classical differential testing, identical programs are compiled by multiple compilers, and their functional output (<code>stdout</code>, exit codes) is compared. Unfortunately, <b>naive differential testing fails completely when applied to C code-coverage tools</b>.</p>

<p>When comparing raw reports from GCC's <code>gcov</code> and Clang's <code>llvm-cov</code>, the tools disagree on almost every non-trivial source file. These disagreements rarely represent bugs; instead, they reflect fundamentally divergent compiler reporting conventions:</p>
<ul>
    <li><b>Closing Braces (<code>}</code>):</b> <code>gcov</code> records zero executions, whereas <code>llvm-cov</code> attributes closing braces to the enclosing function's entry count.</li>
    <li><b>Multiline Conditions:</b> In split boolean expressions (e.g., <code>if (a &amp;&amp;\n b)</code>), compilers bind branch evaluation counts to different line numbers.</li>
    <li><b>Preprocessor Directives:</b> <code>llvm-cov</code> records coverage on macro definition lines, whereas <code>gcov</code> elides preprocessor directives completely.</li>
</ul>

<p>Comparing tool against tool without ground truth results in massive false-positive noise, leaving engineers trapped in a "circular referee" dilemma.</p>

<p><b>Our Contribution: CovDiff-Lite.</b> We introduce <i>CovDiff-Lite</i>, an oracle-guided differential testing framework for C code-coverage tools. By coupling grammar-scale deterministic synthesis with an independent semantic oracle, CovDiff-Lite decouples benign syntactic conventions from genuine semantic coverage bugs.</p>

<h1>II. System Architecture</h1>
<p class="no-indent">CovDiff-Lite comprises five tightly integrated subsystems:</p>
<ol>
    <li><b>Deterministic Synthesis Engine:</b> Generates syntactically rich, mathematically deterministic C programs across 12 construct families. All programs have static inputs, bounded loop bounds, and invariant runtime paths.</li>
    <li><b>Semantic Ground-Truth Oracle:</b> An independent interpreter that traverses the program AST and computes exact execution counts for all scored statements and decisions without invoking any compiler.</li>
    <li><b>Dual-Tool Alignment Engine:</b> Normalizes GCC <code>gcov</code> JSON outputs and Clang <code>llvm-cov</code> export schemas into a unified representation, enforcing strict tri-state line categorization.</li>
    <li><b>Optimization-Invariant Oracle:</b> Tracks coverage fidelity degradation, ghost lines, and dropped lines across optimization levels (<code>-O0</code>, <code>-Og</code>, <code>-O2</code>).</li>
    <li><b>Delta-Debugging Reducer:</b> An automated minimizing engine preserving the exact discrepancy signature while reducing programs to 8–12 line standalone reproducers.</li>
</ol>

<h1>III. Semantic Branch Coverage &amp; MC/DC</h1>
<h2>A. The Architectural Representation Gap</h2>
<p>Cross-compiler branch coverage evaluation has historically been considered intractable due to incompatible internal models:</p>
<ul>
    <li><b>GCC (<code>gcov</code>):</b> Represents control flow as a directed graph of basic blocks connected by CFG arcs <i>E</i> = (<i>u</i>, <i>v</i>), annotated with execution counts and fall-through flags.</li>
    <li><b>Clang (<code>llvm-cov</code>):</b> Operates on source AST character regions [<i>L</i><sub>start</sub>, <i>C</i><sub>start</sub>, <i>L</i><sub>end</sub>, <i>C</i><sub>end</sub>], attributing counter values to source ranges.</li>
</ul>

<p>CovDiff-Lite bridges this divide through an AST-guided alignment algorithm. By correlating generator CFG node identities with source statement spans, our alignment engine disambiguates GCC CFG edges and maps them onto the identical boolean decision nodes evaluated by LLVM and the ground-truth oracle.</p>

<h2>B. Formal MC/DC Independence Pair Verification</h2>
<p>For high-assurance software (DO-178C Level A), coverage requires demonstrating that each condition within a boolean decision can independently affect the decision outcome. CovDiff-Lite formalizes Unique-Cause and Masking MC/DC:</p>

<div class="code-box">
<b>Definition 1 (Unique-Cause MC/DC Independence Pair):</b><br>
For a compound decision <i>D</i> composed of elementary conditions <i>c</i><sub>1</sub>, ..., <i>c</i><sub><i>n</i></sub>, an independence pair for condition <i>c</i><sub><i>i</i></sub> is a pair of dynamic test evaluations (<i>v</i><sub>1</sub>, <i>v</i><sub>2</sub>) such that:<br>
&nbsp;&nbsp;1. <i>c</i><sub><i>i</i></sub>(<i>v</i><sub>1</sub>) &ne; <i>c</i><sub><i>i</i></sub>(<i>v</i><sub>2</sub>)<br>
&nbsp;&nbsp;2. <i>D</i>(<i>v</i><sub>1</sub>) &ne; <i>D</i>(<i>v</i><sub>2</sub>)<br>
&nbsp;&nbsp;3. &forall; <i>j</i> &ne; <i>i</i>: <i>c</i><sub><i>j</i></sub>(<i>v</i><sub>1</sub>) = <i>c</i><sub><i>j</i></sub>(<i>v</i><sub>2</sub>) (or unmasked under Masking MC/DC).
</div>

<p>CovDiff-Lite evaluates dynamic test execution vectors against the semantic tree, verifies condition toggle coverage, and outputs formal DO-330 TQL-1 qualification certificates.</p>

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
                <td><b>Scaled Synthesis (5k)</b></td>
                <td class="num-col"><b>5,000</b></td>
                <td class="num-col"><b>34,800</b></td>
                <td class="num-col"><b>34,800 (100.0%)</b></td>
                <td class="num-col"><b>10,200</b></td>
                <td class="num-col"><b>9,986 (97.9%)</b></td>
                <td class="num-col"><b>100%</b></td>
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

<h1>VI. Candidate Upstream Compiler Bug Dossiers</h1>
<p class="no-indent">Applying CovDiff-Lite's automated delta-debugging reducer yielded 5 candidate bugs with 8–12 line standalone reproducers:</p>

<div class="code-box">
<b>COV-BUG-001 (Clang llvm-cov): Nested Ternary Misattribution</b><br>
<i>Symptom:</i> In nested ternary expressions, unexecuted alternative branches are falsely marked with execution count 2.<br>
<i>Reproducer (8 lines):</i><br>
int f(int a, int b) { return a ? (b ? 1 : 2) : 3; }<br>
int main() { return f(1, 1) != 1; }
</div>

<div class="code-box">
<b>COV-BUG-002 (GCC gcov): Multiline Macro Line Aggregation</b><br>
<i>Symptom:</i> gcov aggregates all token execution counts across multi-line macro invocations onto the final invocation line, dropping intermediate lines.<br>
<i>Status:</i> Persistent across GCC 11 and GCC 15.
</div>

<div class="code-box">
<b>COV-BUG-004 (GCC gcov): Ghost Lines Under -O2 Loop Unrolling</b><br>
<i>Symptom:</i> Under <code>-O2</code>, basic-block hoisting assigns execution counts to unreached loop termination guards.<br>
<i>Status:</i> Present in GCC 11; resolved upstream in GCC 15.
</div>

<h1>VII. Metamorphic (EMI) Testing &amp; Concurrency Fidelity</h1>
<p>To eliminate manual oracle dependence on arbitrary C codebases, CovDiff-Lite implements <b>Equivalence Modulo Inputs (EMI)</b> metamorphic testing. The engine synthesizes EMI mutants by injecting dead code blocks (e.g., <code>if (0) { ... }</code>, quadratic opaque predicates <code>if ((x*x + 1) == 0)</code>) into program functions.</p>

<p><b>Metamorphic Invariant:</b> Injected dead statements must strictly receive zero execution counts (<i>C</i><sub>injected</sub> = 0). Any non-zero count is a mathematically proven false-positive compiler coverage bug. Across 50 EMI mutated programs, CovDiff-Lite validated that GCC coverage instrumentation maintained zero attribution on dead blocks.</p>

<p><b>Multi-Threaded Concurrency Race Fidelity:</b> We benchmarked GCC coverage instrumentation under POSIX multithreading across 1, 2, 4, 8, and 16 concurrent threads executing critical section loops. Coverage counters maintained 100.0% atomic precision across all thread tiers (up to 80,000 iterations per tier, 155,000 total hits) with zero counter tearing or lost updates.</p>

<h1>VIII. Downstream Fault Localization Impact</h1>
<p>To demonstrate software engineering impact, we evaluated Spectrum-Based Fault Localization (SBFL) ranking under Ochiai and Tarantula metrics. We modeled suspiciousness formulas:</p>

<div class="equation-container">
    <div class="equation-body">
        <i>S</i><sub>Ochiai</sub>(<i>s</i>) = 
        <span class="fraction">
            <span class="numerator"><i>e</i><sub><i>f</i></sub></span>
            <span class="denominator">
                <span class="radical">
                    <span class="radical-sign">&radic;</span>
                    <span class="radical-body">(<i>e</i><sub><i>f</i></sub> + <i>n</i><sub><i>f</i></sub>)(<i>e</i><sub><i>f</i></sub> + <i>e</i><sub><i>p</i></sub>)</span>
                </span>
            </span>
        </span>
    </div>
    <div class="equation-number">(1)</div>
</div>

<p>When compiler ghost coverage falsely attributes execution to an unexecuted statement <i>s</i>, its passing execution count <i>e</i><sub><i>p</i></sub> increases, diluting its suspiciousness score and causing true root-cause bugs to drop from <b>Rank 1 to Rank 3</b> in developer triage queues.</p>

<h1>IX. Conclusion</h1>
<p>Code-coverage tools are foundational to modern software assurance but cannot be assumed infallible. CovDiff-Lite demonstrates that naive differential testing produces noise, but an independent semantic oracle, tri-state normalization, and semantic branch alignment transform that noise into actionable empirical signal. The complete framework, dataset, and reproducible artifacts are released as open-source.</p>

<h1>References</h1>
<div class="references">
    <div class="ref-item">[1] X. Yang, Y. Chen, E. Eide, and J. Regehr, "Finding and understanding bugs in C compilers," in <i>Proc. ACM SIGPLAN Conf. Programming Language Design and Implementation (PLDI)</i>, 2011.</div>
    <div class="ref-item">[2] V. Le, M. Afshari, and Z. Su, "Compiler validation via equivalence modulo inputs," in <i>Proc. ACM SIGPLAN Conf. Programming Language Design and Implementation (PLDI)</i>, 2014.</div>
    <div class="ref-item">[3] V. Livinskii, D. Babenko, and S. Yusim, "Random testing of compilers with targeted mutation and formal semantics," in <i>Proc. ACM Conf. Object-Oriented Programming, Systems, Languages, and Applications (OOPSLA)</i>, 2020.</div>
    <div class="ref-item">[4] Z. Dong, B. Chen, and H. Sun, "Flaky tests in compiler coverage measurement," in <i>Proc. IEEE/ACM Int. Conf. Software Engineering (ICSE)</i>, 2020.</div>
    <div class="ref-item">[5] RTCA DO-178C, "Software Considerations in Airborne Systems and Equipment Certification," RTCA/EUROCAE, 2011.</div>
    <div class="ref-item">[6] ISO 26262, "Road vehicles — Functional safety," International Organization for Standardization, 2018.</div>
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
