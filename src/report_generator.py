#!/usr/bin/env python3
"""
Android Performance Tester - Report Generator
Generate HTML reports from performance test results
"""

import json
import os 
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Union

from jinja2 import Environment, FileSystemLoader


class ReportGenerator:
    """Generate HTML reports from performance test results"""
    
    def __init__(self, template_dir: str = "templates"):
        """Initialize the report generator with templates directory"""
        self.template_dir = template_dir
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template = self.env.get_template("report_template.html")
    
    def generate_report(self, 
                       raw_data_file: str, 
                       analysis_file: str, 
                       output_dir: str = "reports") -> str:
        """
        Generate an HTML report from raw and analysis data files
        
        Args:
            raw_data_file: Path to raw data JSON file
            analysis_file: Path to analysis data JSON file
            output_dir: Directory to save the report
            
        Returns:
            Path to the generated HTML report
        """
        # Load data files
        with open(raw_data_file, 'r') as f:
            raw_data = json.load(f)
        
        with open(analysis_file, 'r') as f:
            analysis_data = json.load(f)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Copy assets
        assets_dir = os.path.join(output_dir, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        # Copy CSS and JS files
        for asset_file in ["styles.css", "charts.js"]:
            src_path = os.path.join(self.template_dir, "assets", asset_file)
            dst_path = os.path.join(assets_dir, asset_file)
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
        
        # Extract timestamp from filename or use current time
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "_" in os.path.basename(raw_data_file):
            try:
                # Format: package_name_raw_YYYYMMDD_HHMMSS.json
                date_part = os.path.basename(raw_data_file).split("_")[-2:]
                date_str = f"{date_part[0]}_{date_part[1].replace('.json', '')}"
                timestamp = datetime.strptime(date_str, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, IndexError):
                pass
        
        # Prepare template data
        template_data = {
            "package_name": raw_data.get("package_name", "Unknown App"),
            "timestamp": timestamp,
            "device_info": raw_data.get("device_info", {}),
            "analysis": analysis_data.get("analysis", {}),
            "recommendations": analysis_data.get("recommendations", []),
            "summary": analysis_data.get("summary", {}),
            "cpu_data": self._prepare_cpu_data(raw_data),
            "startup_data": self._prepare_startup_data(raw_data)
        }
        
        # Generate HTML
        html_content = self.template.render(**template_data)
        
        # Save HTML file
        package_name = raw_data.get("package_name", "app")
        report_filename = f"{package_name}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report_path = os.path.join(output_dir, report_filename)
        
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        return report_path
    
    def generate_report_from_console_output(self, 
                                           console_output: str, 
                                           output_dir: str = "reports") -> str:
        """
        Generate a simplified HTML report from console output
        
        Args:
            console_output: Console output from the performance test
            output_dir: Directory to save the report
            
        Returns:
            Path to the generated HTML report
        """
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Copy assets
        assets_dir = os.path.join(output_dir, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        # Copy CSS and JS files
        for asset_file in ["styles.css", "charts.js"]:
            src_path = os.path.join(self.template_dir, "assets", asset_file)
            dst_path = os.path.join(assets_dir, asset_file)
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
        
        # Parse console output
        parsed_data = self._parse_console_output(console_output)
        
        # Generate HTML using a simplified template
        simple_template = self.env.from_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ package_name }} - Android Performance Report</title>
    <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
    <div class="container">
        <header>
            <div class="header-content">
                <h1>Android Performance Report</h1>
                <div class="app-info">
                    <h2>{{ package_name }}</h2>
                    <p class="timestamp">Generated: {{ timestamp }}</p>
                </div>
            </div>
        </header>

        <section class="summary-section">
            <div class="score-container">
                <div class="score-circle {{ status }}">
                    <span class="score-value">{{ score }}</span>
                    <span class="score-label">Score</span>
                </div>
                <div class="score-details">
                    <h3>{{ status|title }} Performance</h3>
                </div>
            </div>
            
            <div class="key-findings">
                <h3>Key Findings</h3>
                <ul>
                    {% for finding in findings %}
                    <li>{{ finding }}</li>
                    {% endfor %}
                </ul>
            </div>
        </section>

        <section class="metrics-section">
            <h2>Performance Metrics</h2>
            
            <div class="metrics-grid">
                {% if memory is not none %}
                <div class="metric-card">
                    <h3>Memory Usage</h3>
                    <div class="metric-value">{{ memory }} MB</div>
                </div>
                {% endif %}
                
                {% if smoothness is not none %}
                <div class="metric-card">
                    <h3>UI Smoothness</h3>
                    <div class="metric-value">{{ smoothness }}% <span class="metric-label">smooth frames</span></div>
                </div>
                {% endif %}
                
                {% if startup is not none %}
                <div class="metric-card">
                    <h3>Startup Time</h3>
                    <div class="metric-value">{{ startup }} <span class="metric-label">ms</span></div>
                    {% if startup_measurements %}
                    <div class="startup-details">
                        <div class="startup-type">{{ startup_type|title }} Start</div>
                        {% for measurement in startup_measurements %}
                        <div class="startup-item">
                            <span class="startup-label">Measurement {{ loop.index }}:</span>
                            <span class="startup-value">{{ measurement }} ms</span>
                        </div>
                        {% endfor %}
                    </div>
                    {% endif %}
                </div>
                {% endif %}
            </div>
        </section>

        <section class="device-section">
            <h2>Device Information</h2>
            <div class="device-info">
                {% if device_manufacturer %}
                <div class="device-item">
                    <span class="device-label">Device:</span>
                    <span class="device-value">{{ device_manufacturer }} {{ device_model }}</span>
                </div>
                {% endif %}
                
                {% if android_version %}
                <div class="device-item">
                    <span class="device-label">Android Version:</span>
                    <span class="device-value">{{ android_version }}</span>
                </div>
                {% endif %}
            </div>
        </section>

        <section class="console-output">
            <h2>Console Output</h2>
            <pre>{{ console_output }}</pre>
        </section>

        <footer>
            <p>Generated with Android Performance Tester</p>
            <p class="timestamp">{{ timestamp }}</p>
        </footer>
    </div>
