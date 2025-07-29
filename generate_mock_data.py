#!/usr/bin/env python3
"""
Generate mock Excel data for stress testing the semaphore implementation.
Creates realistic test data with hundreds of projects and thousands of URLs.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def generate_mock_excel_data(num_projects=100, urls_per_project_range=(10, 50), output_path="mock_stress_test.xlsx"):
    """
    Generate mock Excel data for testing semaphore implementation.
    
    Args:
        num_projects: Number of projects to create
        urls_per_project_range: Tuple of (min, max) URLs per project
        output_path: Path to save the Excel file
    """
    
    # Generate realistic project names
    project_prefixes = ["Solar Farm", "PV Project", "Renewable Energy", "Green Power", "SunTech", "EcoSolar"]
    locations = ["CA", "TX", "FL", "AZ", "NV", "NM", "CO", "NC", "NY", "OR"]
    
    project_names = []
    for i in range(num_projects):
        prefix = np.random.choice(project_prefixes)
        location = np.random.choice(locations)
        number = np.random.randint(1000, 9999)
        project_names.append(f"{prefix} {location}-{number}")
    
    # Generate mock URLs (realistic but fake)
    base_domains = [
        "solarpower.gov",
        "renewableenergy.org", 
        "greentechdb.com",
        "solardatabase.net",
        "cleanenergyportal.gov",
        "pvprojects.info"
    ]
    
    url_data = {}
    total_urls = 0
    
    for project_name in project_names:
        # Random number of URLs per project
        num_urls = np.random.randint(urls_per_project_range[0], urls_per_project_range[1] + 1)
        urls = []
        
        for j in range(num_urls):
            domain = np.random.choice(base_domains)
            page_id = np.random.randint(10000, 99999)
            urls.append(f"https://{domain}/project/{page_id}")
        
        # Pad with NaN to make all columns same length
        max_urls = urls_per_project_range[1]
        while len(urls) < max_urls:
            urls.append(np.nan)
            
        url_data[project_name] = urls
        total_urls += num_urls
    
    # Create DataFrame
    df = pd.DataFrame(url_data)
    
    # Create Excel writer and save
    output_path = Path(output_path)
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='urls', index=False)
    
    print(f"✓ Generated mock data:")
    print(f"  - Projects: {num_projects}")
    print(f"  - Total URLs: {total_urls}")
    print(f"  - Average URLs per project: {total_urls/num_projects:.1f}")
    print(f"  - Saved to: {output_path}")
    
    return output_path

def generate_small_test_data():
    """Generate small dataset for quick testing (10 projects)."""
    return generate_mock_excel_data(
        num_projects=10,
        urls_per_project_range=(5, 15),
        output_path="mock_small_test.xlsx"
    )

def generate_medium_test_data():
    """Generate medium dataset for semaphore testing (100 projects)."""
    return generate_mock_excel_data(
        num_projects=100,
        urls_per_project_range=(10, 30),
        output_path="mock_medium_test.xlsx"
    )

def generate_large_stress_test_data():
    """Generate large dataset for stress testing (500 projects)."""
    return generate_mock_excel_data(
        num_projects=500,
        urls_per_project_range=(20, 100),
        output_path="mock_large_stress_test.xlsx"
    )

if __name__ == "__main__":
    print("Generating mock test datasets...")
    
    # Generate different sizes for testing
    small_file = generate_small_test_data()
    medium_file = generate_medium_test_data()
    large_file = generate_large_stress_test_data()
    
    print(f"\n✓ All mock datasets generated:")
    print(f"  - Small (10 projects): {small_file}")
    print(f"  - Medium (100 projects): {medium_file}")
    print(f"  - Large (500 projects): {large_file}")
    
    print(f"\nTo test semaphore implementation:")
    print(f"  1. Start with small dataset: python main.py (modify excel_path to use {small_file})")
    print(f"  2. Monitor logs for semaphore acquisition/release messages")
    print(f"  3. Verify concurrent project count stays ≤ 50")