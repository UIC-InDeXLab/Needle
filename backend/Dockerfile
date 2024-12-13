FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make the CLI executable and place it in /usr/local/bin
RUN chmod +x needlectl && cp needlectl /usr/local/bin/


# Expose the port for FastAPI
EXPOSE 8000

# Start the app with uvicorn
CMD ["needlectl",  "--install-completion"]
CMD ["source", "~/.bashrc"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
