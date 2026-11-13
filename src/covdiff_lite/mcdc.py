"""Modified Condition/Decision Coverage (MC/DC) and branch analysis engine.

Formalizes condition-decision trees, Boolean truth tables, independence pair
identification (Unique-Cause and Masking MC/DC under DO-178C guidelines),
and branch coverage evaluation.
"""

from dataclasses import dataclass, field
from itertools import product
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ConditionOutcome:
    """Outcome for a single elementary condition within a decision."""
    condition_id: str
    true_count: int = 0
    false_count: int = 0
    unevaluated_count: int = 0

    @property
    def condition_covered(self) -> bool:
        return self.true_count > 0 and self.false_count > 0

    def to_dict(self) -> dict:
        return {
            "true": self.true_count,
            "false": self.false_count,
            "unevaluated": self.unevaluated_count,
            "condition_covered": self.condition_covered,
        }


@dataclass
class IndependencePair:
    """An MC/DC independence pair proving a condition's independent effect."""
    condition_id: str
    vector_true: Dict[str, Optional[bool]]
    vector_false: Dict[str, Optional[bool]]
    decision_true: bool
    decision_false: bool
    pair_type: str = "unique_cause"  # 'unique_cause' or 'masking'

    def to_dict(self) -> dict:
        return {
            "condition_id": self.condition_id,
            "vector_true": self.vector_true,
            "vector_false": self.vector_false,
            "decision_true": self.decision_true,
            "decision_false": self.decision_false,
            "pair_type": self.pair_type,
        }


class DecisionTree:
    """Represents a Boolean decision composed of conditions and logical operators."""

    def __init__(self, decision_id: str, expression_ast: dict):
        self.decision_id = decision_id
        self.ast = expression_ast
        self.condition_ids: List[str] = []
        self._extract_conditions(self.ast)

    def _extract_conditions(self, node: dict):
        if not isinstance(node, dict):
            return
        kind = node.get("kind")
        if kind == "decision":
            # An atomic condition inside a compound decision
            cond_id = node.get("id")
            if cond_id and cond_id != self.decision_id:
                if cond_id not in self.condition_ids:
                    self.condition_ids.append(cond_id)
            self._extract_conditions(node.get("value", {}))
        elif kind == "binary":
            self._extract_conditions(node.get("left", {}))
            self._extract_conditions(node.get("right", {}))
        elif kind == "select":
            self._extract_conditions(node.get("condition", {}))
        elif kind == "literal":
            pass

    def evaluate(self, env: Dict[str, bool]) -> Tuple[bool, Dict[str, Optional[bool]]]:
        """Evaluate with short-circuit semantics; returns (decision_val, evaluated_conditions)."""
        evaluated: Dict[str, Optional[bool]] = {cid: None for cid in self.condition_ids}

        def eval_node(node: dict) -> bool:
            kind = node.get("kind")
            if kind == "literal":
                return bool(node.get("value"))
            if kind == "decision":
                cid = node.get("id")
                if cid in env:
                    val = bool(env[cid])
                else:
                    val = eval_node(node.get("value", {}))
                if cid in evaluated:
                    evaluated[cid] = val
                return val
            if kind == "binary":
                op = node.get("op")
                left = eval_node(node["left"])
                if op == "&&":
                    if not left:
                        return False
                    return eval_node(node["right"])
                elif op == "||":
                    if left:
                        return True
                    return eval_node(node["right"])
                elif op == "==":
                    return left == eval_node(node["right"])
                else:
                    return bool(left)
            return True

        decision_result = eval_node(self.ast)
        return decision_result, evaluated

    def truth_table(self) -> List[dict]:
        """Generate full truth table with short-circuit evaluations."""
        table = []
        if not self.condition_ids:
            return table
        for combo in product([False, True], repeat=len(self.condition_ids)):
            env = dict(zip(self.condition_ids, combo))
            result, evaluated = self.evaluate(env)
            table.append({
                "inputs": env,
                "evaluated": evaluated,
                "decision": result,
            })
        return table


