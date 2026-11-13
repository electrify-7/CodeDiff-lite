"""Unit and integration tests for Enterprise CI Audit, DO-178C Cert, and Dashboard."""

import tempfile
import unittest
from pathlib import Path

from covdiff_lite.audit import classify_line_attribution_cause, AuditVerdict
from covdiff_lite.cert import generate_mcdc_certificate
from covdiff_lite.dashboard import generate_dashboard_html


class EnterpriseAuditTests(unittest.TestCase):
    def test_classify_line_attribution_causes(self):
        source = [
            "#define FOO 1",
            "int main(void) {",
            "    if (x && y) {",
            "        /* a comment */",
            "        int x = 10;",
            "    }",
            "    return 0;",
            "}",
        ]
        self.assertEqual(classify_line_attribution_cause(source, 1), "macro_preprocessor_directive")
        self.assertEqual(classify_line_attribution_cause(source, 3), "conditional_split_branch")
        self.assertEqual(classify_line_attribution_cause(source, 4), "comment_token_attribution")
        self.assertEqual(classify_line_attribution_cause(source, 5), "statement_execution")
        self.assertEqual(classify_line_attribution_cause(source, 6), "delimiter_token_mapping")
        self.assertEqual(classify_line_attribution_cause(source, 999), "out_of_bounds")

    def test_audit_verdict_to_dict(self):
        verdict = AuditVerdict(
            target_name="test.c",
            verdict="FLIP_RISK",
            ci_gate_threshold=75.0,
            gcc_percentage=76.5,
            llvm_percentage=74.2,
            macro_divergence_pct=2.3,
            gcc_only_lines=[10, 11],
            llvm_only_lines=[15],
            root_cause_categories={"statement_execution": 3},
            markdown_report="# Report"
        )
        d = verdict.to_dict()
        self.assertEqual(d["verdict"], "FLIP_RISK")
        self.assertEqual(d["gcc_only_lines_count"], 2)
        self.assertEqual(d["llvm_only_lines_count"], 1)


class EnterpriseCertTests(unittest.TestCase):
    def test_generate_mcdc_certificate_fully_satisfied(self):
        decisions = [{"id": "d1", "conditions": ["A", "B"]}]
        # Two evaluations satisfying independence:
        # A=T, B=T -> T
        # A=F, B=T -> F (independence for A)
        # A=T, B=F -> F (independence for B)
        test_vectors = [
            {"d1": {"outcome": True, "conditions": {"A": True, "B": True}}},
            {"d1": {"outcome": False, "conditions": {"A": False, "B": True}}},
            {"d1": {"outcome": False, "conditions": {"A": True, "B": False}}},
        ]
        cert = generate_mcdc_certificate("safety_core.c", decisions, test_vectors)
        self.assertTrue(cert.all_decisions_satisfied)
        self.assertEqual(cert.overall_mcdc_percentage, 100.0)
        self.assertIn("CERTIFIED COMPLIANT", cert.to_markdown())

    def test_generate_mcdc_certificate_partially_satisfied(self):
        decisions = [{"id": "d1", "conditions": ["A", "B"]}]
        test_vectors = [
            {"d1": {"outcome": True, "conditions": {"A": True, "B": True}}},
            {"d1": {"outcome": False, "conditions": {"A": False, "B": True}}},
        ]
        cert = generate_mcdc_certificate("safety_core.c", decisions, test_vectors)
        self.assertFalse(cert.all_decisions_satisfied)
        self.assertEqual(cert.decisions_fully_covered, 0)
        self.assertIn("NON-COMPLIANT", cert.to_markdown())


class EnterpriseDashboardTests(unittest.TestCase):
    def test_generate_dashboard_html(self):
        with tempfile.TemporaryDirectory() as td:
            out_file = Path(td) / "index.html"
            res = generate_dashboard_html(out_file)
            self.assertTrue(res.exists())
            text = res.read_text(encoding="utf-8")
            self.assertIn("CovDiff-Lite", text)
            self.assertIn("30,000", text)
            self.assertIn("SQLite", text)

    def test_cert_cli_invocation(self):
        import json
        from covdiff_lite.cli import main
        with tempfile.TemporaryDirectory() as td:
            dec_file = Path(td) / "dec.json"
            vec_file = Path(td) / "vec.json"
            out_file = Path(td) / "cert.md"
            dec_file.write_text(json.dumps([{"id": "d1", "conditions": ["A", "B"]}]))
            vec_file.write_text(json.dumps([
                {"d1": {"outcome": True, "conditions": {"A": True, "B": True}}},
                {"d1": {"outcome": False, "conditions": {"A": False, "B": True}}},
                {"d1": {"outcome": False, "conditions": {"A": True, "B": False}}},
            ]))
            ret = main(["cert", "--software-name", "FlightControl",
                        "--decisions-file", str(dec_file),
                        "--vectors-file", str(vec_file),
                        "--output", str(out_file)])
            self.assertEqual(ret, 0)
            self.assertTrue(out_file.exists())
            self.assertIn("FlightControl", out_file.read_text())


if __name__ == "__main__":
    unittest.main()
