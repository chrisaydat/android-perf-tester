"""
data_processor.py - Performance data processing module
Processes raw performance data and generates insights
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import statistics


class PerformanceDataProcessor:
    """Process and analyze performance data"""
    
    # Performance thresholds (can be made configurable)
    THRESHOLDS = {
        "cpu": {
            "good": 30,      # < 30% CPU usage
            "warning": 60,   # 30-60% CPU usage
            "critical": 100  # > 60% CPU usage
        },
        "memory": {
            "good": 100,     # < 100MB PSS
            "warning": 200,  # 100-200MB PSS
            "critical": 500  # > 200MB PSS (in MB)
        },
        "jank": {
            "good": 5,       # < 5% janky frames
            "warning": 10,   # 5-10% janky frames
            "critical": 100  # > 10% janky frames
        },
        "startup": {
            "good": 1000,    # < 1 second
            "warning": 2000, # 1-2 seconds
            "critical": 5000 # > 2 seconds (in ms)
        },
        "frame_time": {
            "good": 16,      # < 16ms (60 FPS)
            "warning": 33,   # 16-33ms (30-60 FPS)
            "critical": 100  # > 33ms (< 30 FPS)
        }
    }
    
    def __init__(self):
        self.results = {}
        self.analysis = {}
        self.recommendations = []
    
    def process_performance_data(self, raw_data: Dict) -> Dict:
        """Process raw performance data and generate analysis"""
        self.results = raw_data
        
        # Process each metric
        if "cpu" in raw_data.get("metrics", {}):
            self._analyze_cpu_usage(raw_data["metrics"]["cpu"])
        
        if "memory" in raw_data.get("metrics", {}):
            self._analyze_memory_usage(raw_data["metrics"]["memory"])
        
        if "frames" in raw_data.get("metrics", {}):
            self._analyze_frame_performance(raw_data["metrics"]["frames"])
        
        if "startup" in raw_data.get("metrics", {}):
            self._analyze_startup_time(raw_data["metrics"]["startup"])
        
        # Generate overall score and recommendations
        self._calculate_performance_score()
        self._generate_recommendations()
        
        return {
            "raw_data": raw_data,
            "analysis": self.analysis,
            "recommendations": self.recommendations,
            "summary": self._generate_summary()
        }
    
    def _analyze_cpu_usage(self, cpu_data: Dict):
        """Analyze CPU usage patterns"""
        if "error" in cpu_data:
            self.analysis["cpu"] = {"status": "error", "message": cpu_data["error"]}
            return
        
        avg_cpu = cpu_data.get("average", 0)
        max_cpu = cpu_data.get("max", 0)
        
        # Determine status
        status = self._get_status(avg_cpu, self.THRESHOLDS["cpu"])
        
        self.analysis["cpu"] = {
            "status": status,
            "average": avg_cpu,
            "max": max_cpu,
            "min": cpu_data.get("min", 0),
            "std_dev": cpu_data.get("std_dev", 0),
            "samples": cpu_data.get("samples", []),
            "insights": []
        }
        
        # Generate insights
        if avg_cpu > self.THRESHOLDS["cpu"]["warning"]:
            self.analysis["cpu"]["insights"].append(
                f"High CPU usage detected: {avg_cpu}% average"
            )
        
        if max_cpu > 90:
            self.analysis["cpu"]["insights"].append(
                f"CPU spikes detected: peaked at {max_cpu}%"
            )
        
        if cpu_data.get("std_dev", 0) > 20:
            self.analysis["cpu"]["insights"].append(
                "High CPU usage variability detected"
            )
    
    def _analyze_memory_usage(self, memory_data: Dict):
        """Analyze memory usage patterns"""
        if "error" in memory_data:
            self.analysis["memory"] = {"status": "error", "message": memory_data["error"]}
            return
        
        total_pss_mb = memory_data.get("total_pss", 0) / 1024
        
        # Determine status
        status = self._get_status(total_pss_mb, self.THRESHOLDS["memory"])
        
        self.analysis["memory"] = {
            "status": status,
            "total_pss_mb": round(total_pss_mb, 2),
            "native_heap_mb": round(memory_data.get("heap", {}).get("native_pss", 0) / 1024, 2),
            "dalvik_heap_mb": round(memory_data.get("heap", {}).get("dalvik_pss", 0) / 1024, 2),
            "graphics_mb": round(memory_data.get("graphics", 0) / 1024, 2),
            "insights": []
        }
        
        # Generate insights
        if total_pss_mb > self.THRESHOLDS["memory"]["warning"]:
            self.analysis["memory"]["insights"].append(
                f"High memory usage: {total_pss_mb:.1f}MB total PSS"
            )
        
        # Check for memory leaks indicators
        native_alloc = memory_data.get("heap", {}).get("native_heap_alloc", 0)
        dalvik_alloc = memory_data.get("heap", {}).get("dalvik_heap_alloc", 0)
        
        if native_alloc > 50 * 1024:  # 50MB native heap
            self.analysis["memory"]["insights"].append(
                f"Large native heap allocation: {native_alloc/1024:.1f}MB"
            )
        
        if dalvik_alloc > 100 * 1024:  # 100MB Dalvik heap
            self.analysis["memory"]["insights"].append(
                f"Large Dalvik heap allocation: {dalvik_alloc/1024:.1f}MB"
            )
    
    def _analyze_frame_performance(self, frame_data: Dict):
        """Analyze UI rendering performance"""
        if "error" in frame_data:
            self.analysis["frames"] = {"status": "error", "message": frame_data["error"]}
            return
        
        jank_percentage = frame_data.get("jank_percentage", 0)
        p90_time = frame_data.get("percentile_90ms", 0)
        
        # Determine status based on jank rate
        status = self._get_status(jank_percentage, self.THRESHOLDS["jank"])
        
        self.analysis["frames"] = {
            "status": status,
            "total_frames": frame_data.get("total_frames", 0),
            "janky_frames": frame_data.get("janky_frames", 0),
            "jank_percentage": jank_percentage,
            "smooth_percentage": frame_data.get("smooth_percentage", 100),
            "percentiles": {
                "p50": frame_data.get("percentile_50ms", 0),
                "p90": p90_time,
                "p95": frame_data.get("percentile_95ms", 0),
                "p99": frame_data.get("percentile_99ms", 0)
            },
            "insights": []
        }
        
        # Generate insights
        if jank_percentage > self.THRESHOLDS["jank"]["warning"]:
            self.analysis["frames"]["insights"].append(
                f"Poor UI smoothness: {jank_percentage}% janky frames"
            )
        
        if p90_time > self.THRESHOLDS["frame_time"]["warning"]:
            self.analysis["frames"]["insights"].append(
                f"Slow frame rendering: 90th percentile at {p90_time}ms"
            )
        
        if frame_data.get("slow_ui_thread", 0) > 0:
            self.analysis["frames"]["insights"].append(
                f"UI thread bottlenecks detected: {frame_data['slow_ui_thread']} slow operations"
            )
    
    def _analyze_startup_time(self, startup_data: Dict):
        """Analyze app startup performance"""
        if "error" in startup_data:
            self.analysis["startup"] = {"status": "error", "message": startup_data["error"]}
            return
        
        avg_time = startup_data.get("average_total_time_ms", 0)
        
        # Determine status
        status = self._get_status(avg_time, self.THRESHOLDS["startup"])
        
        self.analysis["startup"] = {
            "status": status,
            "type": startup_data.get("type", "unknown"),
            "average_ms": avg_time,
            "min_ms": startup_data.get("min_total_time_ms", 0),
            "max_ms": startup_data.get("max_total_time_ms", 0),
            "measurements": startup_data.get("measurements", []),
            "insights": []
        }
        
        # Generate insights
        if avg_time > self.THRESHOLDS["startup"]["warning"]:
            self.analysis["startup"]["insights"].append(
                f"Slow app startup: {avg_time}ms average"
            )
        
        # Check variance
        if startup_data.get("measurements"):
            times = [m.get("total_time_ms", 0) for m in startup_data["measurements"]]
            if len(times) > 1 and max(times) - min(times) > 500:
                self.analysis["startup"]["insights"].append(
                    "High startup time variance detected"
                )
    
    def _get_status(self, value: float, thresholds: Dict) -> str:
        """Determine status based on thresholds"""
        if value <= thresholds["good"]:
            return "good"
        elif value <= thresholds["warning"]:
            return "warning"
        else:
            return "critical"
    
    def _calculate_performance_score(self):
        """Calculate overall performance score (0-100)"""
        scores = []
        weights = {
            "cpu": 0.25,
            "memory": 0.25,
            "frames": 0.30,
            "startup": 0.20
        }
        
        # CPU score
        if "cpu" in self.analysis and self.analysis["cpu"]["status"] != "error":
            cpu_avg = self.analysis["cpu"]["average"]
            cpu_score = max(0, 100 - (cpu_avg / self.THRESHOLDS["cpu"]["critical"]) * 100)
            scores.append(("cpu", cpu_score))
        
        # Memory score
        if "memory" in self.analysis and self.analysis["memory"]["status"] != "error":
            mem_mb = self.analysis["memory"]["total_pss_mb"]
            mem_score = max(0, 100 - (mem_mb / self.THRESHOLDS["memory"]["critical"]) * 100)
            scores.append(("memory", mem_score))
        
        # Frame score
        if "frames" in self.analysis and self.analysis["frames"]["status"] != "error":
            jank = self.analysis["frames"]["jank_percentage"]
            frame_score = max(0, 100 - (jank / self.THRESHOLDS["jank"]["critical"]) * 100)
            scores.append(("frames", frame_score))
        
        # Startup score
        if "startup" in self.analysis and self.analysis["startup"]["status"] != "error":
            startup_ms = self.analysis["startup"]["average_ms"]
            startup_score = max(0, 100 - (startup_ms / self.THRESHOLDS["startup"]["critical"]) * 100)
            scores.append(("startup", startup_score))
        
        # Calculate weighted average
        if scores:
            total_weight = sum(weights[metric] for metric, _ in scores)
            weighted_sum = sum(score * weights[metric] for metric, score in scores)
            self.analysis["overall_score"] = round(weighted_sum / total_weight)
        else:
            self.analysis["overall_score"] = 0
    
    def _generate_recommendations(self):
        """Generate actionable recommendations based on analysis"""
        self.recommendations = []
        
        # CPU recommendations
        if "cpu" in self.analysis and self.analysis["cpu"]["status"] in ["warning", "critical"]:
            self.recommendations.append({
                "category": "CPU",
                "priority": "high" if self.analysis["cpu"]["status"] == "critical" else "medium",
                "title": "Optimize CPU Usage",
                "suggestions": [
                    "Profile CPU-intensive operations",
                    "Move heavy computations to background threads",
                    "Implement efficient algorithms and data structures",
                    "Use lazy loading for resource-intensive features"
                ]
            })
        
        # Memory recommendations
        if "memory" in self.analysis and self.analysis["memory"]["status"] in ["warning", "critical"]:
            self.recommendations.append({
                "category": "Memory",
                "priority": "high" if self.analysis["memory"]["status"] == "critical" else "medium",
                "title": "Reduce Memory Footprint",
                "suggestions": [
                    "Check for memory leaks using LeakCanary",
                    "Optimize bitmap and image handling",
                    "Implement proper lifecycle management",
                    "Use memory-efficient data structures"
                ]
            })
        
        # UI performance recommendations
        if "frames" in self.analysis and self.analysis["frames"]["status"] in ["warning", "critical"]:
            self.recommendations.append({
                "category": "UI Performance",
                "priority": "high",
                "title": "Improve UI Smoothness",
                "suggestions": [
                    "Reduce overdraw in layouts",
                    "Optimize view hierarchies",
                    "Use hardware acceleration appropriately",
                    "Avoid blocking operations on UI thread"
                ]
            })
        
        # Startup recommendations
        if "startup" in self.analysis and self.analysis["startup"]["status"] in ["warning", "critical"]:
            self.recommendations.append({
                "category": "Startup",
                "priority": "medium",
                "title": "Optimize App Startup",
                "suggestions": [
                    "Defer non-critical initialization",
                    "Use lazy initialization for heavy components",
                    "Optimize Application class onCreate()",
                    "Consider using App Startup library"
                ]
            })
    
    def _generate_summary(self) -> Dict:
        """Generate executive summary"""
        return {
            "overall_score": self.analysis.get("overall_score", 0),
            "status": self._get_overall_status(),
            "key_findings": self._get_key_findings(),
            "critical_issues": len([r for r in self.recommendations if r["priority"] == "high"]),
            "total_recommendations": len(self.recommendations)
        }
    
    def _get_overall_status(self) -> str:
        """Determine overall app status"""
        score = self.analysis.get("overall_score", 0)
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "needs_improvement"
        else:
            return "poor"
    
    def _get_key_findings(self) -> List[str]:
        """Extract key findings from analysis"""
        findings = []
        
        for metric in ["cpu", "memory", "frames", "startup"]:
            if metric in self.analysis and "insights" in self.analysis[metric]:
                findings.extend(self.analysis[metric]["insights"][:1])  # Top insight per metric
        
        return findings[:3]  # Return top 3 findings
    
    def save_processed_data(self, output_file: str):
        """Save processed data to JSON file"""
        processed_data = {
            "analysis": self.analysis,
            "recommendations": self.recommendations,
            "summary": self._generate_summary(),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(output_file, 'w') as f:
            json.dump(processed_data, f, indent=2)
        
        return output_file


def compare_performance_results(results: List[Dict]) -> Dict:
    """Compare multiple performance test results"""
    comparison = {
        "trends": {},
        "improvements": [],
        "regressions": []
    }
    
    if len(results) < 2:
        return comparison
    
    # Sort by timestamp
    sorted_results = sorted(results, key=lambda x: x.get("timestamp", ""))
    
    # Compare key metrics
    metrics_to_compare = [
        ("cpu", "average"),
        ("memory", "total_pss_mb"),
        ("frames", "jank_percentage"),
        ("startup", "average_ms")
    ]
    
    for metric, field in metrics_to_compare:
        values = []
        for result in sorted_results:
            if "analysis" in result and metric in result["analysis"]:
                value = result["analysis"][metric].get(field)
                if value is not None:
                    values.append(value)
        
        if len(values) >= 2:
            change = values[-1] - values[0]
            change_percent = (change / values[0]) * 100 if values[0] != 0 else 0
            
            comparison["trends"][metric] = {
                "initial": values[0],
                "latest": values[-1],
                "change": change,
                "change_percent": round(change_percent, 2),
                "all_values": values
            }
            
            # Determine if improvement or regression
            if metric in ["cpu", "memory", "startup"]:
                # Lower is better
                if change < -5:  # 5% improvement threshold
                    comparison["improvements"].append(f"{metric}: {abs(change_percent):.1f}% improvement")
                elif change > 5:  # 5% regression threshold
                    comparison["regressions"].append(f"{metric}: {abs(change_percent):.1f}% regression")
            elif metric == "frames":
                # For jank percentage, lower is better
                if change < -1:  # 1% improvement threshold
                    comparison["improvements"].append(f"UI smoothness: {abs(change_percent):.1f}% improvement")
                elif change > 1:  # 1% regression threshold
                    comparison["regressions"].append(f"UI smoothness: {abs(change_percent):.1f}% regression")
    
    return comparison