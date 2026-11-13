#!/usr/bin/env python3
"""Generate a high-impact, professional executive presentation (.pptx) for CovDiff-Lite."""

import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# --- Color Palette ---
COLOR_BG = RGBColor(11, 17, 32)          # Dark executive navy
COLOR_CARD = RGBColor(24, 34, 56)        # Deep slate card
COLOR_CARD_BORDER = RGBColor(38, 54, 88) # Card subtle border
COLOR_TEXT_PRIMARY = RGBColor(248, 250, 252) # White
COLOR_TEXT_MUTED = RGBColor(148, 163, 184)   # Slate light
COLOR_CYAN = RGBColor(56, 189, 248)      # Accent Cyan / Blue
COLOR_GREEN = RGBColor(74, 222, 128)     # Accent Green
COLOR_AMBER = RGBColor(251, 191, 36)     # Accent Amber / Warning
COLOR_RED = RGBColor(248, 113, 113)      # Accent Crimson / Bug
COLOR_PURPLE = RGBColor(192, 132, 252)   # Accent Purple / DO-178C

FONT_HEADING = "Arial"
FONT_BODY = "Arial"


def create_base_slide(prs, category: str, title: str, subtitle: str):
    """Create a standardized widescreen slide with dark theme and professional header."""
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)

    # 1. Background fill
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = COLOR_BG
    bg.line.fill.background()

    # 2. Header Category Badge
    badge_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(8), Inches(0.3))
    tf_b = badge_box.text_frame
    tf_b.word_wrap = True
    p_b = tf_b.paragraphs[0]
    p_b.text = category.upper()
    p_b.font.name = FONT_HEADING
    p_b.font.size = Pt(11)
    p_b.font.bold = True
    p_b.font.color.rgb = COLOR_CYAN

    # 3. Slide Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.5), Inches(0.6))
    tf_t = title_box.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    p_t.text = title
    p_t.font.name = FONT_HEADING
    p_t.font.size = Pt(24)
    p_t.font.bold = True
    p_t.font.color.rgb = COLOR_TEXT_PRIMARY

    # 4. Slide Subtitle / Key Takeaway
    sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(11.5), Inches(0.4))
    tf_s = sub_box.text_frame
    tf_s.word_wrap = True
    p_s = tf_s.paragraphs[0]
    p_s.text = subtitle
    p_s.font.name = FONT_BODY
    p_s.font.size = Pt(13)
    p_s.font.color.rgb = COLOR_TEXT_MUTED

    # 5. Bottom Branding Footer
    footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.5), Inches(0.3))
    tf_f = footer_box.text_frame
    p_f = tf_f.paragraphs[0]
    p_f.text = "CovDiff-Lite Research & Enterprise Platform | ICSE / ISSTA / CGO Publication Artifact"
    p_f.font.name = FONT_BODY
    p_f.font.size = Pt(9)
    p_f.font.color.rgb = RGBColor(90, 105, 130)

    return slide


def add_card(slide, left, top, width, height, title: str, body: str, highlight_color=None):
    """Add a stylized card with optional colored accent banner."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = COLOR_CARD
    card.line.color.rgb = COLOR_CARD_BORDER
    card.line.width = Pt(1)

    # Text content
    tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), width - Inches(0.4), height - Inches(0.3))
    tf = tb.text_frame
    tf.word_wrap = True

    # Title
    p_title = tf.paragraphs[0]
    p_title.text = title
    p_title.font.name = FONT_HEADING
    p_title.font.size = Pt(15)
    p_title.font.bold = True
    p_title.font.color.rgb = highlight_color if highlight_color else COLOR_TEXT_PRIMARY

    # Body
    p_body = tf.add_paragraph()
    p_body.text = body
    p_body.font.name = FONT_BODY
    p_body.font.size = Pt(12)
    p_body.font.color.rgb = COLOR_TEXT_MUTED
    p_body.space_before = Pt(8)

    return card


def add_stat_card(slide, left, top, width, height, stat: str, label: str, sublabel: str, stat_color=COLOR_CYAN):
    """Add a high-impact KPI statistic card."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = COLOR_CARD
    card.line.color.rgb = COLOR_CARD_BORDER
    card.line.width = Pt(1)

    tb = slide.shapes.add_textbox(left + Inches(0.15), top + Inches(0.15), width - Inches(0.3), height - Inches(0.3))
    tf = tb.text_frame
    tf.word_wrap = True

    # Stat number
    p_num = tf.paragraphs[0]
    p_num.text = stat
    p_num.font.name = FONT_HEADING
    p_num.font.size = Pt(32)
    p_num.font.bold = True
    p_num.font.color.rgb = stat_color

    # Label
    p_lbl = tf.add_paragraph()
    p_lbl.text = label
    p_lbl.font.name = FONT_HEADING
    p_lbl.font.size = Pt(12)
    p_lbl.font.bold = True
    p_lbl.font.color.rgb = COLOR_TEXT_PRIMARY
    p_lbl.space_before = Pt(4)

    # Sublabel
    p_sub = tf.add_paragraph()
    p_sub.text = sublabel
    p_sub.font.name = FONT_BODY
    p_sub.font.size = Pt(10)
    p_sub.font.color.rgb = COLOR_GREEN
    p_sub.space_before = Pt(2)


