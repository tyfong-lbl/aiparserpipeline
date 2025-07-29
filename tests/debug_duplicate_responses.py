#!/usr/bin/env python3
"""
Debug script to identify why we're getting 10 responses per URL instead of expected 6.
"""

import pandas as pd
from pathlib import Path
from collections import Counter
import re

def analyze_csv_log(csv_path):
    """Analyze the pipeline log CSV to understand duplication patterns."""
    print("=== ANALYZING CSV LOG ===")
    
    # Read the CSV
    df = pd.read_csv(csv_path)
    print(f"Total log entries: {len(df)}")
    
    # Count entries per URL
    url_counts = df['URL'].value_counts()
    print(f"\nEntries per URL:")
    for url, count in url_counts.items():
        print(f"  {url}: {count} entries")
    
    # Check for timing patterns that might indicate concurrent processing
    print(f"\nTiming analysis:")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df_sorted = df.sort_values('timestamp')
    
    for url in url_counts.index:
        url_entries = df_sorted[df_sorted['URL'] == url]
        print(f"\n{url}:")
        print(f"  First entry: {url_entries.iloc[0]['timestamp']}")
        print(f"  Last entry: {url_entries.iloc[-1]['timestamp']}")
        
        # Check for rapid-fire entries (potential concurrent processing)
        time_diffs = url_entries['timestamp'].diff().dt.total_seconds().dropna()
        rapid_entries = (time_diffs < 1).sum()  # Less than 1 second apart
        print(f"  Entries < 1 second apart: {rapid_entries}")
    
    return df

def check_prompt_files(prompt_dir):
    """Check the actual prompt files in the directory."""
    print("\n=== ANALYZING PROMPT FILES ===")
    
    prompt_dir = Path(prompt_dir)
    if not prompt_dir.exists():
        print(f"Prompt directory {prompt_dir} does not exist!")
        return
    
    # List all .txt files
    txt_files = list(prompt_dir.glob("*.txt"))
    print(f"Found {len(txt_files)} .txt files:")
    for file in sorted(txt_files):
        print(f"  {file.name}")
    
    # Check for the expected pattern
    priority_prompts = list(prompt_dir.glob("solar-projects-priority-prompt*.txt"))
    other_prompts = [f for f in txt_files if f not in priority_prompts]
    
    print(f"\nPriority prompts (solar-projects-priority-prompt*): {len(priority_prompts)}")
    for file in sorted(priority_prompts):
        print(f"  {file.name}")
    
    print(f"\nOther prompts: {len(other_prompts)}")
    for file in sorted(other_prompts):
        print(f"  {file.name}")
    
    return len(priority_prompts), len(other_prompts)

def simulate_get_all_prompts(prompt_dir, number_of_queries=5, prompt_filename_base='solar-projects-priority-prompt'):
    """Simulate the get_all_prompts() method to see what files it would read."""
    print(f"\n=== SIMULATING get_all_prompts() ===")
    print(f"number_of_queries: {number_of_queries}")
    print(f"prompt_filename_base: {prompt_filename_base}")
    
    prompt_dir = Path(prompt_dir)
    prompt_nums = range(1, number_of_queries + 1)
    prompt_filenames = [Path(prompt_dir, f'{prompt_filename_base}{x}.txt') for x in prompt_nums]
    
    print(f"\nFiles that would be read:")
    existing_files = []
    for i, filepath in enumerate(prompt_filenames, 1):
        exists = filepath.exists()
        print(f"  {i}: {filepath.name} - {'EXISTS' if exists else 'MISSING'}")
        if exists:
            existing_files.append(filepath)
    
    print(f"\nTotal files that would be successfully read: {len(existing_files)}")
    return existing_files

def analyze_url_extraction_logic():
    """Analyze potential issues with URL extraction."""
    print(f"\n=== ANALYZING URL EXTRACTION LOGIC ===")
    
    # The extract_urls method uses regex to find URLs
    url_pattern = re.compile(r'(https?://\S+)')
    
    # Sample test cases that might cause duplication
    test_cases = [
        "https://example.com/page1",
        "https://example.com/page1 https://example.com/page1",  # Duplicate in same cell
        "Visit https://example.com/page1 for more info",
        "https://example.com/page1\nhttps://example.com/page2",  # Multiple URLs
    ]
    
    print("Testing URL extraction with various inputs:")
    for i, test_case in enumerate(test_cases, 1):
        urls = url_pattern.findall(test_case)
        print(f"  Test {i}: '{test_case}' -> {urls}")

def main():
    """Main diagnostic function."""
    print("DEBUGGING: Why are we getting 10 responses per URL instead of 6?")
    print("=" * 60)
    
    # Analyze the CSV log
    csv_path = "diagnostics/pipeline_log_2025-07-07_17-24-28.csv"
    df = analyze_csv_log(csv_path)
    
    # Check prompt files
    prompt_dir = "test_prompts"
    priority_count, other_count = check_prompt_files(prompt_dir)
    
    # Simulate the get_all_prompts method
    existing_files = simulate_get_all_prompts(prompt_dir)
    
    # Analyze URL extraction
    analyze_url_extraction_logic()
    
    # Summary and diagnosis
    print(f"\n=== DIAGNOSIS SUMMARY ===")
    print(f"Expected responses per URL: 6 (based on 6 prompt files)")
    print(f"Actual responses per URL: ~10 (from CSV analysis)")
    print(f"Priority prompt files found: {priority_count}")
    print(f"Other prompt files found: {other_count}")
    print(f"Files that get_all_prompts() would read: {len(existing_files)}")
    
    # Calculate the discrepancy
    total_prompt_files = priority_count + other_count
    expected_from_code = len(existing_files)
    actual_responses = 10  # From CSV analysis
    
    print(f"\nDISCREPANCY ANALYSIS:")
    print(f"  Total prompt files in directory: {total_prompt_files}")
    print(f"  Files read by get_all_prompts(): {expected_from_code}")
    print(f"  Actual responses logged: {actual_responses}")
    print(f"  Excess responses: {actual_responses - expected_from_code}")
    
    if actual_responses > expected_from_code:
        print(f"\nPOSSIBLE CAUSES:")
        print(f"  1. Concurrent processing - same URL processed multiple times simultaneously")
        print(f"  2. Resume/checkpoint logic - URLs being reprocessed")
        print(f"  3. URL extraction returning duplicates")
        print(f"  4. Multiple projects processing same URLs")
        print(f"  5. Pipeline logger creating multiple entries per API call")

if __name__ == "__main__":
    main()