#!/usr/bin/env python3
"""
Android Performance Tester
Main script for collecting performance metrics from Android apps using ADB
"""

import subprocess
import json
import time
import argparse
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import statistics


class ADBCommands:
    """Wrapper class for ADB commands"""
    
    def __init__(self):
        self.verify_adb()
    
    def verify_adb(self):
        """Verify ADB is installed and device is connected"""
        try:
            result = self.run_command(["adb", "devices"])
            if "device" not in result or result.count('\n') < 2:
                raise Exception("No Android device connected. Please connect a device and try again.")
            print("✓ ADB connection verified")
        except FileNotFoundError:
            raise Exception("ADB not found. Please install Android SDK Platform Tools.")
    
    def run_command(self, command: List[str]) -> str:
        """Execute ADB command and return output"""
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error running command {' '.join(command)}: {e.stderr}")
            return ""
    
    def get_package_list(self) -> List[str]:
        """Get list of installed packages"""
        output = self.run_command(["adb", "shell", "pm", "list", "packages"])
        packages = [line.replace("package:", "").strip() 
                   for line in output.splitlines() if line.startswith("package:")]
        return sorted(packages)
    
    def get_current_activity(self) -> Optional[str]:
        """Get currently focused activity"""
        output = self.run_command(["adb", "shell", "dumpsys", "window", "windows"])
        for line in output.splitlines():
            if "mCurrentFocus" in line:
                match = re.search(r'([a-zA-Z0-9._]+)/([a-zA-Z0-9._]+)}', line)
                if match:
                    return match.group(1)
        return None

    def get_device_info(self) -> Dict:
        """Get device information"""
        device_info = {
            "manufacturer": "Unknown",
            "model": "Unknown",
            "android_version": "Unknown",
            "sdk_version": "Unknown",
            "screen_density": "Unknown",
            "screen_size": "Unknown"
        }
        
        # Get manufacturer and model
        output = self.run_command(["adb", "shell", "getprop", "ro.product.manufacturer"])
        if output.strip():
            device_info["manufacturer"] = output.strip().title()
        
        output = self.run_command(["adb", "shell", "getprop", "ro.product.model"])
        if output.strip():
            device_info["model"] = output.strip()
        
        # Get Android version
        output = self.run_command(["adb", "shell", "getprop", "ro.build.version.release"])
        if output.strip():
            device_info["android_version"] = output.strip()
        
        # Get SDK version
        output = self.run_command(["adb", "shell", "getprop", "ro.build.version.sdk"])
        if output.strip():
            device_info["sdk_version"] = output.strip()
        
        # Get screen properties
        output = self.run_command(["adb", "shell", "wm", "density"])
        density_match = re.search(r'Physical density: (\d+)', output)
        if density_match:
            device_info["screen_density"] = density_match.group(1)
        
        output = self.run_command(["adb", "shell", "wm", "size"])
        size_match = re.search(r'Physical size: (\d+x\d+)', output)
        if size_match:
            device_info["screen_size"] = size_match.group(1)
        
        return device_info
        
    def get_cpu_info(self) -> str:
        """Get CPU info from device"""
        return self.run_command(["adb", "shell", "dumpsys", "cpuinfo"])

    def get_memory_info(self, package_name: str) -> str:
        """Get memory info for a specific package"""
        return self.run_command(["adb", "shell", "dumpsys", "meminfo", package_name])

    def reset_gfx_info(self, package_name: str) -> str:
        """Reset graphics info for a specific package"""
        return self.run_command(["adb", "shell", "dumpsys", "gfxinfo", package_name, "reset"])

    def get_gfx_info(self, package_name: str) -> str:
        """Get graphics info for a specific package"""
        return self.run_command(["adb", "shell", "dumpsys", "gfxinfo", package_name])

    def get_main_activity(self, package_name: str) -> Optional[str]:
        """Get main activity for a package"""
        output = self.run_command([
            "adb", "shell", "cmd", "package", "resolve-activity",
            "--brief", package_name
        ])
        for line in output.splitlines():
            if "/" in line:
                return line.strip()
        return None

    def force_stop_app(self, package_name: str) -> str:
        """Force stop an app"""
        return self.run_command(["adb", "shell", "am", "force-stop", package_name])

    def start_app(self, activity_name: str) -> str:
        """Start an app and measure startup time"""
        return self.run_command([
            "adb", "shell", "am", "start", "-W", "-n", activity_name
        ])

    def get_battery_stats(self, package_name: str) -> str:
        """Get battery usage stats for a package"""
        return self.run_command(["adb", "shell", "dumpsys", "batterystats", package_name])

    def get_network_stats(self) -> str:
        """Get network stats"""
        return self.run_command(["adb", "shell", "dumpsys", "netstats"])

    def take_screenshot(self, filename: str) -> str:
        """Take a screenshot and save it to a file"""
        # Create results directory if it doesn't exist
        os.makedirs("results", exist_ok=True)
        temp_path = f"/sdcard/{filename}"
        local_path = f"results/{filename}"
        
        # Take screenshot and pull it to local machine
        self.run_command(["adb", "shell", "screencap", "-p", temp_path])
        self.run_command(["adb", "pull", temp_path, local_path])
        self.run_command(["adb", "shell", "rm", temp_path])
        
        return local_path


