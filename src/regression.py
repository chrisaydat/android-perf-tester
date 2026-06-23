"""
regression.py - Baseline comparison for Android Perf Tester
"""

from typing import Any, Dict, List, Optional

from src.thresholds import get_nested


DEFAULT_REGRESSION_METRICS = [
    "cpu.average",
    "cpu.max",
    "memory.total_pss_mb",
    "frames.jank_percentage",
    "frames.percentiles.p95",
    "startup.average_ms",
]


def extract_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    if "analysis" in payload:
        return payload["analysis"]
    if "raw_data" in payload and "analysis" in payload["raw_data"]:
        return payload["raw_data"]["analysis"]
    return payload


def compare_against_baseline(
    current_payload: Dict[str, Any],
    baseline_payload: Dict[str, Any],
    tolerance_percent: float = 10,
    metrics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    current = extract_analysis(current_payload)
    baseline = extract_analysis(baseline_payload)
    results = []

    for metric in metrics or DEFAULT_REGRESSION_METRICS:
        current_value = get_nested(current, metric)
        baseline_value = get_nested(baseline, metric)
        if current_value is None or baseline_value is None:
            results.append({
                "metric": metric,
                "baseline": baseline_value,
                "current": current_value,
                "delta": None,
                "delta_percent": None,
                "status": "missing",
            })
            continue

        try:
            current_number = float(current_value)
            baseline_number = float(baseline_value)
        except (TypeError, ValueError):
            results.append({
                "metric": metric,
                "baseline": baseline_value,
                "current": current_value,
                "delta": None,
                "delta_percent": None,
                "status": "missing",
            })
            continue

        delta = current_number - baseline_number
        delta_percent = (delta / baseline_number * 100) if baseline_number else 0
        status = "pass"
        if delta_percent > tolerance_percent:
            status = "fail"
        elif delta_percent > tolerance_percent / 2:
            status = "warn"

        results.append({
            "metric": metric,
            "baseline": baseline_number,
            "current": current_number,
            "delta": round(delta, 2),
            "delta_percent": round(delta_percent, 2),
            "status": status,
        })

    failed = [item for item in results if item["status"] == "fail"]
    warnings = [item for item in results if item["status"] == "warn"]

    return {
        "status": "fail" if failed else "warn" if warnings else "pass",
        "tolerance_percent": tolerance_percent,
        "failed": failed,
        "warnings": warnings,
        "results": results,
    }
