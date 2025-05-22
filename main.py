#!/usr/bin/env python3
"""
Android Performance Tester - Main Script
Run performance tests on Android apps and generate reports
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, Optional

from src.adb_commands import ADBCommands
from src.data_collector import PerformanceCollector
from src.data_processor import PerformanceDataProcessor, compare_performance_results


class AndroidPerformanceTester:
    """Main class for running performance tests"""
    
    def __init__(self, package_name: str, output_dir: str = "results"):
        self.package_name = package_name
        self.output_dir = output_dir
        self.collector = PerformanceCollector(package_name)
        self.processor = PerformanceDataProcessor()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
    
    def run_full_test(self, config: Dict) -> Dict:
        """Run complete performance test suite"""
        print(f"\n{'='*60}")
        print(f"🚀 Android Performance Tester")
        print(f"📱 Package: {self.package_name}")
        print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        # Collect device info
        device_info = self.collector.device_info
        print(f"📱 Device: {device_info['manufacturer']} {device_info['model']}")
        print(f"🤖 Android: {device_info['android_version']} (SDK {device_info['sdk_version']})\n")
        
        # Initialize results
        results = {
            "package_name": self.package_name,
            "timestamp": datetime.now().isoformat(),
            "device_info": device_info,
            "metrics": {},
            "config": config
        }
        
        # Run tests based on configuration
        if config.get("cpu", True):
            results["metrics"]["cpu"] = self.collector.collect_cpu_usage(
                duration=config.get("cpu_duration", 5)
            )
        
        if config.get("memory", True):
            results["metrics"]["memory"] = self.collector.collect_memory_info()
        
        if config.get("frames", True):
            results["metrics"]["frames"] = self.collector.collect_frame_stats(
                duration=config.get("frame_duration", 5)
            )
        
        if config.get("startup", True):
            results["metrics"]["startup"] = self.collector.collect_startup_time(
                cold_start=config.get("cold_start", True)
            )
        
        if config.get("battery", False):
            results["metrics"]["battery"] = self.collector.collect_battery_stats()
        
        if config.get("network", False):
            results["metrics"]["network"] = self.collector.collect_network_stats()
        
        if config.get("screenshot", False):
            screenshot_path = self.collector.take_performance_screenshot("test_complete")
            results["screenshot"] = screenshot_path
        
        # Process the results
        processed_data = self.processor.process_performance_data(results)
        
        # Save raw and processed data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw data
        raw_file = os.path.join(self.output_dir, f"{self.package_name}_raw_{timestamp}.json")
        with open(raw_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save processed data
        processed_file = os.path.join(self.output_dir, f"{self.package_name}_analysis_{timestamp}.json")
        self.processor.save_processed_data(processed_file)
        
        print(f"\n📊 Results saved:")
        print(f"  - Raw data: {raw_file}")
        print(f"  - Analysis: {processed_file}")
        
        # Print summary
        self._print_summary(processed_data)
        
        return processed_data
    
    def _print_summary(self, processed_data: Dict):
        """Print test summary to console"""
        summary = processed_data.get("summary", {})
        analysis = processed_data.get("analysis", {})
        
        print(f"\n{'='*60}")
        print(f"📊 PERFORMANCE SUMMARY")
        print(f"{'='*60}")
        
        # Overall score
        score = summary.get("overall_score", 0)
        status = summary.get("status", "unknown")
        status_emoji = {
            "excellent": "🌟",
            "good": "✅",
            "needs_improvement": "⚠️",
            "poor": "❌"
        }.get(status, "❓")
        
        print(f"\n{status_emoji} Overall Score: {score}/100 ({status.replace('_', ' ').title()})")
        
        # Individual metrics
        print(f"\n📈 Metrics Summary:")
        
        if "cpu" in analysis and analysis["cpu"]["status"] != "error":
            cpu_status = self._get_status_emoji(analysis["cpu"]["status"])
            print(f"  {cpu_status} CPU Usage: {analysis['cpu']['average']:.1f}% average")
        
        if "memory" in analysis and analysis["memory"]["status"] != "error":
            mem_status = self._get_status_emoji(analysis["memory"]["status"])
            print(f"  {mem_status} Memory (PSS): {analysis['memory']['total_pss_mb']:.1f}MB")
        
        if "frames" in analysis and analysis["frames"]["status"] != "error":
            frame_status = self._get_status_emoji(analysis["frames"]["status"])
            print(f"  {frame_status} UI Smoothness: {analysis['frames']['smooth_percentage']:.1f}% smooth frames")
        
        if "startup" in analysis and analysis["startup"]["status"] != "error":
            startup_status = self._get_status_emoji(analysis["startup"]["status"])
            print(f"  {startup_status} Startup Time: {analysis['startup']['average_ms']}ms")
        
        # Key findings
        findings = summary.get("key_findings", [])
        if findings:
            print(f"\n🔍 Key Findings:")
            for finding in findings:
                print(f"  • {finding}")
        
        # Recommendations
        recommendations = processed_data.get("recommendations", [])
        if recommendations:
            print(f"\n💡 Top Recommendations:")
            high_priority = [r for r in recommendations if r["priority"] == "high"]
            for rec in high_priority[:3]:
                print(f"  • {rec['title']} ({rec['category']})")
        
        print(f"\n{'='*60}\n")
    
    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for status"""
        return {
            "good": "✅",
            "warning": "⚠️",
            "critical": "❌",
            "error": "❓"
        }.get(status, "❓")


