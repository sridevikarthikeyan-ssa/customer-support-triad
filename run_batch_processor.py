"""
run_batch_processor.py
Script to run the batch processor using environment variables from .env file.
"""
import os
import sys
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Print configuration loaded from .env file
print(f"Using OLLAMA_MODEL from .env: {os.environ.get('OLLAMA_MODEL', 'Not set')}")
print(f"Using OLLAMA_ENDPOINT from .env: {os.environ.get('OLLAMA_ENDPOINT', 'Not set')}")

# Set environment variables to ensure batch size is respected
# This will make the batch processor exit after processing one batch
os.environ["BATCH_PROCESSOR_FORCE_EXIT_AFTER_BATCH"] = "true"

# Run the batch processor - now using the fixed original file
# Setting --mode=batch to ensure it runs only once and exits
# Process 100 documents with concurrency of 5
cmd = [
    sys.executable,
    "batch_processor.py",
    "--batch-size", "100",   # Increased to process 100 documents
    "--concurrent", "5",     # Keep concurrency at 5 for optimal performance
    "--mode", "batch",       # Ensures it runs only one iteration
    "--checkpoint-interval", "10"  # Checkpoint every 10 documents
]

print(f"Running: {' '.join(cmd)}")
print("This will process exactly one batch of 100 documents with 5 concurrent LLM calls and exit.")
subprocess.run(cmd)