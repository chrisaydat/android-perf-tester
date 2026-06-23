# Android Perf Tester v2

A CI-ready Android performance testing tool for QA engineers.

Android Perf Tester uses ADB to collect CPU, memory, frame rendering, startup, battery, and network signals, then turns them into threshold results, regression comparisons, exit codes, JSON artifacts, and HTML reports that work locally and in CI/CD.

## What It Is For

- Pre-merge performance smoke checks
- Nightly performance suites
- Release-candidate validation
- Regression detection between builds
- Shareable QA evidence for developers and release owners

The main CI contract is:

```bash
python main.py run com.example.app \
  --scenario checkout \
  --threshold-config perf.thresholds.json \
  --baseline results/baseline.json \
  --output results/perf \
  --fail-on threshold,regression \
  --ci
```

## Prerequisites

1. Python 3.8+
2. Android SDK Platform Tools
3. `adb` available on your `PATH`
4. A connected Android device or running emulator
5. USB debugging enabled for physical devices

Install optional dependencies:

```bash
python -m pip install -r requirements.txt
```

The core CLI works with the Python standard library. Optional packages improve future reporting and terminal output.

## Quick Start

Check the environment:

```bash
python main.py doctor
python main.py doctor com.example.app
```

Run one scenario:

```bash
python main.py run com.example.app --scenario login-smoke
```

Run a quick local test:

```bash
python main.py run com.example.app --quick
```

Run the currently focused app:

```bash
python main.py run --current --ui-focus
```

Generate an HTML report from an existing analysis file:

```bash
python main.py report \
  --input results/com.example.app_checkout_analysis_20260515_093000.json \
  --output results/report
```

## Commands

| Command | Purpose |
|---|---|
| `doctor` | Validate ADB, device, package, launch activity, and metric readiness |
| `run` | Run one performance scenario |
| `suite` | Run multiple scenarios from a JSON suite file |
| `compare` | Compare current analysis JSON against a baseline |
| `report` | Generate an HTML report from analysis JSON |

Legacy commands still work:

```bash
python main.py com.example.app --quick
python main.py com.example.app --full
python main.py --list
python main.py --compare results/baseline.json results/current.json
```

## Scenario Suite Config

Create `perf.suite.json`:

```json
{
  "app": "com.example.app",
  "output": "results/perf",
  "scenarios": [
    {
      "name": "checkout",
      "metrics": ["cpu", "memory", "frames", "startup"],
      "cpu_duration": 30,
      "frame_duration": 30,
      "cold_start": true
    },
    {
      "name": "home-scroll",
      "metrics": ["cpu", "memory", "frames"],
      "cpu_duration": 60,
      "frame_duration": 60
    }
  ]
}
```

Run it:

```bash
python main.py suite \
  --config perf.suite.json \
  --threshold-config perf.thresholds.json \
  --fail-on threshold,regression
```

## Thresholds

Use `--threshold-config` for repeatable QA gates:

```json
{
  "defaults": {
    "failOnMissingMetric": true,
    "regressionTolerancePercent": 10
  },
  "scenarios": {
    "checkout": {
      "cpu.average": { "warn": 35, "fail": 45 },
      "cpu.max": { "warn": 70, "fail": 85 },
      "memory.total_pss_mb": { "warn": 400, "fail": 500 },
      "frames.jank_percentage": { "warn": 3, "fail": 5 },
      "frames.percentiles.p95": { "warn": 24, "fail": 32 },
      "startup.average_ms": { "warn": 1500, "fail": 1800 }
    }
  }
}
```

Run with thresholds:

```bash
python main.py run com.example.app \
  --scenario checkout \
  --threshold-config perf.thresholds.json \
  --fail-on threshold \
  --ci
```

Use inline one-off thresholds:

```bash
python main.py run com.example.app \
  --fail-if "cpu.average > 45" \
  --fail-if "frames.jank_percentage > 5" \
  --fail-on threshold
```

Supported MVP threshold fields:

| Metric path | Meaning |
|---|---|
| `cpu.average` | Average app CPU percentage |
| `cpu.max` | Maximum app CPU percentage |
| `memory.total_pss_mb` | Total PSS memory in MB |
| `frames.jank_percentage` | Janky frame percentage |
| `frames.percentiles.p95` | 95th percentile frame time in ms |
| `startup.average_ms` | Average startup time in ms |

