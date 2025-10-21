# Demo Scripts

This directory contains scripts to build and customize the Needle demo.

## Scripts

### `build-sample-queries.py`

Builds the `sample-queries.json` file by querying your running Needle API and copying the resulting images.

**Prerequisites:**
- Needle backend running on `http://127.0.0.1:8000`
- Python 3 with `requests` library installed

**Usage:**
```bash
# Make sure your Needle backend is running first
cd demo
python3 scripts/build-sample-queries.py
```

Or use the convenience script:
```bash
cd demo
./scripts/run-build.sh
```

**What it does:**
1. Queries the Needle API with predefined sample queries
2. Gets generated images and similar image results
3. Copies images from your dataset to `public/demo-images/`
4. Saves generated images from base64 data
5. Creates the final `src/sample-queries.json` file

**Sample Queries:**
- "a cute cat with a red hat"
- "mountain landscape"
- "coca cola advertising car"
- "happy birthday to youuu!"
- "broccoli pasta"
- "two cats watching a dog on tv"

### `run-build.sh`

Convenience script to run the sample queries builder.

## Customization

To add your own queries, edit the `SAMPLE_QUERIES` list in `build-sample-queries.py`:

```python
SAMPLE_QUERIES = [
    "your custom query 1",
    "your custom query 2",
    # ... add more queries
]
```

## Output

The script creates:
- `src/sample-queries.json` - The demo data file
- `public/demo-images/` - Directory with all the images
  - `query_X_generated.jpg` - AI-generated images
  - `query_X_001.jpg` to `query_X_012.jpg` - Similar images from dataset (12 results per query)