class PerformanceCollector:
    """Collect various performance metrics"""
    
    def __init__(self, package_name: str):
        self.package_name = package_name
        self.adb = ADBCommands()
        self.data = {
            "package_name": package_name,
            "timestamp": datetime.now().isoformat(),
            "metrics": {}
        }
    
    def collect_cpu_usage(self, duration: int = 5) -> Dict:
        """Collect CPU usage over specified duration"""
        print(f"Collecting CPU usage for {duration} seconds...")
        cpu_samples = []
        
        for i in range(duration):
            output = self.adb.run_command(["adb", "shell", "dumpsys", "cpuinfo"])
            
            for line in output.splitlines():
                if self.package_name in line:
                    # Extract CPU percentage
                    match = re.search(r'(\d+\.?\d*)%', line)
                    if match:
                        cpu_samples.append(float(match.group(1)))
                        break
            
            if i < duration - 1:
                time.sleep(1)
        
        if cpu_samples:
            return {
                "samples": cpu_samples,
                "average": statistics.mean(cpu_samples),
                "max": max(cpu_samples),
                "min": min(cpu_samples)
            }
        return {"error": "Could not collect CPU data"}
    
    def collect_memory_info(self) -> Dict:
        """Collect memory usage information"""
        print("Collecting memory information...")
        output = self.adb.run_command(["adb", "shell", "dumpsys", "meminfo", self.package_name])
        
        memory_data = {}
        for line in output.splitlines():
            if "TOTAL" in line and "TOTAL SWAP" not in line:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        memory_data["total_pss_kb"] = int(parts[1].replace(",", ""))
                    except ValueError:
                        pass
            elif "Native Heap" in line:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        memory_data["native_heap_kb"] = int(parts[2].replace(",", ""))
                    except ValueError:
                        pass
            elif "Dalvik Heap" in line:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        memory_data["dalvik_heap_kb"] = int(parts[2].replace(",", ""))
                    except ValueError:
                        pass
        
        return memory_data if memory_data else {"error": "Could not collect memory data"}
    
    def collect_frame_stats(self) -> Dict:
        """Collect UI rendering performance stats"""
        print("Collecting frame rendering statistics...")
        # Reset gfxinfo
        self.adb.run_command(["adb", "shell", "dumpsys", "gfxinfo", self.package_name, "reset"])
        
        # Let the app run for a bit
        print("Recording frame data for 3 seconds...")
        time.sleep(3)
        
        output = self.adb.run_command(["adb", "shell", "dumpsys", "gfxinfo", self.package_name])
        
        frame_data = {
            "total_frames": 0,
            "janky_frames": 0,
            "percentile_90ms": 0
        }
        
        for line in output.splitlines():
            if "Total frames rendered:" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    frame_data["total_frames"] = int(match.group(1))
            elif "Janky frames:" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    frame_data["janky_frames"] = int(match.group(1))
            elif "90th percentile:" in line:
                match = re.search(r'(\d+)ms', line)
                if match:
                    frame_data["percentile_90ms"] = int(match.group(1))
        
        if frame_data["total_frames"] > 0:
            frame_data["jank_percentage"] = round(
                (frame_data["janky_frames"] / frame_data["total_frames"]) * 100, 2
            )
        
        return frame_data
    
    def collect_startup_time(self, activity_name: Optional[str] = None) -> Dict:
        """Measure app startup time"""
        print("Measuring app startup time...")
        
        # First, force stop the app
        self.adb.run_command(["adb", "shell", "am", "force-stop", self.package_name])
        time.sleep(1)
        
        # Try to get the main activity if not provided
        if not activity_name:
            output = self.adb.run_command([
                "adb", "shell", "cmd", "package", "resolve-activity",
                "--brief", self.package_name
            ])
            for line in output.splitlines():
                if "/" in line:
                    activity_name = line.strip()
                    break
        
        if not activity_name:
            return {"error": "Could not determine main activity"}
        
        # Start the app and measure time
        output = self.adb.run_command([
            "adb", "shell", "am", "start", "-W", "-n", activity_name
        ])
        
        startup_data = {}
        for line in output.splitlines():
            if "TotalTime:" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    startup_data["total_time_ms"] = int(match.group(1))
            elif "WaitTime:" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    startup_data["wait_time_ms"] = int(match.group(1))
        
        return startup_data if startup_data else {"error": "Could not measure startup time"}
    
    def collect_network_stats(self) -> Dict:
        """Collect network usage statistics"""
        print("Collecting network statistics...")
        output = self.adb.run_command(["adb", "shell", "dumpsys", "netstats"])
        
        # This is simplified - you might want to parse more detailed stats
        network_data = {
            "info": "Network stats collected",
            "detailed_parsing": "TODO"
        }
        
        return network_data
    
    def run_performance_test(self, include_startup: bool = True) -> Dict:
        """Run all performance tests"""
        print(f"\n🚀 Starting performance test for: {self.package_name}")
        print("=" * 50)
        
        # Collect all metrics
        self.data["metrics"]["cpu"] = self.collect_cpu_usage()
        self.data["metrics"]["memory"] = self.collect_memory_info()
        self.data["metrics"]["frames"] = self.collect_frame_stats()
        
        if include_startup:
            self.data["metrics"]["startup"] = self.collect_startup_time()
        
        self.data["metrics"]["network"] = self.collect_network_stats()
        
        print("\n✅ Performance test completed!")
        return self.data
    
    def save_results(self, output_dir: str = "results"):
        """Save results to JSON file"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/{self.package_name}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.data, f, indent=2)
        
        print(f"\n📊 Results saved to: {filename}")
        return filename


def main():
    parser = argparse.ArgumentParser(description="Android Performance Tester")
    parser.add_argument("package", nargs="?", help="Package name to test")
    parser.add_argument("--list-packages", action="store_true", help="List all installed packages")
    parser.add_argument("--no-startup", action="store_true", help="Skip startup time measurement")
    parser.add_argument("--output", default="results", help="Output directory for results")
    
    args = parser.parse_args()
    
    try:
        adb = ADBCommands()
        
        if args.list_packages:
            packages = adb.get_package_list()
            print("\n📱 Installed packages:")
            for pkg in packages:
                print(f"  - {pkg}")
            return
        
        if not args.package:
            # Try to get current activity's package
            current_package = adb.get_current_activity()
            if current_package:
                print(f"No package specified. Using current app: {current_package}")
                args.package = current_package
            else:
                print("Error: No package specified and couldn't detect current app.")
                print("Usage: python android_perf_tester.py <package_name>")
                print("       python android_perf_tester.py --list-packages")
                return
        
        # Run performance test
        collector = PerformanceCollector(args.package)
        results = collector.run_performance_test(include_startup=not args.no_startup)
        
        # Save results
        collector.save_results(args.output)
        
        # Print summary
        print("\n📈 Performance Summary:")
        print(f"  Package: {args.package}")
        
        if "cpu" in results["metrics"] and "average" in results["metrics"]["cpu"]:
            print(f"  CPU Average: {results['metrics']['cpu']['average']:.1f}%")
        
        if "memory" in results["metrics"] and "total_pss_kb" in results["metrics"]["memory"]:
            print(f"  Memory (PSS): {results['metrics']['memory']['total_pss_kb']:,} KB")
        
        if "frames" in results["metrics"] and "jank_percentage" in results["metrics"]["frames"]:
            print(f"  Jank Rate: {results['metrics']['frames']['jank_percentage']}%")
        
        if "startup" in results["metrics"] and "total_time_ms" in results["metrics"]["startup"]:
            print(f"  Startup Time: {results['metrics']['startup']['total_time_ms']} ms")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    main()