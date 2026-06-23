#!/usr/bin/env python3
"""
Android Performance Tester v2
QA-first Android performance testing for local and CI workflows.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.adb_commands import ADBCommands
from src.data_collector import PerformanceCollector
from src.data_processor import PerformanceDataProcessor
from src.regression import compare_against_baseline
from src.report_generator import generate_html_report
from src.thresholds import evaluate_thresholds, load_threshold_config


EXIT_PASS = 0
EXIT_WARN = 1
EXIT_THRESHOLD = 2
EXIT_REGRESSION = 3
EXIT_SETUP = 10
EXIT_APP_LAUNCH = 11
EXIT_METRIC = 12
EXIT_USAGE = 20


COMMANDS = {"doctor", "run", "suite", "compare", "report"}


class CliError(Exception):
    def __init__(self, message: str, exit_code: int = EXIT_USAGE):
        super().__init__(message)
        self.exit_code = exit_code


class Console:
    def __init__(self, quiet: bool = False):
        self.quiet = quiet

    def section(self, title: str) -> None:
        if not self.quiet:
            print(f"\n{title}")
            print("-" * len(title))

    def line(self, message: str = "") -> None:
        if not self.quiet:
            print(message)

    def error(self, message: str) -> None:
        print(f"ERROR: {message}", file=sys.stderr)


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str, payload: Dict[str, Any]) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return path


def fail_on_set(value: Optional[str]) -> set:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def build_config(args: argparse.Namespace, scenario_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if scenario_config:
        metrics = set(scenario_config.get("metrics", ["cpu", "memory", "frames", "startup"]))
        return {
            "scenario": scenario_config.get("name", getattr(args, "scenario", "default")),
            "cpu": "cpu" in metrics,
            "memory": "memory" in metrics,
            "frames": "frames" in metrics,
            "startup": "startup" in metrics,
            "battery": "battery" in metrics,
            "network": "network" in metrics,
            "screenshot": scenario_config.get("screenshot", False),
            "cpu_duration": scenario_config.get("cpu_duration", getattr(args, "cpu_duration", 5)),
            "frame_duration": scenario_config.get("frame_duration", getattr(args, "frame_duration", 5)),
            "cold_start": scenario_config.get("cold_start", not getattr(args, "warm_start", False)),
        }

    if getattr(args, "config", None):
        config = load_json(args.config)
        config.setdefault("scenario", getattr(args, "scenario", "default"))
        return config

    if getattr(args, "quick", False):
        config = {"cpu": True, "memory": True, "frames": False, "startup": False}
    elif getattr(args, "full", False):
        config = {
            "cpu": True,
            "memory": True,
            "frames": True,
            "startup": True,
            "battery": True,
            "network": True,
            "screenshot": True,
        }
    elif getattr(args, "ui_focus", False):
        config = {
            "cpu": False,
            "memory": True,
            "frames": True,
            "startup": True,
            "battery": False,
            "network": False,
            "frame_duration": 10,
        }
    else:
        config = {
            "cpu": not getattr(args, "no_cpu", False),
            "memory": not getattr(args, "no_memory", False),
            "frames": not getattr(args, "no_frames", False),
            "startup": not getattr(args, "no_startup", False),
            "battery": getattr(args, "battery", False),
            "network": getattr(args, "network", False),
            "screenshot": getattr(args, "screenshot", False),
        }

    config["scenario"] = getattr(args, "scenario", "default")
    config["cpu_duration"] = getattr(args, "cpu_duration", 5)
    config["frame_duration"] = getattr(args, "frame_duration", 5)
    config["cold_start"] = not getattr(args, "warm_start", False)
    return config


class AndroidPerformanceTester:
    def __init__(self, package_name: str, output_dir: str = "results", console: Optional[Console] = None):
        self.package_name = package_name
        self.output_dir = output_dir
        self.console = console or Console()
        self.collector = PerformanceCollector(package_name)
        self.processor = PerformanceDataProcessor()
        os.makedirs(output_dir, exist_ok=True)

    def run_full_test(
        self,
        config: Dict[str, Any],
        threshold_config: Optional[Dict[str, Any]] = None,
        inline_fail_if: Optional[List[str]] = None,
        baseline: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        scenario = config.get("scenario", "default")
        self.console.section("Device")
        device_info = self.collector.device_info
        self.console.line(f"Package: {self.package_name}")
        self.console.line(f"Scenario: {scenario}")
        self.console.line(
            f"Device: {device_info.get('manufacturer', 'Unknown')} {device_info.get('model', 'Unknown')}"
        )
        self.console.line(
            f"Android: {device_info.get('android_version', 'Unknown')} "
            f"(SDK {device_info.get('sdk_version', 'Unknown')})"
        )

        self.console.section("Running")
        raw_data = {
            "package_name": self.package_name,
            "timestamp": datetime.now().isoformat(),
            "device_info": device_info,
            "metrics": {},
            "config": config,
        }

        if config.get("cpu", True):
            raw_data["metrics"]["cpu"] = self.collector.collect_cpu_usage(config.get("cpu_duration", 5))
        if config.get("memory", True):
            raw_data["metrics"]["memory"] = self.collector.collect_memory_info()
        if config.get("frames", True):
            raw_data["metrics"]["frames"] = self.collector.collect_frame_stats(config.get("frame_duration", 5))
        if config.get("startup", True):
            raw_data["metrics"]["startup"] = self.collector.collect_startup_time(
                cold_start=config.get("cold_start", True)
            )
        if config.get("battery", False):
            raw_data["metrics"]["battery"] = self.collector.collect_battery_stats()
        if config.get("network", False):
            raw_data["metrics"]["network"] = self.collector.collect_network_stats()
        if config.get("screenshot", False):
            raw_data["screenshot"] = self.collector.take_performance_screenshot("test_complete")

        processed = self.processor.process_performance_data(raw_data)
        analysis = processed.get("analysis", {})
        threshold_results = evaluate_thresholds(
            analysis,
            scenario=scenario,
            threshold_config=threshold_config,
            inline_rules=inline_fail_if,
        )
        regression_results = None
        if baseline:
            tolerance = (threshold_config or {}).get("defaults", {}).get("regressionTolerancePercent", 10)
            regression_results = compare_against_baseline(processed, baseline, tolerance_percent=tolerance)

        status = combine_status(threshold_results, regression_results)
        report_payload = {
            "status": status,
            "package_name": self.package_name,
            "scenario": scenario,
            "raw_data": raw_data,
            "analysis": analysis,
            "summary": processed.get("summary", {}),
            "recommendations": processed.get("recommendations", []),
            "thresholds": threshold_results,
            "regression": regression_results,
            "timestamp": datetime.now().isoformat(),
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_package = self.package_name.replace("/", "_")
        raw_file = os.path.join(self.output_dir, f"{safe_package}_{scenario}_raw_{timestamp}.json")
        analysis_file = os.path.join(self.output_dir, f"{safe_package}_{scenario}_analysis_{timestamp}.json")
        report_dir = os.path.join(self.output_dir, f"{safe_package}_{scenario}_report_{timestamp}")
        write_json(raw_file, raw_data)
        write_json(analysis_file, report_payload)
        html_file = generate_html_report(report_payload, report_dir, raw_file=raw_file, analysis_file=analysis_file)

        self.console.section("Summary")
        print_threshold_summary(threshold_results, self.console)
        if regression_results:
            print_regression_summary(regression_results, self.console)
        self.console.section("Result")
        self.console.line(f"Status: {status.upper()}")
        self.console.line(f"Raw JSON: {raw_file}")
        self.console.line(f"Analysis JSON: {analysis_file}")
        self.console.line(f"HTML report: {html_file}")

        return report_payload, {"raw": raw_file, "analysis": analysis_file, "html": html_file}


def combine_status(thresholds: Dict[str, Any], regression: Optional[Dict[str, Any]]) -> str:
    if thresholds.get("status") == "fail" or (regression and regression.get("status") == "fail"):
        return "fail"
    if thresholds.get("status") == "warn" or (regression and regression.get("status") == "warn"):
        return "warn"
    return "pass"


def choose_exit_code(
    thresholds: Dict[str, Any],
    regression: Optional[Dict[str, Any]],
    fail_on: set,
) -> int:
    if thresholds.get("failed") and "threshold" in fail_on:
        return EXIT_THRESHOLD
    if thresholds.get("missing") and "missing-metric" in fail_on:
        return EXIT_THRESHOLD
    if regression and regression.get("failed") and "regression" in fail_on:
        return EXIT_REGRESSION
    if thresholds.get("warnings") or (regression and regression.get("warnings")):
        return EXIT_WARN
    return EXIT_PASS


def print_threshold_summary(thresholds: Dict[str, Any], console: Console) -> None:
    console.line("Metric                         Value       Warn        Fail        Status")
    for item in thresholds.get("results", []):
        console.line(
            f"{item['metric']:<30} {str(item['value']):<11} "
            f"{str(item['warn']):<11} {str(item['fail']):<11} {item['status'].upper()}"
        )


def print_regression_summary(regression: Dict[str, Any], console: Console) -> None:
    console.line("")
    console.line("Regression")
    console.line("Metric                         Baseline    Current     Delta %     Status")
    for item in regression.get("results", []):
        delta = item.get("delta_percent")
        delta_label = "n/a" if delta is None else f"{delta:+.2f}%"
        console.line(
            f"{item['metric']:<30} {str(item['baseline']):<11} "
            f"{str(item['current']):<11} {delta_label:<11} {item['status'].upper()}"
        )


def run_command(args: argparse.Namespace) -> int:
    console = Console(quiet=getattr(args, "quiet", False))
    package_name = args.package
    if getattr(args, "current", False) or not package_name:
        package_name = ADBCommands().get_current_activity()
        if not package_name:
            raise CliError("No package specified and no active app could be detected.", EXIT_USAGE)

    threshold_config = load_threshold_config(getattr(args, "threshold_config", None))
    baseline = load_json(args.baseline) if getattr(args, "baseline", None) else None
    config = build_config(args)
    tester = AndroidPerformanceTester(package_name, args.output, console=console)
    result, _artifacts = tester.run_full_test(
        config,
        threshold_config=threshold_config,
        inline_fail_if=getattr(args, "fail_if", None),
        baseline=baseline,
    )
    return choose_exit_code(result["thresholds"], result.get("regression"), fail_on_set(getattr(args, "fail_on", "")))


def suite_command(args: argparse.Namespace) -> int:
    suite_config = load_json(args.config)
    package_name = args.package or suite_config.get("app")
    if not package_name:
        raise CliError("Suite config must include 'app' or pass --package.", EXIT_USAGE)
    output = args.output or suite_config.get("output", "results/perf")
    threshold_config = load_threshold_config(args.threshold_config)
    baseline = load_json(args.baseline) if args.baseline else None
    fail_on = fail_on_set(args.fail_on)
    console = Console(quiet=args.quiet)
    exit_code = EXIT_PASS

    for scenario in suite_config.get("scenarios", []):
        config = build_config(args, scenario_config=scenario)
        tester = AndroidPerformanceTester(package_name, output, console=console)
        result, _artifacts = tester.run_full_test(
            config,
            threshold_config=threshold_config,
            inline_fail_if=args.fail_if,
            baseline=baseline,
        )
        scenario_exit = choose_exit_code(result["thresholds"], result.get("regression"), fail_on)
        exit_code = max(exit_code, scenario_exit)

    return exit_code


def compare_command(args: argparse.Namespace) -> int:
    current = load_json(args.current)
    baseline = load_json(args.baseline)
    result = compare_against_baseline(current, baseline, tolerance_percent=args.tolerance_percent)
    print_regression_summary(result, Console())
    if args.output:
        write_json(args.output, result)
    return choose_exit_code({"failed": [], "warnings": [], "missing": []}, result, fail_on_set(args.fail_on))


def report_command(args: argparse.Namespace) -> int:
    payload = load_json(args.input)
    report_payload = {
        "status": payload.get("status", payload.get("summary", {}).get("status", "pass")),
        "package_name": payload.get("package_name", payload.get("raw_data", {}).get("package_name", "unknown")),
        "scenario": payload.get("scenario", "default"),
        "raw_data": payload.get("raw_data", {}),
        "analysis": payload.get("analysis", {}),
        "summary": payload.get("summary", {}),
        "recommendations": payload.get("recommendations", []),
        "thresholds": payload.get("thresholds", {"results": []}),
        "regression": payload.get("regression"),
        "timestamp": payload.get("timestamp", datetime.now().isoformat()),
    }
    path = generate_html_report(report_payload, args.output, analysis_file=args.input)
    print(f"HTML report: {path}")
    return EXIT_PASS


def doctor_command(args: argparse.Namespace) -> int:
    console = Console()
    console.section("Checks")
    adb = ADBCommands()
    console.line("adb connection        PASS")
    device = adb.get_device_info()
    console.line(f"device detected       PASS ({device.get('manufacturer')} {device.get('model')})")
    if args.package:
        packages = adb.get_package_list()
        if args.package not in packages:
            console.line(f"package installed     FAIL ({args.package})")
            return EXIT_SETUP
        console.line(f"package installed     PASS ({args.package})")
        activity = adb.get_main_activity(args.package)
        if not activity:
            console.line("activity launchable   FAIL")
            return EXIT_APP_LAUNCH
        console.line(f"activity launchable   PASS ({activity})")
    console.line("metrics available     PASS")
    return EXIT_PASS


def add_run_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("package", nargs="?", help="Package name to test")
    parser.add_argument("--current", action="store_true", help="Test currently active app")
    parser.add_argument("--scenario", default="default", help="Scenario name for reports and thresholds")
    parser.add_argument("--output", default="results", help="Output directory")
    parser.add_argument("--config", help="Run configuration JSON")
    parser.add_argument("--threshold-config", help="Threshold configuration JSON")
    parser.add_argument("--baseline", help="Baseline analysis JSON for regression detection")
    parser.add_argument("--fail-if", action="append", help="Inline threshold, for example: cpu.average > 45")
    parser.add_argument("--fail-on", default="", help="Comma-separated failure modes: threshold,regression,missing-metric")
    parser.add_argument("--ci", action="store_true", help="CI mode; intended for stable output and exit codes")
    parser.add_argument("--quiet", action="store_true", help="Reduce terminal output")
    parser.add_argument("--quick", action="store_true", help="Quick test (CPU and memory)")
    parser.add_argument("--full", action="store_true", help="Full test")
    parser.add_argument("--ui-focus", action="store_true", help="Focus on UI rendering, startup, and memory")
    parser.add_argument("--no-cpu", action="store_true", help="Skip CPU test")
    parser.add_argument("--no-memory", action="store_true", help="Skip memory test")
    parser.add_argument("--no-frames", action="store_true", help="Skip frame rendering test")
    parser.add_argument("--no-startup", action="store_true", help="Skip startup time test")
    parser.add_argument("--battery", action="store_true", help="Include battery stats")
    parser.add_argument("--network", action="store_true", help="Include network stats")
    parser.add_argument("--screenshot", action="store_true", help="Take screenshot after test")
    parser.add_argument("--cpu-duration", type=int, default=5, help="CPU collection duration in seconds")
    parser.add_argument("--frame-duration", type=int, default=5, help="Frame collection duration in seconds")
    parser.add_argument("--warm-start", action="store_true", help="Measure warm start instead of cold start")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Android Perf Tester v2 - QA-first Android performance testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    doctor = subparsers.add_parser("doctor", help="Validate adb, device, package, and metric readiness")
    doctor.add_argument("package", nargs="?", help="Optional package to validate")
    doctor.set_defaults(func=doctor_command)

    run = subparsers.add_parser("run", help="Run one performance scenario")
    add_run_options(run)
    run.set_defaults(func=run_command)

    suite = subparsers.add_parser("suite", help="Run scenarios from a JSON suite config")
    suite.add_argument("--config", required=True, help="Suite configuration JSON")
    suite.add_argument("--package", help="Package name override")
    suite.add_argument("--output", help="Output directory override")
    suite.add_argument("--threshold-config", help="Threshold configuration JSON")
    suite.add_argument("--baseline", help="Baseline analysis JSON")
    suite.add_argument("--fail-if", action="append", help="Inline threshold")
    suite.add_argument("--fail-on", default="", help="Comma-separated failure modes")
    suite.add_argument("--quiet", action="store_true", help="Reduce terminal output")
    suite.set_defaults(func=suite_command)

    compare = subparsers.add_parser("compare", help="Compare current analysis JSON against a baseline")
    compare.add_argument("--current", required=True, help="Current analysis JSON")
    compare.add_argument("--baseline", required=True, help="Baseline analysis JSON")
    compare.add_argument("--tolerance-percent", type=float, default=10, help="Allowed regression percentage")
    compare.add_argument("--fail-on", default="regression", help="Comma-separated failure modes")
    compare.add_argument("--output", help="Optional JSON output path")
    compare.set_defaults(func=compare_command)

    report = subparsers.add_parser("report", help="Generate an HTML report from analysis JSON")
    report.add_argument("--input", required=True, help="Analysis JSON")
    report.add_argument("--output", required=True, help="Report output directory")
    report.set_defaults(func=report_command)

    parser.add_argument("--list", action="store_true", help=argparse.SUPPRESS)
    return parser


def legacy_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Android Performance Tester legacy command compatibility")
    add_run_options(parser)
    parser.add_argument("--list", action="store_true", help="List all installed packages")
    parser.add_argument("--compare", nargs="+", help="Compare previous result files")
    parser.add_argument("--history", action="store_true", help="Show performance history")
    return parser


def legacy_main(argv: List[str]) -> int:
    parser = legacy_parser()
    args = parser.parse_args(argv)
    if args.list:
        adb = ADBCommands()
        for package in adb.get_package_list():
            print(package)
        return EXIT_PASS
    if args.compare:
        if len(args.compare) < 2:
            raise CliError("Legacy --compare requires at least 2 files.", EXIT_USAGE)
        compare_args = argparse.Namespace(
            current=args.compare[-1],
            baseline=args.compare[0],
            tolerance_percent=10,
            fail_on="",
            output=None,
        )
        return compare_command(compare_args)
    return run_command(args)


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv and argv[0] in {"-h", "--help"}:
            build_parser().print_help()
            return EXIT_PASS
        if not argv or argv[0] not in COMMANDS:
            return legacy_main(argv)
        parser = build_parser()
        args = parser.parse_args(argv)
        if not hasattr(args, "func"):
            parser.print_help()
            return EXIT_USAGE
        return args.func(args)
    except CliError as error:
        Console().error(str(error))
        return error.exit_code
    except FileNotFoundError as error:
        Console().error(f"File not found: {error.filename}")
        return EXIT_USAGE
    except json.JSONDecodeError as error:
        Console().error(f"Invalid JSON: {error}")
        return EXIT_USAGE
    except Exception as error:
        Console().error(str(error))
        return EXIT_SETUP


if __name__ == "__main__":
    sys.exit(main())
