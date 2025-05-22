"""
data_collector.py - Performance data collection module
Collects various performance metrics using ADB commands
"""

import time
import re
from datetime import datetime
from typing import Dict, List, Optional
import statistics

from src.adb_commands import ADBCommands


class PerformanceCollector:
    """Collect various performance metrics for Android apps"""
    
    def __init__(self, package_name: str):
        self.package_name = package_name
        self.adb = ADBCommands()
        self.device_info = self.adb.get_device_info()
        self.collection_timestamp = datetime.now()
    
    def collect_cpu_usage(self, duration: int = 5, interval: float = 1.0) -> Dict:
        """
        Collect CPU usage over specified duration
        
        Args:
            duration: Total duration to collect samples (seconds)
            interval: Time between samples (seconds)
        """
        print(f"📊 Collecting CPU usage for {duration} seconds...")
        cpu_samples = []
        timestamps = []
        
        samples_count = int(duration / interval)
        
        for i in range(samples_count):
            timestamp = time.time()
            output = self.adb.get_cpu_info()
            
            # Parse CPU usage for our package
            for line in output.splitlines():
                if self.package_name in line:
                    # Extract CPU percentage (format: "XX% XXXX/package.name: ...")
                    match = re.search(r'(\d+\.?\d*)%\s+\d+/' + re.escape(self.package_name), line)
                    if match:
                        cpu_samples.append(float(match.group(1)))
                        timestamps.append(timestamp)
                        print(f"  Sample {i+1}/{samples_count}: {match.group(1)}%")
                        break
            
            if i < samples_count - 1:
                time.sleep(interval)
        
        if cpu_samples:
            return {
                "samples": cpu_samples,
                "timestamps": timestamps,
                "average": round(statistics.mean(cpu_samples), 2),
                "max": round(max(cpu_samples), 2),
                "min": round(min(cpu_samples), 2),
                "std_dev": round(statistics.stdev(cpu_samples), 2) if len(cpu_samples) > 1 else 0,
                "duration": duration,
                "sample_count": len(cpu_samples)
            }
        return {"error": "Could not collect CPU data", "samples": []}
    
    def collect_memory_info(self) -> Dict:
        """Collect detailed memory usage information"""
        print("🧠 Collecting memory information...")
        output = self.adb.get_memory_info(self.package_name)
        
        memory_data = {
            "pss": {},
            "private_dirty": {},
            "heap": {},
            "graphics": 0,
            "total_pss": 0
        }
        
        # Parse memory info
        for line in output.splitlines():
            line = line.strip()
            
            # Total PSS
            if line.startswith("TOTAL") and "TOTAL SWAP" not in line:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        memory_data["total_pss"] = int(parts[1].replace(",", ""))
                    except ValueError:
                        pass
            
            # Native Heap
            elif "Native Heap" in line and ":" not in line:
                parts = line.split()
                if len(parts) >= 8:
                    try:
                        memory_data["heap"]["native_pss"] = int(parts[2].replace(",", ""))
                        memory_data["heap"]["native_private_dirty"] = int(parts[3].replace(",", ""))
                        memory_data["heap"]["native_heap_alloc"] = int(parts[5].replace(",", ""))
                        memory_data["heap"]["native_heap_free"] = int(parts[6].replace(",", ""))
                    except (ValueError, IndexError):
                        pass
            
            # Dalvik Heap
            elif "Dalvik Heap" in line and ":" not in line:
                parts = line.split()
                if len(parts) >= 8:
                    try:
                        memory_data["heap"]["dalvik_pss"] = int(parts[2].replace(",", ""))
                        memory_data["heap"]["dalvik_private_dirty"] = int(parts[3].replace(",", ""))
                        memory_data["heap"]["dalvik_heap_alloc"] = int(parts[5].replace(",", ""))
                        memory_data["heap"]["dalvik_heap_free"] = int(parts[6].replace(",", ""))
                    except (ValueError, IndexError):
                        pass
            
            # Graphics
            elif line.startswith("Graphics"):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        memory_data["graphics"] = int(parts[1].replace(",", ""))
                    except ValueError:
                        pass
        
        # Calculate some useful metrics
        if memory_data["heap"].get("native_heap_alloc") and memory_data["heap"].get("dalvik_heap_alloc"):
            memory_data["total_heap_alloc"] = (
                memory_data["heap"]["native_heap_alloc"] + 
                memory_data["heap"]["dalvik_heap_alloc"]
            )
        
        return memory_data
    
    def collect_frame_stats(self, duration: int = 5) -> Dict:
        """Collect UI rendering performance stats"""
        print(f"🎞️  Collecting frame rendering statistics for {duration} seconds...")
        
        # Reset stats
        self.adb.reset_gfx_info(self.package_name)
        
        # Let the app run
        print(f"  Recording frame data...")
        time.sleep(duration)
        
        # Get frame stats
        output = self.adb.get_gfx_info(self.package_name)
        
        frame_data = {
            "total_frames": 0,
            "janky_frames": 0,
            "percentile_50ms": 0,
            "percentile_90ms": 0,
            "percentile_95ms": 0,
            "percentile_99ms": 0,
            "vsync_count": 0,
            "input_event_count": 0,
            "slow_ui_thread": 0,
            "slow_bitmap_uploads": 0,
            "slow_draw_commands": 0
        }
        
        # Parse frame statistics
        for line in output.splitlines():
            line = line.strip()
            
            if "Total frames rendered:" in line:
                match = re.search(r'Total frames rendered:\s*(\d+)', line)
                if match:
                    frame_data["total_frames"] = int(match.group(1))
            
            elif "Janky frames:" in line:
                # Format: "Janky frames: XXX (XX.XX%)"
                match = re.search(r'Janky frames:\s*(\d+)', line)
                if match:
                    frame_data["janky_frames"] = int(match.group(1))
            
            elif "50th percentile:" in line:
                match = re.search(r'50th percentile:\s*(\d+)ms', line)
                if match:
                    frame_data["percentile_50ms"] = int(match.group(1))
            
            elif "90th percentile:" in line:
                match = re.search(r'90th percentile:\s*(\d+)ms', line)
                if match:
                    frame_data["percentile_90ms"] = int(match.group(1))
            
            elif "95th percentile:" in line:
                match = re.search(r'95th percentile:\s*(\d+)ms', line)
                if match:
                    frame_data["percentile_95ms"] = int(match.group(1))
            
            elif "99th percentile:" in line:
                match = re.search(r'99th percentile:\s*(\d+)ms', line)
                if match:
                    frame_data["percentile_99ms"] = int(match.group(1))
            
            elif "Number Slow UI thread" in line:
                match = re.search(r':\s*(\d+)', line)
                if match:
                    frame_data["slow_ui_thread"] = int(match.group(1))
            
            elif "Number Slow bitmap uploads" in line:
                match = re.search(r':\s*(\d+)', line)
                if match:
                    frame_data["slow_bitmap_uploads"] = int(match.group(1))
            
            elif "Number Slow draw" in line:
                match = re.search(r':\s*(\d+)', line)
                if match:
                    frame_data["slow_draw_commands"] = int(match.group(1))
        
        # Calculate percentages
        if frame_data["total_frames"] > 0:
            frame_data["jank_percentage"] = round(
                (frame_data["janky_frames"] / frame_data["total_frames"]) * 100, 2
            )
            frame_data["smooth_percentage"] = round(100 - frame_data["jank_percentage"], 2)
        else:
            frame_data["jank_percentage"] = 0
            frame_data["smooth_percentage"] = 100
        
        return frame_data
    
    def collect_startup_time(self, activity_name: Optional[str] = None, cold_start: bool = True) -> Dict:
        """
        Measure app startup time
        
        Args:
            activity_name: Specific activity to launch (auto-detected if None)
            cold_start: If True, force stop app first for cold start measurement
        """
        print(f"⏱️  Measuring {'cold' if cold_start else 'warm'} startup time...")
        
        startup_data = {
            "type": "cold" if cold_start else "warm",
            "measurements": []
        }
        
        # Get main activity if not provided
        if not activity_name:
            activity_name = self.adb.get_main_activity(self.package_name)
            if not activity_name:
                return {"error": "Could not determine main activity"}
        
        # Perform multiple measurements for accuracy
        num_measurements = 3
        
        for i in range(num_measurements):
            if cold_start:
                # Force stop for cold start
                self.adb.force_stop_app(self.package_name)
                time.sleep(2)  # Wait for app to fully stop
            
            # Launch app and measure
            output = self.adb.start_app(activity_name)
            
            measurement = {}
            for line in output.splitlines():
                if "TotalTime:" in line:
                    match = re.search(r'TotalTime:\s*(\d+)', line)
                    if match:
                        measurement["total_time_ms"] = int(match.group(1))
                elif "WaitTime:" in line:
                    match = re.search(r'WaitTime:\s*(\d+)', line)
                    if match:
                        measurement["wait_time_ms"] = int(match.group(1))
            
            if measurement:
                startup_data["measurements"].append(measurement)
                print(f"  Measurement {i+1}: {measurement.get('total_time_ms', 'N/A')}ms")
            
            if i < num_measurements - 1:
                time.sleep(2)  # Wait between measurements
        
        # Calculate averages
        if startup_data["measurements"]:
            total_times = [m["total_time_ms"] for m in startup_data["measurements"] 
                          if "total_time_ms" in m]
            if total_times:
                startup_data["average_total_time_ms"] = round(statistics.mean(total_times))
                startup_data["min_total_time_ms"] = min(total_times)
                startup_data["max_total_time_ms"] = max(total_times)
        
        return startup_data
    
    def collect_battery_stats(self) -> Dict:
        """Collect battery usage statistics"""
        print("🔋 Collecting battery statistics...")
        output = self.adb.get_battery_stats(self.package_name)
        
        battery_data = {
            "uid": None,
            "foreground_time_ms": 0,
            "estimated_power_mah": 0,
            "cpu_time_ms": 0,
            "wake_lock_time_ms": 0
        }
        
        # Basic parsing - this could be enhanced
        uid_pattern = f"UID \\d+.*{self.package_name}"
        for line in output.splitlines():
            if re.search(uid_pattern, line):
                battery_data["uid"] = line.strip()
            # Add more detailed parsing as needed
        
        return battery_data
    
    def collect_network_stats(self) -> Dict:
        """Collect network usage statistics"""
        print("🌐 Collecting network statistics...")
        output = self.adb.get_network_stats()
        
        network_data = {
            "mobile": {"rx_bytes": 0, "tx_bytes": 0},
            "wifi": {"rx_bytes": 0, "tx_bytes": 0},
            "total": {"rx_bytes": 0, "tx_bytes": 0}
        }
        
        # This is a simplified implementation
        # You would need to parse the complex netstats output
        # based on UID and time windows
        
        return network_data
    
    def take_performance_screenshot(self, tag: str = "") -> str:
        """Take a screenshot during performance testing"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{self.package_name}_{tag}_{timestamp}.png"
        return self.adb.take_screenshot(filename)