## Regression Detection

Compare current results with a baseline:

```bash
python main.py compare \
  --current results/current_analysis.json \
  --baseline results/baseline_analysis.json \
  --tolerance-percent 10 \
  --fail-on regression
```

Use regression checks during a run:

```bash
python main.py run com.example.app \
  --scenario checkout \
  --baseline results/baseline_analysis.json \
  --threshold-config perf.thresholds.json \
  --fail-on threshold,regression \
  --ci
```

Regression logic treats CPU, memory, startup, jank, and frame time as lower-is-better. A metric fails when the current value is worse than baseline by more than the configured tolerance.

## CI/CD Usage

### GitHub Actions

```yaml
name: Android performance

on:
  pull_request:
  workflow_dispatch:

jobs:
  perf:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run performance gate
        run: |
          python main.py run com.example.app \
            --scenario checkout \
            --threshold-config perf.thresholds.json \
            --baseline results/baseline_analysis.json \
            --output results/perf \
            --fail-on threshold,regression \
            --ci

      - name: Upload performance artifacts
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: android-performance-report
          path: results/perf
```

### Jenkins

```groovy
pipeline {
  agent any

  stages {
    stage('Android Performance') {
      steps {
        sh '''
          python main.py suite \
            --config perf.suite.json \
            --threshold-config perf.thresholds.json \
            --baseline results/baseline_analysis.json \
            --output results/perf \
            --fail-on threshold,regression
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: 'results/perf/**', allowEmptyArchive: true
          publishHTML target: [
            reportDir: 'results/perf',
            reportFiles: '**/index.html',
            reportName: 'Android Performance Report'
          ]
        }
      }
    }
  }
}
```

## Exit Codes

| Code | Meaning |
|---:|---|
| `0` | Passed |
| `1` | Completed with warnings |
| `2` | Threshold or missing-metric failure |
| `3` | Regression failure |
| `10` | Device/setup failure |
| `11` | App launch failure |
| `12` | Metric collection failure |
| `20` | Invalid config or CLI usage |

If both threshold and regression failures happen, threshold failure exits first with code `2`.

## Output Artifacts

Each `run` writes:

```text
results/
├── com.example.app_checkout_raw_20260515_093000.json
├── com.example.app_checkout_analysis_20260515_093000.json
└── com.example.app_checkout_report_20260515_093000/
    ├── index.html
    └── assets/
        ├── styles.css
        └── charts.js
```

How to read the report:

| Status | Meaning |
|---|---|
| `PASS` | Metric is inside target |
| `WARN` | Metric should be reviewed but does not block unless your process treats warnings as blockers |
| `FAIL` | Metric exceeded a configured gate |
| `MISSING` | Metric was not available or was not collected |

## Local Debugging Workflow

1. Check setup:

```bash
python main.py doctor com.example.app
```

2. Run a focused test:

```bash
python main.py run com.example.app --ui-focus --scenario home-scroll
```

3. Compare against a known good run:

```bash
python main.py compare \
  --current results/current_analysis.json \
  --baseline results/good_analysis.json
```

4. Open the generated `index.html` report from the output directory.

## Troubleshooting

### ADB not found

Install Android SDK Platform Tools and add them to `PATH`:

```bash
export PATH="$PATH:/path/to/platform-tools"
```

### No device connected

```bash
adb devices
adb kill-server
adb start-server
adb devices
```

For physical devices, confirm USB debugging and the device trust prompt.

### Package not installed

```bash
adb shell pm list packages | grep example
```

Install the APK or correct the package name.

### App launch failure

Run:

```bash
python main.py doctor com.example.app
```

If the launch activity cannot be resolved, check the app manifest and package name.

### Missing metrics

Missing metrics usually mean the scenario skipped that metric, the app did not render frames during the capture window, or ADB returned an unexpected `dumpsys` format. Use `--full` once to confirm the collector can read every metric.

### Flaky emulator/device behavior

Use a stable emulator image, keep only one target device connected for CI, reset app state before scenarios, and archive raw JSON plus HTML reports for failed runs.

## Development

Run tests with the standard library test runner:

```bash
python -m unittest discover -s tests -v
```

Compile-check the CLI:

```bash
python -m py_compile main.py src/*.py
```
