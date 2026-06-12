# Android Performance Tester 🚀

![Python](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-Apache%202.0-green)
![Status](https://img.shields.io/badge/status-active-success)
![Contributions](https://img.shields.io/badge/contributions-welcome-orange)

# Android Performance Tester

An open-source performance testing toolkit for Android and Flutter applications.

Android Performance Tester helps QA engineers and mobile developers measure CPU usage, memory consumption, startup performance, UI rendering smoothness, battery usage, and network activity using Android Debug Bridge (ADB).

Built to support local testing, performance benchmarking, and CI/CD integration.

## Vision

Mobile teams frequently catch functional defects while performance regressions go unnoticed until late in the release cycle.

Android Performance Tester aims to make performance testing as easy and repeatable as functional testing.

## Maintainers

A community-driven project maintained by QA and Mobile Engineering professionals.

Contributions are welcome from:

- QA Engineers
- Test Automation Engineers
- Android Developers
- Flutter Developers
- Performance Engineers

## Features ✨

- **CPU Usage Monitoring** - Track CPU usage patterns over time
- **Memory Analysis** - Monitor PSS, heap usage, and potential memory leaks  
- **UI Performance** - Measure frame rendering, jank rate, and UI smoothness
- **Startup Time** - Measure cold and warm app startup times
- **Battery Usage** - Track battery consumption (optional)
- **Network Stats** - Monitor network usage (optional)
- **Device Info** - Automatically capture device specifications
- **Performance Score** - Get an overall performance score (0-100)
- **Actionable Recommendations** - Receive specific optimization suggestions

## Prerequisites 📋

1. **Python 3.6+** installed
2. **Android SDK Platform Tools** (for ADB)
   - Download from: https://developer.android.com/studio/releases/platform-tools
   - Add to PATH environment variable
3. **USB Debugging** enabled on your Android device
4. Device connected via USB or running emulator

## Installation 🛠️

1. Clone the repository:
```bash
git clone https://github.com/chrisaydat/android-perf-tester.git
cd android-perf-tester
```

2. Install dependencies (optional - tool works without them):
```bash
pip install -r requirements.txt
```

## Quick Start 🏃‍♂️

### Basic Usage

```bash
# Test a specific app
python main.py com.example.yourapp

# Test the currently active app
python main.py --current

# List all installed packages
python main.py --list
```

### Test Profiles

```bash
# Quick test (CPU & Memory only)
python main.py com.example.app --quick

# Full test (all metrics including battery & network)
python main.py com.example.app --full

# UI-focused test (frames, startup, memory)
python main.py com.example.app --ui-focus
```

### Custom Configuration

Create a `config.json` file:

```json
{
  "cpu": true,
  "memory": true,
  "frames": true,
  "startup": true,
  "battery": false,
  "network": false,
  "screenshot": true,
  "cpu_duration": 10,
  "frame_duration": 10,
  "cold_start": true
}
```

Then run:
```bash
python main.py com.example.app --config config.json
```

## Output 📊

The tool generates:

1. **Raw data file** - Complete measurement data in JSON format
2. **Analysis file** - Processed metrics with insights and recommendations
3. **Console summary** - Quick overview with emoji indicators

Example output structure:
```
results/
├── com.example.app_raw_20240115_143022.json
├── com.example.app_analysis_20240115_143022.json
└── screenshot_com.example.app_test_complete_20240115_143022.png
```

## Understanding the Results 📈

### Performance Score (0-100)
- **80-100**: Excellent 🌟
- **60-79**: Good ✅
- **40-59**: Needs Improvement ⚠️
- **0-39**: Poor ❌

### Key Metrics

1. **CPU Usage**
   - Good: < 30% average
   - Warning: 30-60%
   - Critical: > 60%

2. **Memory (PSS)**
   - Good: < 100MB
   - Warning: 100-200MB
   - Critical: > 200MB

3. **UI Jank Rate**
   - Good: < 5% janky frames
   - Warning: 5-10%
   - Critical: > 10%

4. **Startup Time**
   - Good: < 1 second
   - Warning: 1-2 seconds
   - Critical: > 2 seconds

## Advanced Features 🔧

### Compare Results
```bash
# Compare multiple test results
python main.py --compare results/test1.json results/test2.json
```

### Performance History
```bash
# Show performance trends
python main.py com.example.app --history
```

### Custom Test Duration
```bash
# Longer CPU monitoring (20 seconds)
python main.py com.example.app --cpu-duration 20

# Extended frame analysis (15 seconds)
python main.py com.example.app --frame-duration 15
```

## Project Structure 📁

```
android-perf-tester/
├── adb_commands.py       # ADB wrapper module
├── data_collector.py     # Performance data collection
├── data_processor.py     # Data analysis and insights
├── main.py              # Main entry point
├── requirements.txt     # Optional dependencies
├── README.md           # This file
└── results/            # Output directory (auto-created)
```

## Next Steps 🎯

1. **HTML Report Generator** - Coming soon!
2. **Continuous Monitoring** - Run tests periodically
3. **CI/CD Integration** - Automate performance testing
4. **Custom Metrics** - Add your own measurements

## Troubleshooting 🔍

### "ADB not found"
- Install Android SDK Platform Tools
- Add to PATH: `export PATH=$PATH:/path/to/platform-tools`

### "No device connected"
- Enable USB debugging on device
- Check connection: `adb devices`
- Restart ADB: `adb kill-server && adb start-server`

### "Package not found"
- Verify package name: `adb shell pm list packages | grep yourapp`
- Ensure app is installed

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments 🙏

- Android Debug Bridge (ADB) for making this possible
- The Android development community for performance best practices

---

Made with ❤️ for Android developers who care about performance

# Contributing

We welcome contributions of all sizes.

Ways to contribute:

- Bug reports
- Feature requests
- Documentation improvements
- Performance metric enhancements
- New report formats

# Test a specific package
python android_perf_tester.py com.example.myapp

# Test the currently active app
python android_perf_tester.py

# List all installed packages
python android_perf_tester.py --list-packages

# Skip startup time measurement
python android_perf_tester.py com.example.myapp --no-startup

# Specify output directory
python android_perf_tester.py com.example.myapp --output my_results
