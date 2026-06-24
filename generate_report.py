#!/usr/bin/env python3
"""
Generate HTML reports from Android Performance Tester results
"""

import os
import sys
from src.report_generator import generate_report, generate_report_from_console


def print_usage():
    """Print usage instructions"""
    print("Android Performance Tester - Report Generator")
    print("\nUsage:")
    print("  1. Generate report from JSON files:")
    print("     python generate_report.py json <raw_data.json> <analysis_data.json> [output_dir]")
    print("\n  2. Generate report from console output:")
    print("     python generate_report.py console <console_output.txt> [output_dir]")
    print("\n  3. Generate reports for all results in a directory:")
    print("     python generate_report.py batch <results_dir> [output_dir]")


def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print_usage()
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "json":
        if len(sys.argv) < 4:
            print("Error: Missing analysis file")
            print_usage()
            return 1
        
        raw_file = sys.argv[2]
        analysis_file = sys.argv[3]
        output_dir = sys.argv[4] if len(sys.argv) > 4 else "reports"
        
        if not os.path.exists(raw_file):
            print(f"Error: Raw data file not found: {raw_file}")
            return 1
        
        if not os.path.exists(analysis_file):
            print(f"Error: Analysis file not found: {analysis_file}")
            return 1
        
        report_path = generate_report(raw_file, analysis_file, output_dir)
        print(f"Report generated: {report_path}")
        return 0
    
    elif command == "console":
        console_file = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else "reports"
        
        if not os.path.exists(console_file):
            print(f"Error: Console output file not found: {console_file}")
            return 1
        
        with open(console_file, 'r') as f:
            console_output = f.read()
        
        report_path = generate_report_from_console(console_output, output_dir)
        print(f"Report generated: {report_path}")
        return 0
    
    elif command == "batch":
        results_dir = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else "reports"
        
        if not os.path.exists(results_dir):
            print(f"Error: Results directory not found: {results_dir}")
            return 1
        
        # Find all raw data files
        raw_files = []
        for filename in os.listdir(results_dir):
            if "_raw_" in filename and filename.endswith(".json"):
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
                report_path = generate_report(raw_file, analysis_file, output_dir)
                print(f"Report generated: {report_path}")
                success_count += 1
            except Exception as e:
                print(f"Error generating report for {raw_file}: {e}")
        
        print(f"Generated {success_count} reports in {output_dir}")
        return 0 if success_count > 0 else 1
    
    else:
        print(f"Unknown command: {command}")
        print_usage()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 