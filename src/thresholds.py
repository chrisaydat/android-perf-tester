"""
thresholds.py - CI threshold evaluation for Android Perf Tester
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


DEFAULT_THRESHOLDS = {
    "cpu.average": {"warn": 30, "fail": 60},
    "cpu.max": {"warn": 70, "fail": 90},
    "memory.total_pss_mb": {"warn": 100, "fail": 200},
    "frames.jank_percentage": {"warn": 5, "fail": 10},
    "frames.percentiles.p95": {"warn": 24, "fail": 33},
    "startup.average_ms": {"warn": 1000, "fail": 2000},
}


@dataclass
class ThresholdRule:
    metric: str
    warn: Optional[float] = None
    fail: Optional[float] = None
    source: str = "config"


def load_threshold_config(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def get_nested(data: Dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def parse_fail_if(expression: str) -> ThresholdRule:
    match = re.match(r"^\s*([a-zA-Z0-9_.]+)\s*>\s*([0-9]+(?:\.[0-9]+)?)(%)?\s*$", expression)
    if not match:
        raise ValueError(
            f"Unsupported --fail-if expression '{expression}'. Use format: metric.path > number"
        )
    return ThresholdRule(metric=match.group(1), fail=float(match.group(2)), source="inline")


def _rules_for_scenario(
    scenario: str,
    threshold_config: Dict[str, Any],
    inline_rules: Optional[List[str]],
) -> List[ThresholdRule]:
    rules: Dict[str, ThresholdRule] = {
        metric: ThresholdRule(metric=metric, warn=limits.get("warn"), fail=limits.get("fail"), source="default")
        for metric, limits in DEFAULT_THRESHOLDS.items()
    }

    configured = threshold_config.get("scenarios", {}).get(scenario, {})
    if not configured and scenario != "default":
        configured = threshold_config.get("scenarios", {}).get("default", {})

    for metric, limits in configured.items():
        rules[metric] = ThresholdRule(
            metric=metric,
            warn=limits.get("warn"),
            fail=limits.get("fail"),
            source="config",
        )

    for expression in inline_rules or []:
        rule = parse_fail_if(expression)
        existing = rules.get(rule.metric, ThresholdRule(metric=rule.metric))
        existing.fail = rule.fail
        existing.source = rule.source
        rules[rule.metric] = existing

    return list(rules.values())


def evaluate_thresholds(
    analysis: Dict[str, Any],
    scenario: str = "default",
    threshold_config: Optional[Dict[str, Any]] = None,
    inline_rules: Optional[List[str]] = None,
) -> Dict[str, Any]:
    threshold_config = threshold_config or {}
    fail_on_missing = threshold_config.get("defaults", {}).get("failOnMissingMetric", False)
    results = []

    for rule in _rules_for_scenario(scenario, threshold_config, inline_rules):
        value = get_nested(analysis, rule.metric)
        if value is None:
            status = "fail" if fail_on_missing else "missing"
            results.append({
                "metric": rule.metric,
                "value": None,
                "warn": rule.warn,
                "fail": rule.fail,
                "status": status,
                "source": rule.source,
                "message": "Metric is missing",
            })
            continue

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            results.append({
                "metric": rule.metric,
                "value": value,
                "warn": rule.warn,
                "fail": rule.fail,
                "status": "fail" if fail_on_missing else "missing",
                "source": rule.source,
                "message": "Metric is not numeric",
            })
            continue

        status = "pass"
        if rule.fail is not None and numeric_value > rule.fail:
            status = "fail"
        elif rule.warn is not None and numeric_value > rule.warn:
            status = "warn"

        results.append({
            "metric": rule.metric,
            "value": numeric_value,
            "warn": rule.warn,
            "fail": rule.fail,
            "status": status,
            "source": rule.source,
            "message": "",
        })

    failed = [item for item in results if item["status"] == "fail"]
    warnings = [item for item in results if item["status"] == "warn"]
    missing = [item for item in results if item["status"] == "missing"]

    return {
        "scenario": scenario,
        "status": "fail" if failed else "warn" if warnings else "pass",
        "failed": failed,
        "warnings": warnings,
        "missing": missing,
        "results": results,
    }
