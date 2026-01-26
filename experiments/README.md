# Sample Variance Reduction Analysis

This experiment implements a bootstrapping approach to demonstrate that the standard deviation of distance scores decreases as we increase:
- **m**: number of guide images
- **l**: number of embedders

This validates **Theorem 1** from your paper, showing that σ ∝ 1/√m.

## Implementation Overview

### Backend Changes (Minimal)

1. **New Endpoint**: `/variance-analysis/generate-pool`
   - Generates a pool of guide images (M_pool=20) for a query
   - Computes embeddings for all guide images using all available embedders
   - Returns structured data with images and embeddings

2. **New Schemas**: Added to `backend/models/schemas.py`
   - `GeneratePoolRequest`: Request schema
   - `GeneratePoolResponse`: Response schema with guide images and embeddings

### Notebook Implementation

The notebook (`variance_reduction_analysis.ipynb`) implements:

1. **Data Collection**: Generate pools for multiple queries
2. **Bootstrapping**: Sample m images and l embedders, compute distance scores
3. **Analysis**: Calculate standard deviations for different configurations
4. **Visualization**: Plot σ vs m to show the 1/√m decay pattern

## How to Run

### Prerequisites

1. **Backend Running**: Ensure your backend is running on `http://localhost:8000` (or update `BACKEND_URL` in the notebook)

2. **Dependencies**: Install required Python packages:
   ```bash
   pip install numpy matplotlib seaborn requests pandas pillow
   ```

3. **Generator Configuration**: Update the `generation_config` in the notebook's `generate_pool()` function to match your available image generators (e.g., SDTurbo, DALL-E, etc.)

### Step-by-Step Execution

1. **Start the Backend**:
   ```bash
   cd backend
   # Activate your virtual environment if needed
   python main.py
   # Or use your usual backend startup method
   ```

2. **Open the Notebook**:
   ```bash
   cd experiments
   jupyter notebook variance_reduction_analysis.ipynb
   ```

3. **Configure the Experiment**:
   - Update `TEST_QUERIES` with your "Hard Set" queries (e.g., from LVIS or Winoground)
   - Adjust `POOL_SIZE` (default: 20)
   - Adjust `BOOTSTRAP_ITERATIONS` (default: 100)
   - Set `M_VALUES` and `L_VALUES` based on your needs
   - Update `generation_config` in `generate_pool()` to match your generator setup

4. **Run All Cells**: Execute the notebook cells sequentially

### Expected Output

- **Plots**: 
  - `variance_reduction_analysis.png`: Two plots showing σ vs m and σ vs l
  - The first plot should show a 1/√m decay pattern (red dashed line)

- **Results File**: 
  - `variance_analysis_results.json`: JSON file with all numerical results

- **Console Output**: 
  - Progress updates during pool generation
  - Bootstrap analysis results for each query
  - Aggregated statistics

## Methodology Details

### Ground Truth Definition

The ground truth embedding is computed as the **mean of all guide image embeddings** in the pool for each embedder. This represents the "true" embedding that we're trying to estimate.

### Distance Score Calculation

For each bootstrap sample:
1. Randomly sample m guide images from the pool
2. Randomly select l embedders (or use fixed set)
3. For each (image, embedder) pair, compute cosine distance to ground truth
4. Average all distances to get δ_bar

### Bootstrapping

- For each (m, l) configuration:
  - Repeat 100 times (configurable)
  - Each iteration: sample m images, compute distance score
  - Calculate mean and standard deviation of the 100 scores

## Customization

### Using Different Ground Truth

If you want to use a different ground truth (e.g., a manually specified image or the top retrieved result), modify the `compute_ground_truth_embedding()` function in the notebook.

### Adjusting Parameters

- **Pool Size**: Increase `POOL_SIZE` for more robust results (but slower generation)
- **Bootstrap Iterations**: Increase `BOOTSTRAP_ITERATIONS` for more stable statistics
- **Test Queries**: Replace with your actual "Hard Set" queries

### Multiple Queries

The notebook aggregates results across multiple queries to get more robust statistics. You can:
- Add more queries to `TEST_QUERIES`
- Adjust the aggregation method in `aggregate_results()`

## Troubleshooting

### Backend Connection Issues

- Check that backend is running: `curl http://localhost:8000/health`
- Verify `BACKEND_URL` in the notebook matches your backend address

### Generator Errors

- Ensure your generator configuration in `generate_pool()` matches available generators
- Check generator service is running and accessible
- Verify generator authentication parameters if needed

### Embedder Issues

- The notebook automatically detects available embedders from the API response
- If you have fewer than expected embedders, adjust `L_VALUES` accordingly

## Expected Results

The experiment should demonstrate:

1. **Varying m (fixing l)**: Standard deviation decreases as 1/√m
   - Plot should show exponential decay
   - Theoretical curve (red dashed line) should match observed data

2. **Varying l (fixing m)**: Standard deviation decreases with more embedders
   - More embedders provide better averaging and lower variance

## Files

- `variance_reduction_analysis.ipynb`: Main analysis notebook
- `README.md`: This file
- `variance_reduction_analysis.png`: Generated plot (after running)
- `variance_analysis_results.json`: Generated results (after running)

## Notes

- The first run will take time to generate all guide images (20 per query)
- Subsequent runs can reuse the pools if you save them
- The bootstrapping analysis is computationally efficient (no new image generation needed)