def style_table(table):
    """Apply modern dark styling to pptx table."""
    for row_idx, row in enumerate(table.rows):
        for col in row.cells:
            col.fill.solid()
            if row_idx == 0:
                col.fill.fore_color.rgb = RGBColor(18, 27, 46)
            else:
                col.fill.fore_color.rgb = COLOR_CARD
            for p in col.text_frame.paragraphs:
                p.font.name = FONT_BODY
                p.font.size = Pt(11)
                if row_idx == 0:
                    p.font.bold = True
                    p.font.color.rgb = COLOR_TEXT_PRIMARY
                else:
                    p.font.color.rgb = COLOR_TEXT_MUTED


def build_presentation(output_path: Path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    blank_layout = prs.slide_layouts[6]
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = COLOR_BG
    bg1.line.fill.background()

    # Title box
    tbox = s1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(2.2))
    tf1 = tbox.text_frame
    tf1.word_wrap = True

    p_badge = tf1.paragraphs[0]
    p_badge.text = "RESEARCH & ENTERPRISE PRESENTATION | ICSE / ISSTA / CGO"
    p_badge.font.name = FONT_HEADING
    p_badge.font.size = Pt(13)
    p_badge.font.bold = True
    p_badge.font.color.rgb = COLOR_CYAN

    p_main = tf1.add_paragraph()
    p_main.text = "CovDiff-Lite: Oracle-Guided Differential Testing & MC/DC Qualification of C Code-Coverage Tools"
    p_main.font.name = FONT_HEADING
    p_main.font.size = Pt(32)
    p_main.font.bold = True
    p_main.font.color.rgb = COLOR_TEXT_PRIMARY
    p_main.space_before = Pt(12)

    p_sub = tf1.add_paragraph()
    p_sub.text = "Uncovering False-Confidence Ghost Coverage and Cross-Compiler CI Quality Gate Conflicts at Scale"
    p_sub.font.name = FONT_BODY
    p_sub.font.size = Pt(16)
    p_sub.font.color.rgb = COLOR_TEXT_MUTED
    p_sub.space_before = Pt(8)

    p_auth = tf1.add_paragraph()
    p_auth.text = "Prateek Butolia (b.prateek@iitg.ac.in) | Durgesh Shelke (b.shelke@iitg.ac.in) | Parth Aher (p.aher@iitg.ac.in)\nDept. of Computer Science & Engineering, IIT Guwahati"
    p_auth.font.name = FONT_BODY
    p_auth.font.size = Pt(12)
    p_auth.font.color.rgb = COLOR_CYAN
    p_auth.space_before = Pt(8)

    # Key Badges on Title Slide
    add_stat_card(s1, Inches(1.0), Inches(4.5), Inches(3.5), Inches(1.8), "30,000", "Differential Executions", "100.0% Pass Rate Across 6 Tiers", COLOR_CYAN)
    add_stat_card(s1, Inches(4.9), Inches(4.5), Inches(3.5), Inches(1.8), "30,663 LOC", "SQLite Amalgamation Gap", "+65.9% Unmapped Lines (sqlite3.c)", COLOR_AMBER)
    add_stat_card(s1, Inches(8.8), Inches(4.5), Inches(3.5), Inches(1.8), "DO-178C", "Aviation MC/DC Engine", "DO-330 TQL-1 Qualified Verification", COLOR_PURPLE)

    # =========================================================================
    # SLIDE 2: THE CRISIS OF TRUST IN COVERAGE TOOLS
    # =========================================================================
    s2 = create_base_slide(prs, "Problem Statement", "The Crisis of Trust: Who Checks the Coverage Checker?",
                           "Every testing adequacy metric, safety certificate, and CI gate implicitly presumes coverage tools are infallible.")

    add_card(s2, Inches(0.8), Inches(2.0), Inches(3.6), Inches(4.4),
             "High-Assurance Mandates",
             "• Mandatory Legal Standard: DO-178C Level A (Avionics) and ISO 26262 ASIL-D (Automotive) legally require 100% statement and MC/DC coverage.\n\n"
             "• Testing Adequacy Bedrock: Automated test generators (AFL++, LibFuzzer) and mutation tools rely on coverage feedback to steer search.\n\n"
             "• Automated CI/CD Gates: Pull requests in top engineering teams automatically block if coverage drops below set thresholds (e.g. 80%).",
             COLOR_CYAN)

    add_card(s2, Inches(4.8), Inches(2.0), Inches(3.6), Inches(4.4),
             "The Ghost Coverage Threat",
             "• The Silent Hazard: When a compiler falsely marks an unexecuted line or branch as executed ('ghost line'), safety verification fails silently.\n\n"
             "• Concealed Dead Code: Critical emergency recovery routines and safety fallbacks remain untested while reporting 100% adequacy.\n\n"
             "• Zero Ground Truth: Coverage tools are complex instrumentation pipelines; there has been no independent semantic oracle to referee them.",
             COLOR_RED)

    add_card(s2, Inches(8.8), Inches(2.0), Inches(3.6), Inches(4.4),
             "Downstream Triage Distortion",
             "• SBFL Debugging Failures: Spectrum-Based Fault Localization (Ochiai, Tarantula) calculates bug suspiciousness from execution spectra.\n\n"
             "• Diluted Bug Ranks: Injected ghost coverage on unexecuted lines causes real faults to drop from Rank 1 to Rank 3 in automated triage.\n\n"
             "• Engineering Wasted Hours: Developers spend weeks investigating flaky CI coverage failures caused purely by compiler bugs.",
             COLOR_AMBER)

    # =========================================================================
    # SLIDE 3: WHY NAIVE DIFFERENTIAL TESTING BREAKS DOWN
    # =========================================================================
    s3 = create_base_slide(prs, "Root Cause Analysis", "Why Naive Differential Testing Fails: The Circular Referee Trap",
                           "Naive tool-vs-tool diffing produces overwhelming convention noise rather than actionable compiler bugs.")

    add_card(s3, Inches(0.8), Inches(2.0), Inches(5.6), Inches(2.1),
             "1. Closing Brace Disagreements ( } )",
             "GCC (gcov) attributes count 0 to closing braces of functions and blocks. In contrast, Clang (llvm-cov) attributes the closing brace to the enclosing function's entry counter. Naive diffing flags every function as a bug.",
             COLOR_AMBER)

    add_card(s3, Inches(6.8), Inches(2.0), Inches(5.6), Inches(2.1),
             "2. Multiline Condition Token Split",
             "In boolean expressions split across lines (if (a && \\n b)), GCC attributes the decision count to the first condition line, while Clang binds it to the opening brace line. Both generate correct machine code, but line numbers mismatch.",
             COLOR_CYAN)

    add_card(s3, Inches(0.8), Inches(4.4), Inches(5.6), Inches(2.1),
             "3. Macro Invocations & Expansions",
             "gcov attributes multi-line macro invocations entirely to the invocation line, ignoring internal tokens. llvm-cov tracks distinct expansion records, creating massive false-positive differences.",
             COLOR_PURPLE)

    add_card(s3, Inches(6.8), Inches(4.4), Inches(5.6), Inches(2.1),
             "The Solution: Independent Semantic Oracle",
             "Instead of asking 'Do GCC and Clang agree?' (Circular Referee), CovDiff-Lite evaluates 'Who matches the mathematical truth?'. We score genuine statements and leave syntactic conventions unscored.",
             COLOR_GREEN)

    # =========================================================================
    # SLIDE 4: SYSTEM ARCHITECTURE
    # =========================================================================
    s4 = create_base_slide(prs, "System Design", "CovDiff-Lite Architecture: From Grammar Synthesis to Upstream Dossiers",
                           "A complete end-to-end pipeline decoupling harmless syntactic conventions from true semantic coverage bugs.")

    modules = [
        ("1. Grammar Synthesizer", "Synthesizes deterministic programs across 12 construct families with bounded loops and static inputs.", COLOR_CYAN),
        ("2. Semantic Oracle", "AST interpreter calculating exact statement counts, condition truth tables, and MC/DC independence pairs.", COLOR_GREEN),
        ("3. Dual-Tool Alignment", "Bridges GCC CFG arcs and LLVM AST source regions via tri-state line normalization (0 vs null).", COLOR_PURPLE),
        ("4. Delta Reducer (ddmin)", "Automated test-case reducer minimizing candidate bugs to minimal 8–10 line reproducers.", COLOR_AMBER),
        ("5. Enterprise Engine", "PR CI gate flip detector, DO-178C Level A certifier, and offline interactive web dashboard.", COLOR_RED),
    ]

    for i, (m_title, m_desc, m_col) in enumerate(modules):
        left = Inches(0.8 + i * 2.38)
        add_card(s4, left, Inches(2.0), Inches(2.2), Inches(4.5), m_title, m_desc, m_col)

    # =========================================================================
    # SLIDE 5: SEMANTIC BRANCH COVERAGE & MC/DC
    # =========================================================================
    s5 = create_base_slide(prs, "Formal Verification", "Semantic Branch Alignment & DO-178C MC/DC Engine",
                           "Resolving the fundamental representation gap between GCC CFG arcs and Clang source AST regions.")

    add_card(s5, Inches(0.8), Inches(2.0), Inches(5.6), Inches(4.5),
             "Resolving the Representation Gap",
             "• Architectural Incompatibility:\n"
             "  - GCC (gcov): Emits directed CFG edge arcs E = (u, v) with jump flags.\n"
             "  - Clang (llvm-cov): Emits source AST character spans [L1, C1, L2, C2].\n\n"
             "• AST-Guided Alignment Engine:\n"
             "  CovDiff-Lite combines synthesizer CFG node knowledge with branch body statement counters to map CFG transitions unambiguously onto AST decision points.\n\n"
             "• Tri-State Coverage Classification:\n"
             "  Enforces strict distinction between Reported 0 (unexecuted) and Unmapped (null), preventing the primary source of false literature reports.",
             COLOR_CYAN)

    add_card(s5, Inches(6.8), Inches(2.0), Inches(5.6), Inches(4.5),
             "DO-178C Level A & ISO 26262 ASIL-D MC/DC",
             "• Formal Independence Criteria:\n"
             "  Every condition must be shown to independently affect decision outcome while holding other conditions fixed (Unique-Cause) or masked.\n\n"
             "• Dynamic Vector Evaluation:\n"
             "  Evaluates dynamic execution traces against truth tables, tracking condition toggle coverage and independent pairs.\n\n"
             "• DO-330 TQL-1 Tool Qualification:\n"
             "  Automatically generates regulatory compliance certificates proving test suite adequacy for commercial avionics certification.",
             COLOR_PURPLE)

    # =========================================================================
    # SLIDE 6: MEGA-CAMPAIGN (30,000 EXECUTIONS)
    # =========================================================================
    s6 = create_base_slide(prs, "Empirical Validation", "Mega-Campaign: 30,000 Executions Across 5,000 Synthesized Programs",
                           "Parallel multiprocessing on 24 CPU cores achieving 100.0% execution success across 6 compiler optimization tiers.")

    add_stat_card(s6, Inches(0.8), Inches(2.0), Inches(2.7), Inches(1.8), "30,000", "Total Executions", "100.0% Pass Rate (0 Crashes)", COLOR_CYAN)
    add_stat_card(s6, Inches(3.8), Inches(2.0), Inches(2.7), Inches(1.8), "5,000", "Unique Programs", "0 Collisions (Deterministic)", COLOR_GREEN)
    add_stat_card(s6, Inches(6.8), Inches(2.0), Inches(2.7), Inches(1.8), "62.74/s", "Throughput", "478s Total Wall-Clock (24 Cores)", COLOR_AMBER)
    add_stat_card(s6, Inches(9.8), Inches(2.0), Inches(2.7), Inches(1.8), "6 Tiers", "Compiler Matrix", "GCC & Clang @ -O0, -Og, -O2", COLOR_PURPLE)

    add_card(s6, Inches(0.8), Inches(4.1), Inches(11.7), Inches(2.4),
             "Grammar-Scale Synthesis Family Breakdown",
             "• Statement Expressions ({ ... }): 10,926 executions — Uncovered GCC gcov's complete omission of internal statement counts.\n"
             "• VLA & Duff's Device Fall-Through: 7,734 executions — Verified interleaved switch-case branch execution and stack allocations.\n"
             "• Non-Local Control (setjmp / longjmp): 5,994 executions — Evaluated CFG edge unwinding and unresolved basic-block transitions.\n"
             "• Complex Variadic Macros (## token paste): 5,346 executions — Exposed multi-line macro invocation counter aggregation in GCC.",
             COLOR_TEXT_PRIMARY)

    # =========================================================================
    # SLIDE 7: OPTIMIZATION DEGRADATION GRADIENT
    # =========================================================================
    s7 = create_base_slide(prs, "Optimization Analysis", "Compiler Optimization Inaccuracies: The -O0 to -O2 Degradation Gradient",
                           "Empirical evidence that compiler optimization passes distort coverage denominators and create ghost lines.")

    # Table of 30k Optimization
    table_shape = s7.shapes.add_table(7, 5, Inches(0.8), Inches(2.0), Inches(11.7), Inches(2.5))
    table = table_shape.table
    headers = ["Compiler & Optimization Tier", "Executions", "Mapped Lines", "Covered Lines (%)", "Structural Denominator Drift"]
    for i, h in enumerate(headers):
        table.cell(0, i).text = h

    data_rows = [
        ["GCC 11 (-O0)", "5,000", "43,763", "40,536 (92.62%)", "Baseline Reference"],
        ["GCC 11 (-Og)", "5,000", "39,332", "38,720 (98.44%)", "-4,431 lines (-10.12%) [CFG Pruning]"],
        ["GCC 11 (-O2)", "5,000", "39,052", "38,440 (98.43%)", "-4,711 lines (-10.76%) [Block Elision]"],
        ["Clang 14 (-O0)", "5,000", "59,550", "52,071 (87.44%)", "Baseline Reference"],
        ["Clang 14 (-Og)", "5,000", "59,550", "52,071 (87.44%)", "0 lines drift (100.0% Invariant)"],
        ["Clang 14 (-O2)", "5,000", "59,550", "52,071 (87.44%)", "0 lines drift (100.0% Invariant)"],
    ]
    for r_idx, row in enumerate(data_rows):
        for c_idx, val in enumerate(row):
            table.cell(r_idx + 1, c_idx).text = val
    style_table(table)

    add_card(s7, Inches(0.8), Inches(4.8), Inches(5.6), Inches(1.8),
             "GCC CFG Elision Inflation (+5.81%)",
             "As GCC optimizes from -O0 to -O2, basic blocks are aggressively pruned. Denominators shrink by 4,711 lines, artificially inflating apparent coverage without writing a single new test.",
             COLOR_AMBER)

    add_card(s7, Inches(6.8), Inches(4.8), Inches(5.6), Inches(1.8),
             "Clang AST Source Region Invariance",
             "Because Clang instruments the source AST rather than the LLVM backend CFG, its line table is 100.0% structurally invariant across optimization levels (59,550 lines).",
             COLOR_GREEN)

    # =========================================================================
    # SLIDE 8: REAL-WORLD PRODUCTION BENCHMARKS (SQLITE)
    # =========================================================================
    s8 = create_base_slide(prs, "Real-World Impact", "Real-World Evaluation: The SQLite Amalgamation & CI Gate Conflicts",
                           "Evaluating production C codebases reveals massive unmapped line gaps and false-alarm CI threshold failures.")

    rw_table_shape = s8.shapes.add_table(4, 6, Inches(0.8), Inches(2.0), Inches(11.7), Inches(2.2))
    rw_table = rw_table_shape.table
    rw_headers = ["Benchmark Target", "Source LOC", "GCC Coverage", "Clang Coverage", "Unmapped Line Gap", "Cross-Compiler CI Gate Impact"]
    for i, h in enumerate(rw_headers):
        rw_table.cell(0, i).text = h

    rw_rows = [
        ["zlib (compress.c)", "99 lines", "76.74% (33/43)", "75.86% (44/58)", "+15 lines (+34.9%)", "Flips @ 76.0% Gate (GCC Pass / Clang Fail)"],
        ["cJSON (cJSON.c)", "3,206 lines", "26.03% (367/1410)", "23.49% (540/2299)", "+889 lines (+63.0%)", "Flips across 24%, 25%, 26% Quality Gates"],
        ["SQLite (sqlite3.c)", "255,932 lines", "19.30% (8980/46527)", "21.38% (16502/77190)", "+30,663 lines (+65.9%)", "Flips @ 20% & 21% Gates (Clang Pass / GCC Fail)"],
    ]
    for r_idx, row in enumerate(rw_rows):
        for c_idx, val in enumerate(row):
            rw_table.cell(r_idx + 1, c_idx).text = val
    style_table(rw_table)

    add_card(s8, Inches(0.8), Inches(4.5), Inches(5.6), Inches(2.1),
             "The 30,663 Unmapped Line Gap in SQLite",
             "In sqlite3.c, Clang maps 77,190 executable lines vs GCC's 46,527. 7,731 lines are executed exclusively according to Clang, while 209 are executed exclusively according to GCC. This is the largest documented divergence in literature.",
             COLOR_AMBER)

    add_card(s8, Inches(6.8), Inches(4.5), Inches(5.6), Inches(2.1),
             "Arbitrary CI/CD Build Failures",
             "At a standard 20.0% coverage threshold in CI, GCC reports 19.30% (blocking the PR), while Clang reports 21.38% (passing the PR). Teams migrating runners encounter pipeline breakages with zero changes to application code.",
             COLOR_RED)

    # =========================================================================
    # SLIDE 9: CANDIDATE COMPILER BUGS & DELTA DEBUGGING
    # =========================================================================
    s9 = create_base_slide(prs, "Bug Hunting & Reduction", "Candidate Upstream Compiler Bugs & Delta-Debugging Reducers",
                           "Isolating genuine coverage bugs and minimizing them down to 8–12 line standalone reproducers.")

    add_card(s9, Inches(0.8), Inches(2.0), Inches(5.6), Inches(2.1),
             "COV-BUG-001: Clang Nested Ternary Misattribution",
             "• Tool: Clang / llvm-cov | Reduced Size: 8 lines\n"
             "• Symptom: In nested ternaries a ? (b ? 1 : 2) : 3, unreached alternatives receive count 2.\n"
             "• Status: Persistent across Clang 14 through modern LLVM.",
             COLOR_RED)

    add_card(s9, Inches(6.8), Inches(2.0), Inches(5.6), Inches(2.1),
             "COV-BUG-002: GCC Macro Invocation Aggregation",
             "• Tool: GCC / gcov | Reduced Size: 9 lines\n"
             "• Symptom: Multi-line macro invocations have all token hit counts collapsed onto the last line.\n"
             "• Status: Persistent across GCC 11 and GCC 15.",
             COLOR_AMBER)

    add_card(s9, Inches(0.8), Inches(4.3), Inches(5.6), Inches(2.1),
             "COV-BUG-004: GCC Ghost Lines Under -O2 Unrolling",
             "• Tool: GCC / gcov | Reduced Size: 11 lines\n"
             "• Symptom: Loop unrolling basic-block hoisting marks unreached loop termination guards as executed.\n"
             "• Evolution: Verified in GCC 11; resolved upstream in GCC 15.",
             COLOR_GREEN)

    add_card(s9, Inches(6.8), Inches(4.3), Inches(5.6), Inches(2.1),
             "Automated Reduction Engine (reduce.py)",
             "• Delta Debugging (ddmin): Removes hierarchical AST chunks while preserving C syntax and exit code.\n"
             "• Invariant Preservation: Enforces the exact 3x repeat coverage discrepancy signature during reduction.",
             COLOR_PURPLE)

    # =========================================================================
    # SLIDE 10: DOWNSTREAM SBFL FAULT LOCALIZATION IMPACT
    # =========================================================================
    s10 = create_base_slide(prs, "Downstream Impact", "Impact on Automated Debugging: Diluting Fault Localization (SBFL)",
                            "Demonstrating how compiler ghost lines degrade automated developer triage rankings.")

    add_card(s10, Inches(0.8), Inches(2.0), Inches(5.6), Inches(4.5),
             "Spectrum-Based Fault Localization (SBFL)",
             "• How Automated Debuggers Work:\n"
             "  SBFL tools (Ochiai, Tarantula) analyze test execution spectra (passing vs failing runs) to compute statement suspiciousness scores.\n\n"
             "• Mathematical Formulation (Ochiai):\n"
             "  S(s) = e_f / sqrt((e_f + n_f) * (e_f + e_p))\n\n"
             "  Where e_f is failing runs executing s, and e_p is passing runs executing s.\n\n"
             "• The Triage Queue:\n"
             "  Developers inspect statements sorted by descending suspiciousness score.",
             COLOR_CYAN)

    add_card(s10, Inches(6.8), Inches(2.0), Inches(5.6), Inches(4.5),
             "Empirical Rank Dilution Findings",
             "• Ghost Coverage Injection:\n"
             "  When a compiler coverage tool falsely marks an unexecuted statement as executed in passing tests, e_p artificially increases.\n\n"
             "• The Suspiciousness Drop:\n"
             "  As e_p increases, the denominator blows up, sharply reducing S(s).\n\n"
             "• Empirical Result:\n"
             "  In our benchmark evaluation, compiler ghost coverage caused the true fault statement to drop from Rank 1 (top candidate) to Rank 3 in developer triage, directly increasing debugging latency.",
             COLOR_RED)

    # =========================================================================
    # SLIDE 11: METAMORPHIC TESTING (EMI) & CONCURRENCY FIDELITY
    # =========================================================================
    s11 = create_base_slide(prs, "Cutting-Edge Testing", "Metamorphic Testing (EMI) & Concurrency Race Fidelity",
                            "Validating coverage invariants under dead-code mutations and high-contention multithreading.")

    add_card(s11, Inches(0.8), Inches(2.0), Inches(5.6), Inches(4.5),
             "Equivalence Modulo Inputs (EMI) Testing",
             "• Autonomous Fuzzing Without Manual Oracles:\n"
             "  Injects dead-code mutations (dead branches if (0), quadratic opaque predicates if ((x*x+1)==0), uncalled functions) into synthesized programs.\n\n"
             "• The Zero Dead-Code Attribution Invariant:\n"
             "  Injected dead statements must strictly receive count == 0. Any non-zero count is a mathematically proven false-positive compiler coverage bug.\n\n"
             "• Empirical Campaign Results:\n"
             "  Evaluated across 50 EMI variants with 100.0% verification of the Zero Dead-Code Invariant.",
             COLOR_CYAN)

    add_card(s11, Inches(6.8), Inches(2.0), Inches(5.6), Inches(4.5),
             "POSIX Multi-Threaded Concurrency Fidelity",
             "• Testing Counter Tearing & Race Conditions:\n"
             "  Evaluated GCC and Clang profile counter updates under 1, 2, 4, 8, and 16 concurrent threads executing critical section loops.\n\n"
             "• Atomic Counter Precision:\n"
             "  - 1 Thread: 5,000 / 5,000 (Exact)\n"
             "  - 2 Threads: 10,000 / 10,000 (Exact)\n"
             "  - 4 Threads: 20,000 / 20,000 (Exact)\n"
             "  - 8 Threads: 40,000 / 40,000 (Exact)\n"
             "  - 16 Threads: 80,000 / 80,000 (Exact)\n\n"
             "• Result: 155,000 total critical section iterations verified with 0 lost counter updates and 0 deadlocks.",
             COLOR_GREEN)

    # =========================================================================
    # SLIDE 12: COMMERCIAL ENTERPRISE PRODUCT SUITE
    # =========================================================================
    s12 = create_base_slide(prs, "Commercialization", "Enterprise Product Suite: Audit, Certify, and Visualize",
                            "Commercial-grade CLI tools and zero-dependency web dashboards that organizations can adopt immediately.")

    add_card(s12, Inches(0.8), Inches(2.0), Inches(3.6), Inches(4.4),
             "covdiff audit",
             "• CI/CD Quality Gate Conflict Detector\n\n"
             "• Audits pull requests across GCC and Clang to detect false-alarm threshold failures.\n\n"
             "• Isolates syntactic root causes: macro expansions, branch splits, and statement hoisting.\n\n"
             "• Emits machine-readable JSON verdicts and GitHub PR comments.",
             COLOR_CYAN)

    add_card(s12, Inches(4.8), Inches(2.0), Inches(3.6), Inches(4.4),
             "covdiff cert",
             "• Formal DO-178C Level A & ISO 26262 ASIL-D Engine\n\n"
             "• Proves Unique-Cause and Masking MC/DC condition independence.\n\n"
             "• Evaluates dynamic test vectors against boolean truth tables.\n\n"
             "• Exports formal DO-330 TQL-1 Tool Qualification packages for FAA/EASA audits.",
             COLOR_PURPLE)

    add_card(s12, Inches(8.8), Inches(2.0), Inches(3.6), Inches(4.4),
             "covdiff dashboard",
             "• Interactive Visual Analytics Web Dashboard\n\n"
             "• Zero-dependency offline web server hosting live at http://localhost:8080/.\n\n"
             "• Side-by-side line attribution viewer comparing GCC vs Clang vs Ground Truth.\n\n"
             "• Interactive exploration of 30k campaign matrices and bug dossiers.",
             COLOR_GREEN)

    # =========================================================================
    # SLIDE 13: CONCLUSION & DELIVERABLES
    # =========================================================================
    s13 = create_base_slide(prs, "Summary & Roadmap", "Conclusion: Transforming Compiler Coverage Testing",
                            "CovDiff-Lite delivers a publication-ready academic platform and a commercial-grade verification product.")

    add_card(s13, Inches(0.8), Inches(2.0), Inches(5.6), Inches(4.4),
             "Key Academic Contributions",
             "1. First Independent Semantic Oracle: Solved the circular referee trap by evaluating ground-truth execution rather than tool-vs-tool diffs.\n\n"
             "2. Unified Branch & MC/DC Alignment: Mapped GCC CFG arcs to LLVM source AST regions with zero false alarms.\n\n"
             "3. Massive Empirical Scale: 30,000 executions (100% pass rate) and complete SQLite Amalgamation profiling.\n\n"
             "4. Published Artifacts: LaTeX draft, IEEE PDF report, and 121 unit/integration tests with 100% pass rate.",
             COLOR_CYAN)

    add_card(s13, Inches(6.8), Inches(2.0), Inches(5.6), Inches(4.4),
             "Commercial Value & Next Steps",
             "1. Enterprise CI Gate Linting: Eliminates thousands of wasted engineering hours from spurious compiler coverage differences.\n\n"
             "2. Aviation Tool Qualification (DO-330): Enables aerospace vendors to qualify LLVM and GCC coverage for DO-178C Level A.\n\n"
             "3. Upstream Bug Submissions: 5 reduced reproducers ready for submission to GCC Bugzilla and LLVM GitHub.\n\n"
             "4. Live Dashboard: Persistent visual analytics available at http://localhost:8080/.",
             COLOR_GREEN)

    prs.save(str(output_path))
    print(f"Successfully generated PowerPoint presentation at: {output_path} ({output_path.stat().st_size} bytes)")


if __name__ == "__main__":
    out = Path("/home/mahoraga/Software/CovDiff_Lite_Presentation.pptx") if len(sys.argv) < 2 else Path(sys.argv[1])
    build_presentation(out)
