#!/usr/bin/env python3
"""
Script to build sample-queries.json by querying the Needle API
and copying the resulting images to the demo directory.
"""

import requests
import json
import os
import shutil
import base64
from pathlib import Path
import time

# Configuration
API_BASE_URL = "http://127.0.0.1:8000"
DEMO_DIR = Path(__file__).parent.parent
DEMO_IMAGES_DIR = DEMO_DIR / "public" / "demo-images"
SAMPLE_QUERIES_FILE = DEMO_DIR / "src" / "sample-queries.json"

# Sample queries to test
SAMPLE_QUERIES = [
    "a cat with a cute hat",
    "mountain landscape", 
    "coca cola advertising car",
    "birthday cake with candles",
    "broccoli pasta",
    "city skyline in the autumn",
    "two cats watching a dog on tv",
    "people watching a movie in a theater",
]

def ensure_demo_images_dir():
    """Create the demo images directory if it doesn't exist."""
    DEMO_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✅ Created demo images directory: {DEMO_IMAGES_DIR}")

def make_api_request(endpoint, data):
    """Make a POST request to the API."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return None

def query_api(query_text):
    """Query the API with a text query and return results."""
    print(f"🔍 Querying: '{query_text}'")
    
    # Step 1: Create query
    query_data = {"q": query_text}
    query_response = make_api_request("/query", query_data)
    if not query_response:
        return None
    
    qid = query_response.get("qid")
    print(f"   📝 Got QID: {qid}")
    
    # Step 2: Search for images
    search_data = {
        "qid": qid,
        "num_images_to_retrieve": 12,
        "include_base_images_in_preview": True,
        "verbose": False,
        "generation_config": {
            "engines": [{"name": "SDTurbo", "params": {"additionalProp1": {}}}],
            "num_engines_to_use": 1,
            "num_images": 1,
            "image_size": "SMALL",
            "use_fallback": True
        }
    }
    
    search_response = make_api_request("/search", search_data)
    if not search_response:
        return None
    
    print(f"   🖼️  Found {len(search_response.get('results', []))} images")
    return search_response

def copy_image_to_demo(source_path, dest_filename):
    """Copy an image from the dataset to the demo images directory."""
    source_path = Path(source_path)
    dest_path = DEMO_IMAGES_DIR / dest_filename
    
    try:
        if source_path.exists():
            shutil.copy2(source_path, dest_path)
            print(f"   📋 Copied: {source_path.name} -> {dest_filename}")
            return True
        else:
            print(f"   ⚠️  Source image not found: {source_path}")
            return False
    except Exception as e:
        print(f"   ❌ Failed to copy {source_path.name}: {e}")
        return False

def save_base64_image(base64_data, filename):
    """Save a base64 encoded image to the demo images directory."""
    try:
        # Remove data URL prefix if present
        if base64_data.startswith('data:image'):
            base64_data = base64_data.split(',')[1]
        
        image_data = base64.b64decode(base64_data)
        dest_path = DEMO_IMAGES_DIR / filename
        
        with open(dest_path, 'wb') as f:
            f.write(image_data)
        
        print(f"   💾 Saved generated image: {filename}")
        return True
    except Exception as e:
        print(f"   ❌ Failed to save generated image {filename}: {e}")
        return False

def build_sample_queries():
    """Build the complete sample-queries.json file."""
    print("🚀 Building sample-queries.json from Needle API...")
    
    # Ensure demo images directory exists
    ensure_demo_images_dir()
    
    queries_data = []
    
    for i, query_text in enumerate(SAMPLE_QUERIES, 1):
        print(f"\n📝 Processing query {i}/{len(SAMPLE_QUERIES)}")
        
        # Query the API
        api_response = query_api(query_text)
        if not api_response:
            print(f"   ❌ Skipping query due to API error")
            continue
        
        # Extract data from API response
        results = api_response.get("results", [])
        base_images = api_response.get("base_images", "[]")[0]
        
        if not results:
            print(f"   ⚠️  No results for query: {query_text}")
            continue
        
        # Create query entry
        query_id = f"query_{i}"
        query_entry = {
            "id": query_id,
            "text": query_text,
        "generatedImage": {
            "url": f"/Needle/demo/demo-images/{query_id}_generated.jpg",
            "prompt": query_text
        },
            "results": []
        }
        
        # Save generated image (base64)
        if base_images:
            generated_filename = f"{query_id}_generated.jpg"
            save_base64_image(base_images, generated_filename)
        
        # Copy result images and create result entries
        for j, image_path in enumerate(results[:12], 1):  # Take first 12 results
            result_filename = f"{query_id}_{j:03d}.jpg"
            
            # Copy the image
            if copy_image_to_demo(image_path, result_filename):
                # Calculate similarity score (mock for now - you could implement real similarity)
                similarity = max(0.65, 0.95 - (j * 0.025))  # Decreasing similarity for 12 results
                
                result_entry = {
                    "id": f"img_{i}_{j}",
                    "url": f"/Needle/demo/demo-images/{result_filename}",
                    "filename": result_filename,
                    "similarity": round(similarity, 2)
                }
                
                query_entry["results"].append(result_entry)
        
        queries_data.append(query_entry)
        print(f"   ✅ Processed query with {len(query_entry['results'])} results")
        
        # Small delay to avoid overwhelming the API
        time.sleep(1)
    
    # Create final JSON structure
    final_data = {
        "queries": queries_data
    }
    
    # Write to file
    try:
        with open(SAMPLE_QUERIES_FILE, 'w') as f:
            json.dump(final_data, f, indent=2)
        
        print(f"\n🎉 Successfully created {SAMPLE_QUERIES_FILE}")
        print(f"   📊 Total queries: {len(queries_data)}")
        print(f"   🖼️  Images saved to: {DEMO_IMAGES_DIR}")
        
        # Show summary
        total_images = sum(len(q["results"]) for q in queries_data)
        print(f"   📈 Total result images: {total_images}")
        
    except Exception as e:
        print(f"❌ Failed to write sample-queries.json: {e}")

def main():
    """Main function."""
    print("🔧 Needle Demo Sample Queries Builder")
    print("=" * 50)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Needle API is running")
        else:
            print("⚠️  Needle API responded with non-200 status")
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to Needle API. Make sure it's running on http://127.0.0.1:8000")
        return
    
    # Build the sample queries
    build_sample_queries()

if __name__ == "__main__":
    main()