</body>
</html>
        """)
        
        # Generate HTML
        html_content = simple_template.render(**parsed_data, console_output=console_output)
        
        # Save HTML file
        report_filename = f"{parsed_data['package_name']}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report_path = os.path.join(output_dir, report_filename)
        
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        return report_path
    
    def _prepare_cpu_data(self, raw_data: Dict) -> List:
        """Prepare CPU data for charts"""
        cpu_samples = raw_data.get("metrics", {}).get("cpu", {}).get("samples", [])
        
        if not cpu_samples:
            return []
        
        # Format data for chart.js
        return [{"timestamp": sample.get("timestamp", ""), "value": sample.get("value", 0)} 
                for sample in cpu_samples]
    
    def _prepare_startup_data(self, raw_data: Dict) -> List:
        """Prepare startup data for charts"""
        startup_data = raw_data.get("metrics", {}).get("startup", {}).get("measurements", [])
        
        if not startup_data:
            return []
        
        return startup_data
    
    def _parse_console_output(self, console_output: str) -> Dict:
        """Parse console output to extract key metrics"""
        result = {
            "package_name": "Unknown App",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "score": 0,
            "status": "unknown",
            "findings": [],
            "memory": None,
            "smoothness": None,
            "startup": None,
            "startup_type": "cold",
            "startup_measurements": [],
            "device_manufacturer": None,
            "device_model": None,
            "android_version": None
        }
        
        # Extract package name
        for line in console_output.split('\n'):
            if "📱 Package:" in line:
                parts = line.split(":", 1)  # Split only on first occurrence
                if len(parts) > 1:
                    result["package_name"] = parts[1].strip()
                break
        
        # Extract device info
        for line in console_output.split('\n'):
            if "📱 Device:" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    device_parts = parts[1].strip().split()
                    if len(device_parts) >= 2:
                        result["device_manufacturer"] = device_parts[0]
                        result["device_model"] = " ".join(device_parts[1:])
            
            if "🤖 Android:" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    result["android_version"] = parts[1].strip()
        
        # Extract startup measurements
        for line in console_output.split('\n'):
            if "Measurement" in line and "ms" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    try:
                        ms_value = int(parts[1].strip().replace("ms", ""))
                        result["startup_measurements"].append(ms_value)
                    except ValueError:
                        pass
        
        # Extract overall score
        for line in console_output.split('\n'):
            if "Overall Score:" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    score_parts = parts[1].strip().split()
                    try:
                        result["score"] = int(score_parts[0].split('/')[0])
                        
                        # Extract status
                        if "Excellent" in line:
                            result["status"] = "excellent"
                        elif "Good" in line:
                            result["status"] = "good"
                        elif "Needs Improvement" in line:
                            result["status"] = "needs_improvement"
                        elif "Poor" in line:
                            result["status"] = "poor"
                    except (ValueError, IndexError):
                        pass
        
        # Extract memory
        for line in console_output.split('\n'):
            if "Memory (PSS):" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    try:
                        result["memory"] = float(parts[1].strip().split()[0])
                    except (ValueError, IndexError):
                        pass
        
        # Extract UI smoothness
        for line in console_output.split('\n'):
            if "UI Smoothness:" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    try:
                        result["smoothness"] = float(parts[1].strip().split('%')[0])
                    except (ValueError, IndexError):
                        pass
        
        # Extract startup time
        for line in console_output.split('\n'):
            if "Startup Time:" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    try:
                        result["startup"] = int(parts[1].strip().split()[0])
                    except (ValueError, IndexError):
                        pass
        
        # Extract key findings
        findings_section = False
        for line in console_output.split('\n'):
            if "Key Findings:" in line:
                findings_section = True
                continue
            
            if findings_section and line.strip().startswith("•"):
                finding = line.strip().replace("•", "").strip()
                if finding:
                    result["findings"].append(finding)
            
            if findings_section and line.strip().startswith("💡"):
                findings_section = False
        
        return result


def generate_report(raw_data_file: str, 
                   analysis_file: str, 
                   output_dir: str = "reports", 
                   template_dir: str = "templates") -> str:
    """
    Generate an HTML report from raw and analysis data files
    
    Args:
        raw_data_file: Path to raw data JSON file
        analysis_file: Path to analysis data JSON file
        output_dir: Directory to save the report
        template_dir: Directory containing report templates
        
    Returns:
        Path to the generated HTML report
    """
    generator = ReportGenerator(template_dir)
    return generator.generate_report(raw_data_file, analysis_file, output_dir)


def generate_report_from_console(console_output: str, 
                               output_dir: str = "reports", 
                               template_dir: str = "templates") -> str:
    """
    Generate a simplified HTML report from console output
    
    Args:
        console_output: Console output from the performance test
        output_dir: Directory to save the report
        template_dir: Directory containing report templates
        
    Returns:
        Path to the generated HTML report
    """
    generator = ReportGenerator(template_dir)
    return generator.generate_report_from_console_output(console_output, output_dir)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: report_generator.py <raw_data_file> <analysis_file> [output_dir]")
        sys.exit(1)
    
    raw_file = sys.argv[1]
    analysis_file = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "reports"
    
    report_path = generate_report(raw_file, analysis_file, output_dir)
    print(f"Report generated: {report_path}")
