#!/usr/bin/env python3
"""
Android Performance Tester - Report CLI
Command-line interface for generating HTML reports
"""

import argparse
import os
import sys
from typing import List, Optional

from src.report_generator import generate_report, generate_report_from_console


def main():
    """Main entry point for the report CLI"""
    parser = argparse.ArgumentParser(
        description="Android Performance Tester - Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --json results/com.example.app_raw_20250522_171905.json results/com.example.app_analysis_20250522_171905.json
  %(prog)s --console output.txt
  %(prog)s --batch results/ --output reports/
        """
    )
    
    # Create subparsers for different modes
    subparsers = parser.add_subparsers(dest="command", help="Report generation mode")
    
    # JSON report parser
    json_parser = subparsers.add_parser("json", help="Generate report from JSON files")
    json_parser.add_argument("raw_file", help="Path to raw data JSON file")
    json_parser.add_argument("analysis_file", help="Path to analysis data JSON file")
    
    # Console report parser
    console_parser = subparsers.add_parser("console", help="Generate report from console output")
    console_parser.add_argument("console_file", help="Path to console output file")
    
    # Batch report parser
    batch_parser = subparsers.add_parser("batch", help="Generate reports for all results in a directory")
    batch_parser.add_argument("results_dir", help="Directory containing results files")
    
    # Common arguments
    for p in [json_parser, console_parser, batch_parser]:
        p.add_argument("--output", "-o", default="reports", help="Output directory for reports")
        p.add_argument("--templates", "-t", default="templates", help="Templates directory")
    
    # Backwards compatibility with old CLI style
    parser.add_argument("--json", nargs=2, metavar=("RAW_FILE", "ANALYSIS_FILE"), 
                      help="Generate report from JSON files (legacy mode)")
    parser.add_argument("--console", metavar="CONSOLE_FILE", 
                      help="Generate report from console output (legacy mode)")
    parser.add_argument("--batch", metavar="RESULTS_DIR", 
                      help="Generate reports for all results in directory (legacy mode)")
    parser.add_argument("--output", "-o", default="reports", 
                      help="Output directory for reports (legacy mode)")
    parser.add_argument("--templates", "-t", default="templates", 
                      help="Templates directory (legacy mode)")
    
    args = parser.parse_args()
    
    # Handle legacy mode arguments
    if args.json:
        args.command = "json"
        args.raw_file = args.json[0]
        args.analysis_file = args.json[1]
    elif args.console:
        args.command = "console"
        args.console_file = args.console
    elif args.batch:
        args.command = "batch"
        args.results_dir = args.batch
    
    # Execute the appropriate command
    if args.command == "json":
        return generate_json_report(args.raw_file, args.analysis_file, args.output, args.templates)
    elif args.command == "console":
        return generate_console_report(args.console_file, args.output, args.templates)
    elif args.command == "batch":
        return generate_batch_reports(args.results_dir, args.output, args.templates)
    else:
        parser.print_help()
        return 1


def generate_json_report(raw_file: str, analysis_file: str, output_dir: str, template_dir: str) -> int:
    """Generate a report from JSON files"""
    try:
        if not os.path.exists(raw_file):
            print(f"Error: Raw data file not found: {raw_file}")
            return 1
        
        if not os.path.exists(analysis_file):
            print(f"Error: Analysis file not found: {analysis_file}")
            return 1
        
        report_path = generate_report(raw_file, analysis_file, output_dir, template_dir)
        print(f"Report generated: {report_path}")
        return 0
    
    except Exception as e:
        print(f"Error generating report: {e}")
        return 1


def generate_console_report(console_file: str, output_dir: str, template_dir: str) -> int:
    """Generate a report from console output file"""
    try:
        if not os.path.exists(console_file):
            print(f"Error: Console output file not found: {console_file}")
            return 1
        
        with open(console_file, 'r') as f:
            console_output = f.read()
        
        report_path = generate_report_from_console(console_output, output_dir, template_dir)
        print(f"Report generated: {report_path}")
        return 0
    
    except Exception as e:
        print(f"Error generating report: {e}")
        return 1


def generate_batch_reports(results_dir: str, output_dir: str, template_dir: str) -> int:
    """Generate reports for all results in a directory"""
    try:
        if not os.path.exists(results_dir):
            print(f"Error: Results directory not found: {results_dir}")
            return 1
        
        # Find all raw data files
        raw_files = []
        for filename in os.listdir(results_dir):
            if filename.endswith("_raw_" + ".json") or "_raw_" in filename:
                raw_files.append(os.path.join(results_dir, filename))
        
        if not raw_files:
            print(f"No raw data files found in {results_dir}")
            return 1
        
        # Generate reports for each raw file
        success_count = 0
        for raw_file in raw_files:
            # Find corresponding analysis file
            base_name = os.path.basename(raw_file).replace("_raw_", "_analysis_")
            analysis_file = os.path.join(results_dir, base_name)
            
            if not os.path.exists(analysis_file):
                print(f"Warning: Analysis file not found for {raw_file}")
                continue
            
            try:
                report_path = generate_report(raw_file, analysis_file, output_dir, template_dir)
                print(f"Report generated: {report_path}")
                success_count += 1
            except Exception as e:
                print(f"Error generating report for {raw_file}: {e}")
        
        print(f"Generated {success_count} reports in {output_dir}")
        return 0 if success_count > 0 else 1
    
    except Exception as e:
        print(f"Error generating batch reports: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 