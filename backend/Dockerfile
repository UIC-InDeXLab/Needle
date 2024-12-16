FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

# Set the working directory
WORKDIR /app

# Set a cache directory for torch/timm models
ENV TORCH_HOME=/app/.cache/torch/hub

# Copy requirements and model definitions first
COPY requirements.txt config.json download_weights.py ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download model weights by reading from config.json
# This assumes "image_embedders" is a list of objects with a "model_name" field
RUN python download_weights.py

# Copy the rest of the application code
COPY . .

# Expose the port for FastAPI
EXPOSE 8000

# Start the app with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
