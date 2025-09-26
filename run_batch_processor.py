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

# Get command line arguments, use sys.argv[1:] to pass through any arguments provided
cmd = [sys.executable, "batch_processor.py"] + sys.argv[1:]

# If no arguments provided, use defaults
if len(sys.argv) == 1:
    cmd.extend([
        "--batch-size", "10",     # Default to 10 documents
        "--concurrent", "5",      # Default concurrency of 5
        "--mode", "batch",        # Default to batch mode
        "--checkpoint-interval", "10"  # Default checkpoint interval
    ])

print(f"Running: {' '.join(cmd)}")
print("This will process exactly one batch with the specified parameters.")
subprocess.run(cmd)