#!/usr/bin/env python3
"""
Diagnostic script to investigate spurious columns in CSV output.
Specifically tests the suspected problematic URLs to capture raw LLM responses.
"""

import asyncio
import json
import os
from pathlib import Path
from page_tracker import AiParser
from datetime import datetime

# Problematic URLs identified from pipeline log
PROBLEMATIC_URLS = [
    "https://www.nvenergy.com/about-nvenergy/news/news-releases/nv-energy-announces-largest-clean-energy-investment-in-nevadas-history",
    "https://pv-magazine-usa.com/2018/06/01/buffett-buys-a-gigawatt-of-solar-power-and-400-mwh-of-energy-storage-maybe/",
    "https://www.nexteraenergyresources.com/dodge-flat-II-solar.html"
]

# Test configuration
PROJECT_NAME = "Dodge Flat"
API_KEY = os.environ.get('CBORG_API_KEY')
API_URL = "https://api.cborg.lbl.gov"
MODEL = 'lbl/llama'

# Load test prompt
prompt_dir = Path(__file__).resolve().parent / 'test_prompts'
prompt_file = prompt_dir / 'solar-projects-priority-prompt1.txt'

async def capture_raw_responses():
    """Capture and analyze raw LLM responses for problematic URLs."""
    
    if not API_KEY:
        print("ERROR: CBORG_API_KEY not found in environment")
        return
    
    if not prompt_file.exists():
        print(f"ERROR: Prompt file not found: {prompt_file}")
        return
    
    # Read the prompt template
    with open(prompt_file, 'r') as f:
        prompt_template = f.read()
    
    # Replace PROJECT placeholder
    prompt = prompt_template.replace('${PROJECT}', PROJECT_NAME)
    
    print(f"=== DIAGNOSTIC SCRIPT START ===")
    print(f"Project: {PROJECT_NAME}")
    print(f"Testing {len(PROBLEMATIC_URLS)} URLs")
    print(f"Timestamp: {datetime.now()}")
    print()
    
    # Create parser instance
    parser = AiParser(
        api_key=API_KEY,
        api_url=API_URL,
        model=MODEL,
        prompt=prompt,
        project_name=PROJECT_NAME
    )
    
    try:
        await parser.initialize()
        
        for i, url in enumerate(PROBLEMATIC_URLS, 1):
            print(f"=== URL {i}/{len(PROBLEMATIC_URLS)} ===")
            print(f"URL: {url}")
            print()
            
            try:
                # Get the raw response before any processing
                result = await parser.select_article_to_api(url, include_url=True)
                
                if result is None:
                    print("❌ No result returned")
                    print()
                    continue
                
                print("✅ Raw LLM Response Structure:")
                print(f"Type: {type(result)}")
                print(f"Keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
                print()
                
                # Pretty print the full JSON structure
                print("📋 Full JSON Response:")
                print(json.dumps(result, indent=2, default=str))
                print()
                
                # Analyze the structure
                if isinstance(result, dict):
                    for url_key, data in result.items():
                        print(f"🔍 Analysis for URL: {url_key}")
                        if isinstance(data, dict):
                            print(f"  - Data type: dictionary")
                            print(f"  - Keys found: {list(data.keys())}")
                            
                            # Check if any keys look like project names
                            potential_project_keys = []
                            for key in data.keys():
                                if any(word in key.lower() for word in ['solar', 'energy', 'center', 'project', 'flat', 'dodge']):
                                    potential_project_keys.append(key)
                            
                            if potential_project_keys:
                                print(f"  - Potential project name keys: {potential_project_keys}")
                                
                                # Check if these contain nested data
                                for proj_key in potential_project_keys:
                                    if isinstance(data[proj_key], dict):
                                        print(f"    - '{proj_key}' contains nested data: {list(data[proj_key].keys())}")
                            else:
                                print(f"  - No obvious project name keys detected")
                        else:
                            print(f"  - Data type: {type(data)}")
                print()
                print("-" * 80)
                print()
                
            except Exception as e:
                print(f"❌ Error processing URL: {e}")
                print()
                continue
    
    finally:
        await parser.close()
    
    print("=== DIAGNOSTIC SCRIPT COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(capture_raw_responses())