class MCDCAnalyzer:
    """Analyzes an execution trace of evaluations for MC/DC and decision coverage."""

    def __init__(self, decision_id: str, condition_ids: List[str]):
        self.decision_id = decision_id
        self.condition_ids = list(condition_ids)
        self.true_count = 0
        self.false_count = 0
        self.condition_stats = {
            cid: ConditionOutcome(condition_id=cid) for cid in self.condition_ids
        }
        self.observed_evaluations: List[Tuple[bool, Dict[str, Optional[bool]]]] = []

    def record_evaluation(self, decision_val: bool, condition_vals: Dict[str, Optional[bool]]):
        """Record one execution of the decision."""
        if decision_val:
            self.true_count += 1
        else:
            self.false_count += 1

        for cid, val in condition_vals.items():
            if cid not in self.condition_stats:
                self.condition_stats[cid] = ConditionOutcome(condition_id=cid)
            stat = self.condition_stats[cid]
            if val is True:
                stat.true_count += 1
            elif val is False:
                stat.false_count += 1
            else:
                stat.unevaluated_count += 1

        self.observed_evaluations.append((decision_val, dict(condition_vals)))

    def find_independence_pair(self, condition_id: str) -> Optional[IndependencePair]:
        """Find an MC/DC independence pair for condition_id in observed evaluations."""
        # Find (T1, T2) where condition_id changes, decision changes, and other evaluated conditions hold
        true_evals = [e for e in self.observed_evaluations if e[1].get(condition_id) is True]
        false_evals = [e for e in self.observed_evaluations if e[1].get(condition_id) is False]

        for d_t, c_t in true_evals:
            for d_f, c_f in false_evals:
                if d_t == d_f:
                    continue  # Decision must flip!

                # Check Unique-Cause: all other conditions must either be unchanged or unevaluated
                unique_cause = True
                for other_cid in self.condition_ids:
                    if other_cid == condition_id:
                        continue
                    v_t = c_t.get(other_cid)
                    v_f = c_f.get(other_cid)
                    # If evaluated in both, must be identical
                    if v_t is not None and v_f is not None and v_t != v_f:
                        unique_cause = False
                        break

                if unique_cause:
                    return IndependencePair(
                        condition_id=condition_id,
                        vector_true=c_t,
                        vector_false=c_f,
                        decision_true=d_t,
                        decision_false=d_f,
                        pair_type="unique_cause",
                    )

        # Fallback to Masking MC/DC: decision flips, condition flips
        for d_t, c_t in true_evals:
            for d_f, c_f in false_evals:
                if d_t != d_f:
                    return IndependencePair(
                        condition_id=condition_id,
                        vector_true=c_t,
                        vector_false=c_f,
                        decision_true=d_t,
                        decision_false=d_f,
                        pair_type="masking",
                    )
        return None

    def compute_summary(self) -> dict:
        """Compute full MC/DC and decision coverage report."""
        decision_covered = (self.true_count > 0) and (self.false_count > 0)
        conditions_summary = {}
        mcdc_pairs = {}
        satisfied_mcdc_count = 0

        for cid in self.condition_ids:
            stat = self.condition_stats[cid]
            pair = self.find_independence_pair(cid)
            mcdc_satisfied = pair is not None
            if mcdc_satisfied:
                satisfied_mcdc_count += 1
                mcdc_pairs[cid] = pair.to_dict()
            else:
                mcdc_pairs[cid] = None

            conditions_summary[cid] = {
                **stat.to_dict(),
                "mcdc_satisfied": mcdc_satisfied,
                "independence_pair": mcdc_pairs[cid],
            }

        num_conditions = len(self.condition_ids)
        mcdc_pct = (satisfied_mcdc_count / num_conditions * 100.0) if num_conditions > 0 else (100.0 if decision_covered else 0.0)
        cond_pct = (sum(1 for s in self.condition_stats.values() if s.condition_covered) / num_conditions * 100.0) if num_conditions > 0 else 100.0

        return {
            "decision_id": self.decision_id,
            "decision_coverage": {
                "true": self.true_count,
                "false": self.false_count,
                "covered": decision_covered,
            },
            "num_conditions": num_conditions,
            "conditions": conditions_summary,
            "condition_coverage_pct": cond_pct,
            "mcdc_coverage_pct": mcdc_pct,
            "mcdc_fully_satisfied": (satisfied_mcdc_count == num_conditions) and decision_covered,
        }
