"""Semantic repeatability signatures and evidence-based case classification."""

import hashlib
import json


def semantic_signature(execution: dict) -> str:
    tools = {}
    for name, report in execution['reports'].items():
        tools[name] = {
            'lines': report['lines'], 'branches': report.get('branches', []),
            'expansions': [{key: expansion.get(key) for key in ('source_region', 'target_regions', 'branches')}
                           for expansion in report.get('expansions', [])],
        }
    errors = [{'tool': item['tool'], 'stage': item['stage']} for item in execution['errors']]
    return hashlib.sha256(json.dumps({'tools': tools, 'errors': errors,
                                     'functional_outputs': execution.get('functional_outputs', {})}, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def classify(assessments: list[dict], signatures: list[str], failures: list[list]) -> str:
    if len(signatures) > 1 and len(set(signatures)) != 1:
        return 'unstable_or_non_reproducible'
    if any(failures):
        return 'pipeline_failure'
    findings = [finding for assessment in assessments for finding in assessment['findings']]
    labels = {finding['assessment'] for finding in findings}
    if 'candidate_incorrect_report' in labels:
        return 'probable_incorrect_coverage_report' if len(signatures) >= 3 else 'unresolved_disagreement'
    if 'unresolved_disagreement' in labels:
        return 'unresolved_disagreement'
    if 'known_convention_difference' in labels:
        return 'known_convention_difference'
    return 'complete_agreement'