def load_config(config_file: str) -> Dict:
    """Load test configuration from JSON file"""
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}


def main():
    parser = argparse.ArgumentParser(
        description="Android Performance Tester - Comprehensive performance testing for Android apps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s com.example.app                    # Test with default settings
  %(prog)s com.example.app --quick            # Quick test (CPU & memory only)
  %(prog)s com.example.app --full             # Full test including battery & network
  %(prog)s --list                             # List all installed packages
  %(prog)s --current                          # Test currently active app
  %(prog)s com.example.app --config test.json # Use custom configuration
        """
    )
    
    parser.add_argument("package", nargs="?", help="Package name to test")
    parser.add_argument("--list", action="store_true", help="List all installed packages")
    parser.add_argument("--current", action="store_true", help="Test currently active app")
    parser.add_argument("--output", default="results", help="Output directory (default: results)")
    parser.add_argument("--config", help="Configuration file (JSON)")
    
    # Test profiles
    parser.add_argument("--quick", action="store_true", help="Quick test (CPU & memory only)")
    parser.add_argument("--full", action="store_true", help="Full test (all metrics)")
    parser.add_argument("--ui-focus", action="store_true", help="Focus on UI performance")
    
    # Individual test options
    parser.add_argument("--no-cpu", action="store_true", help="Skip CPU test")
    parser.add_argument("--no-memory", action="store_true", help="Skip memory test")
    parser.add_argument("--no-frames", action="store_true", help="Skip frame rendering test")
    parser.add_argument("--no-startup", action="store_true", help="Skip startup time test")
    parser.add_argument("--battery", action="store_true", help="Include battery stats")
    parser.add_argument("--network", action="store_true", help="Include network stats")
    parser.add_argument("--screenshot", action="store_true", help="Take screenshots")
    
    # Test parameters
    parser.add_argument("--cpu-duration", type=int, default=5, help="CPU test duration in seconds")
    parser.add_argument("--frame-duration", type=int, default=5, help="Frame test duration in seconds")
    parser.add_argument("--warm-start", action="store_true", help="Test warm start instead of cold start")
    
    # Analysis options
    parser.add_argument("--compare", nargs="+", help="Compare with previous results (JSON files)")
    parser.add_argument("--history", action="store_true", help="Show performance history")
    
    args = parser.parse_args()
    
    try:
        # Initialize ADB
        adb = ADBCommands()
        
        # Handle list packages
        if args.list:
            packages = adb.get_package_list()
            print("\n📱 Installed packages:")
            for i, pkg in enumerate(packages, 1):
                print(f"  {i:3d}. {pkg}")
            print(f"\nTotal: {len(packages)} packages")
            return 0
        
        # Determine package to test
        package_name = args.package
        
        if args.current or (not package_name and not args.compare):
            package_name = adb.get_current_activity()
            if package_name:
                print(f"📱 Testing current app: {package_name}")
            else:
                print("❌ Error: No package specified and couldn't detect current app")
                parser.print_help()
                return 1
        
        # Handle comparison mode
        if args.compare:
            print("\n📊 Comparing performance results...")
            results = []
            for file_path in args.compare:
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        results.append(json.load(f))
            
            if len(results) >= 2:
                comparison = compare_performance_results(results)
                print(json.dumps(comparison, indent=2))
            else:
                print("❌ Error: Need at least 2 result files to compare")
            return 0
        
        # Build test configuration
        config = {}
        
        if args.config:
            config = load_config(args.config)
        else:
            # Apply test profiles
            if args.quick:
                config = {
                    "cpu": True,
                    "memory": True,
                    "frames": False,
                    "startup": False,
                    "battery": False,
                    "network": False
                }
            elif args.full:
                config = {
                    "cpu": True,
                    "memory": True,
                    "frames": True,
                    "startup": True,
                    "battery": True,
                    "network": True,
                    "screenshot": True
                }
            elif args.ui_focus:
                config = {
                    "cpu": False,
                    "memory": True,
                    "frames": True,
                    "startup": True,
                    "battery": False,
                    "network": False,
                    "frame_duration": 10
                }
            else:
                # Default configuration
                config = {
                    "cpu": not args.no_cpu,
                    "memory": not args.no_memory,
                    "frames": not args.no_frames,
                    "startup": not args.no_startup,
                    "battery": args.battery,
                    "network": args.network,
                    "screenshot": args.screenshot
                }
            
            # Apply test parameters
            config["cpu_duration"] = args.cpu_duration
            config["frame_duration"] = args.frame_duration
            config["cold_start"] = not args.warm_start
        
        # Run performance test
        tester = AndroidPerformanceTester(package_name, args.output)
        results = tester.run_full_test(config)
        
        # Show history if requested
        if args.history:
            print("\n📈 Performance History:")
            # Load all results for this package
            history_files = [f for f in os.listdir(args.output) 
                           if f.startswith(f"{package_name}_analysis_") and f.endswith(".json")]
            
            if history_files:
                history_data = []
                for file_name in sorted(history_files)[-5:]:  # Last 5 results
                    with open(os.path.join(args.output, file_name), 'r') as f:
                        data = json.load(f)
                        history_data.append({
                            "timestamp": data.get("timestamp", "Unknown"),
                            "score": data.get("analysis", {}).get("overall_score", 0)
                        })
                
                for entry in history_data:
                    print(f"  {entry['timestamp']}: Score {entry['score']}/100")
            else:
                print("  No history found")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())