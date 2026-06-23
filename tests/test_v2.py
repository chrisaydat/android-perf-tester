import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

import main
from src.regression import compare_against_baseline
from src.report_generator import generate_html_report
from src.thresholds import evaluate_thresholds, parse_fail_if


class FakeCollector:
    def __init__(self, package_name):
        self.package_name = package_name
        self.device_info = {
            "manufacturer": "Google",
            "model": "Pixel Test",
            "android_version": "15",
            "sdk_version": "35",
        }

    def collect_cpu_usage(self, duration=5):
        return {"samples": [20, 30, 40], "average": 30, "max": 40, "min": 20, "std_dev": 10}

    def collect_memory_info(self):
        return {"heap": {}, "graphics": 0, "total_pss": 120 * 1024}

    def collect_frame_stats(self, duration=5):
        return {
            "total_frames": 100,
            "janky_frames": 4,
            "jank_percentage": 4,
            "smooth_percentage": 96,
            "percentile_50ms": 12,
            "percentile_90ms": 18,
            "percentile_95ms": 22,
            "percentile_99ms": 30,
        }

    def collect_startup_time(self, cold_start=True):
        return {
            "type": "cold" if cold_start else "warm",
            "measurements": [{"total_time_ms": 1200, "wait_time_ms": 1250}],
            "average_total_time_ms": 1200,
            "min_total_time_ms": 1200,
            "max_total_time_ms": 1200,
        }

    def collect_battery_stats(self):
        return {}

    def collect_network_stats(self):
        return {}

    def take_performance_screenshot(self, tag=""):
        return "screenshot.png"


class FakeADB:
    def get_package_list(self):
        return ["com.example.app"]

    def get_current_activity(self):
        return "com.example.app"

    def get_device_info(self):
        return {
            "manufacturer": "Google",
            "model": "Pixel Test",
            "android_version": "15",
            "sdk_version": "35",
        }

    def get_main_activity(self, package_name):
        return f"{package_name}/.MainActivity"


class ThresholdTests(unittest.TestCase):
    def test_threshold_pass_warn_fail_and_missing(self):
        analysis = {"cpu": {"average": 50}, "memory": {"total_pss_mb": 120}}
        config = {
            "defaults": {"failOnMissingMetric": True},
            "scenarios": {
                "checkout": {
                    "cpu.average": {"warn": 40, "fail": 60},
                    "memory.total_pss_mb": {"warn": 100, "fail": 110},
                    "startup.average_ms": {"warn": 1000, "fail": 2000},
                }
            },
        }
        result = evaluate_thresholds(analysis, "checkout", config)
        statuses = {item["metric"]: item["status"] for item in result["results"]}
        self.assertEqual(statuses["cpu.average"], "warn")
        self.assertEqual(statuses["memory.total_pss_mb"], "fail")
        self.assertEqual(statuses["startup.average_ms"], "fail")

    def test_inline_fail_if_parsing(self):
        rule = parse_fail_if("frames.jank_percentage > 5%")
        self.assertEqual(rule.metric, "frames.jank_percentage")
        self.assertEqual(rule.fail, 5)


class RegressionTests(unittest.TestCase):
    def test_regression_percentage_calculation(self):
        baseline = {"analysis": {"startup": {"average_ms": 1000}}}
        current = {"analysis": {"startup": {"average_ms": 1150}}}
        result = compare_against_baseline(current, baseline, tolerance_percent=10, metrics=["startup.average_ms"])
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["results"][0]["delta_percent"], 15)

    def test_exit_code_precedence_threshold_before_warning(self):
        thresholds = {"failed": [{"metric": "cpu.average"}], "warnings": [], "missing": []}
        regression = {"failed": [], "warnings": [{"metric": "startup.average_ms"}]}
        code = main.choose_exit_code(thresholds, regression, {"threshold", "regression"})
        self.assertEqual(code, main.EXIT_THRESHOLD)


class ReportTests(unittest.TestCase):
    def test_report_generation_writes_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = generate_html_report(
                {
                    "status": "pass",
                    "package_name": "com.example.app",
                    "scenario": "checkout",
                    "summary": {"overall_score": 90},
                    "thresholds": {"results": []},
                    "recommendations": [],
                    "raw_data": {"device_info": {}},
                },
                temp_dir,
            )
            self.assertTrue(os.path.exists(path))
            self.assertTrue(os.path.exists(os.path.join(temp_dir, "assets", "styles.css")))


class CliTests(unittest.TestCase):
    def test_doctor_success(self):
        with patch("main.ADBCommands", return_value=FakeADB()):
            with redirect_stdout(StringIO()):
                self.assertEqual(main.main(["doctor", "com.example.app"]), main.EXIT_PASS)

    def test_run_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("main.PerformanceCollector", FakeCollector):
                with redirect_stdout(StringIO()):
                    code = main.main(["run", "com.example.app", "--quick", "--output", temp_dir])
            self.assertEqual(code, main.EXIT_WARN)
            generated = "\n".join(os.listdir(temp_dir))
            self.assertIn("_raw_", generated)
            self.assertIn("_analysis_", generated)
            self.assertTrue(any("_report_" in name for name in os.listdir(temp_dir)))

    def test_run_ci_threshold_failure_exits_2(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            threshold_path = os.path.join(temp_dir, "thresholds.json")
            with open(threshold_path, "w", encoding="utf-8") as handle:
                json.dump({"scenarios": {"default": {"cpu.average": {"warn": 10, "fail": 20}}}}, handle)
            with patch("main.PerformanceCollector", FakeCollector):
                with redirect_stdout(StringIO()):
                    code = main.main([
                        "run",
                        "com.example.app",
                        "--quick",
                        "--output",
                        temp_dir,
                        "--threshold-config",
                        threshold_path,
                        "--fail-on",
                        "threshold",
                        "--ci",
                    ])
            self.assertEqual(code, main.EXIT_THRESHOLD)

    def test_compare_regression_exits_3(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline = os.path.join(temp_dir, "baseline.json")
            current = os.path.join(temp_dir, "current.json")
            with open(baseline, "w", encoding="utf-8") as handle:
                json.dump({"analysis": {"startup": {"average_ms": 1000}}}, handle)
            with open(current, "w", encoding="utf-8") as handle:
                json.dump({"analysis": {"startup": {"average_ms": 1200}}}, handle)
            with redirect_stdout(StringIO()):
                code = main.main([
                    "compare",
                    "--current",
                    current,
                    "--baseline",
                    baseline,
                    "--tolerance-percent",
                    "10",
                    "--fail-on",
                    "regression",
                ])
            self.assertEqual(code, main.EXIT_REGRESSION)

    def test_legacy_command_routes_to_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("main.PerformanceCollector", FakeCollector):
                with redirect_stdout(StringIO()):
                    code = main.main(["com.example.app", "--quick", "--output", temp_dir])
            self.assertEqual(code, main.EXIT_WARN)


if __name__ == "__main__":
    unittest.main()
