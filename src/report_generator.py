"""
report_generator.py - HTML report generation for Android Perf Tester
"""

import html
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


def _escape(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _badge(status: str) -> str:
    status = (status or "unknown").lower()
    return f'<span class="badge badge-{_escape(status)}">{_escape(status.upper())}</span>'


def _metric_rows(thresholds: Dict[str, Any]) -> str:
    rows = []
    for item in thresholds.get("results", []):
        rows.append(
            "<tr>"
            f"<td>{_escape(item.get('metric'))}</td>"
            f"<td>{_escape(item.get('value'))}</td>"
            f"<td>{_escape(item.get('warn'))}</td>"
            f"<td>{_escape(item.get('fail'))}</td>"
            f"<td>{_badge(item.get('status'))}</td>"
            "</tr>"
        )
    return "\n".join(rows) or '<tr><td colspan="5">No threshold results.</td></tr>'


def _regression_rows(regression: Optional[Dict[str, Any]]) -> str:
    if not regression:
        return '<tr><td colspan="6">No baseline comparison was provided.</td></tr>'
    rows = []
    for item in regression.get("results", []):
        delta_percent = item.get("delta_percent")
        delta_label = "" if delta_percent is None else f"{delta_percent:+.2f}%"
        rows.append(
            "<tr>"
            f"<td>{_escape(item.get('metric'))}</td>"
            f"<td>{_escape(item.get('baseline'))}</td>"
            f"<td>{_escape(item.get('current'))}</td>"
            f"<td>{_escape(item.get('delta'))}</td>"
            f"<td>{_escape(delta_label)}</td>"
            f"<td>{_badge(item.get('status'))}</td>"
            "</tr>"
        )
    return "\n".join(rows) or '<tr><td colspan="6">No comparable metrics.</td></tr>'


def _recommendations(recommendations: Any) -> str:
    if not recommendations:
        return "<p>No recommendations generated.</p>"
    cards = []
    for recommendation in recommendations:
        suggestions = "".join(
            f"<li>{_escape(suggestion)}</li>"
            for suggestion in recommendation.get("suggestions", [])
        )
        cards.append(
            '<article class="recommendation">'
            f"<h3>{_escape(recommendation.get('title'))}</h3>"
            f"<p>{_escape(recommendation.get('category'))} - {_escape(recommendation.get('priority'))}</p>"
            f"<ul>{suggestions}</ul>"
            "</article>"
        )
    return "\n".join(cards)


def generate_html_report(
    report_data: Dict[str, Any],
    output_dir: str,
    raw_file: Optional[str] = None,
    analysis_file: Optional[str] = None,
    filename: str = "index.html",
) -> str:
    os.makedirs(output_dir, exist_ok=True)

    analysis = report_data.get("analysis", {})
    raw_data = report_data.get("raw_data", {})
    summary = report_data.get("summary", {})
    thresholds = report_data.get("thresholds", {})
    regression = report_data.get("regression")
    device = raw_data.get("device_info", {})
    scenario = report_data.get("scenario") or raw_data.get("config", {}).get("scenario") or "default"
    package_name = raw_data.get("package_name") or report_data.get("package_name") or "unknown"

    html_document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Android Perf Report - {_escape(package_name)} / {_escape(scenario)}</title>
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <main class="shell">
    <header class="hero">
      <div>
        <p class="eyebrow">Android Perf Tester v2</p>
        <h1>{_escape(package_name)} / {_escape(scenario)}</h1>
        <p>Generated {_escape(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}</p>
      </div>
      <div class="overall">{_badge(report_data.get('status', 'pass'))}</div>
    </header>

    <section class="cards">
      <article><span>Score</span><strong>{_escape(summary.get('overall_score', analysis.get('overall_score', 'n/a')))}</strong></article>
      <article><span>Thresholds</span><strong>{_escape(thresholds.get('status', 'n/a')).upper()}</strong></article>
      <article><span>Regression</span><strong>{_escape((regression or {}).get('status', 'n/a')).upper()}</strong></article>
      <article><span>Device</span><strong>{_escape(device.get('manufacturer', ''))} {_escape(device.get('model', ''))}</strong></article>
    </section>

    <section>
      <h2>Threshold Results</h2>
      <table>
        <thead><tr><th>Metric</th><th>Value</th><th>Warn</th><th>Fail</th><th>Status</th></tr></thead>
        <tbody>{_metric_rows(thresholds)}</tbody>
      </table>
    </section>

    <section>
      <h2>Regression Diff</h2>
      <table>
        <thead><tr><th>Metric</th><th>Baseline</th><th>Current</th><th>Delta</th><th>Delta %</th><th>Status</th></tr></thead>
        <tbody>{_regression_rows(regression)}</tbody>
      </table>
    </section>

    <section>
      <h2>Recommendations</h2>
      <div class="recommendations">{_recommendations(report_data.get('recommendations'))}</div>
    </section>

    <section>
      <h2>Artifacts</h2>
      <ul>
        <li>Raw JSON: {_escape(raw_file or 'not generated')}</li>
        <li>Analysis JSON: {_escape(analysis_file or 'not generated')}</li>
      </ul>
    </section>
  </main>
  <script id="perf-data" type="application/json">{html.escape(json.dumps(report_data))}</script>
  <script src="assets/charts.js"></script>
</body>
</html>
"""

    assets_dir = os.path.join(output_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    _write_default_assets(assets_dir)

    output_path = os.path.join(output_dir, filename)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(html_document)
    return output_path


def _write_default_assets(assets_dir: str) -> None:
    styles_path = os.path.join(assets_dir, "styles.css")
    charts_path = os.path.join(assets_dir, "charts.js")
    if not os.path.exists(styles_path):
        with open(styles_path, "w", encoding="utf-8") as handle:
            handle.write(DEFAULT_CSS)
    if not os.path.exists(charts_path):
        with open(charts_path, "w", encoding="utf-8") as handle:
            handle.write(DEFAULT_JS)


DEFAULT_CSS = """
:root {
  color-scheme: light;
  --bg: #f7f8fa;
  --text: #172026;
  --muted: #5d6974;
  --line: #dfe4ea;
  --panel: #ffffff;
  --pass: #0f7b45;
  --warn: #a35f00;
  --fail: #b42318;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.shell { max-width: 1120px; margin: 0 auto; padding: 32px 20px 56px; }
.hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; border-bottom: 1px solid var(--line); padding-bottom: 20px; }
.eyebrow { margin: 0 0 6px; color: var(--muted); text-transform: uppercase; font-size: 12px; font-weight: 700; }
h1 { margin: 0; font-size: 32px; letter-spacing: 0; }
h2 { margin-top: 32px; font-size: 20px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 24px 0; }
.cards article, .recommendation { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }
.cards span { display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; font-weight: 700; }
.cards strong { display: block; margin-top: 6px; font-size: 22px; }
table { width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
th, td { padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; }
th { background: #eef2f5; font-size: 12px; text-transform: uppercase; }
.badge { display: inline-block; min-width: 64px; padding: 3px 8px; border-radius: 999px; color: white; text-align: center; font-size: 12px; font-weight: 700; }
.badge-pass { background: var(--pass); }
.badge-warn, .badge-missing { background: var(--warn); }
.badge-fail, .badge-critical { background: var(--fail); }
.badge-n/a, .badge-unknown { background: var(--muted); }
.recommendations { display: grid; gap: 12px; }
"""


DEFAULT_JS = """
(() => {
  const node = document.getElementById("perf-data");
  if (!node) return;
  window.androidPerfReport = JSON.parse(node.textContent || "{}");
})();
"""
