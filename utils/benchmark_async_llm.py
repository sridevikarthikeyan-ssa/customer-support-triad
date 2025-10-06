"""
benchmark_async_llm.py

A utility script to benchmark the performance of concurrent LLM calls.
This helps determine optimal batch sizes for production workloads.
"""
import os
import sys
import time
import asyncio
import json
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from async_llm_wrapper import safe_ollama_classify_async

# Sample customer queries to use for benchmarking
SAMPLE_QUERIES = [
    "I've been waiting for my refund for 3 weeks now. This is unacceptable!",
    "When will the mobile app be updated with the new features?",
    "Thank you so much for your help yesterday. The issue is fixed now.",
    "How do I change my shipping address for future orders?",
    "I can't log in to my account after the last update.",
    "Your product is amazing! I've recommended it to all my colleagues.",
    "I need to cancel my subscription immediately.",
    "Is there a discount for annual billing?",
    "The website is extremely slow today. Please fix it.",
    "I'd like to upgrade my current plan to the premium tier."
]

async def run_benchmark(concurrency, total_calls, model):
    """Run a benchmark with the specified parameters."""
    print(f"\n===== BENCHMARK: {concurrency} concurrent calls, {total_calls} total calls =====")
    print(f"Using model: {model}")
    
    # Set the model for the test
    os.environ["OLLAMA_MODEL"] = model
    
    # Create messages for all calls
    all_messages = []
    for i in range(total_calls):
        query = SAMPLE_QUERIES[i % len(SAMPLE_QUERIES)]
        message = [{"role": "user", "content": f"Please classify this customer query in JSON format with 'intent', 'topic', and 'sentiment' fields: '{query}'"}]
        all_messages.append(message)
    
    results = {
        "success_count": 0,
        "error_count": 0,
        "total_time": 0,
        "calls": []
    }
    
    # Process in batches of specified concurrency
    start_time = time.time()
    batch_count = 0
    
    for i in range(0, total_calls, concurrency):
        batch_count += 1
        batch = all_messages[i:i+concurrency]
        batch_size = len(batch)
        
        print(f"\nBatch {batch_count}: Processing {batch_size} calls concurrently...")
        batch_start = time.time()
        
        # Create and run tasks
        tasks = [safe_ollama_classify_async(message) for message in batch]
        batch_results = await asyncio.gather(*tasks)
        
        batch_time = time.time() - batch_start
        print(f"Batch {batch_count} completed in {batch_time:.2f} seconds")
        
        # Process results
        for j, result in enumerate(batch_results):
            call_index = i + j
            success = "error" not in result
            
            if success:
                results["success_count"] += 1
            else:
                results["error_count"] += 1
            
            # Store detailed results
            results["calls"].append({
                "index": call_index,
                "query": SAMPLE_QUERIES[call_index % len(SAMPLE_QUERIES)],
                "success": success,
                "result": result
            })
    
    total_time = time.time() - start_time
    results["total_time"] = total_time
    
    # Calculate statistics
    avg_time_per_call = total_time / total_calls if total_calls > 0 else 0
    
    # Print summary
    print("\n===== BENCHMARK RESULTS =====")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average time per call: {avg_time_per_call:.2f} seconds")
    print(f"Throughput: {total_calls / total_time:.2f} calls/second")
    print(f"Success rate: {results['success_count'] / total_calls * 100:.1f}% ({results['success_count']}/{total_calls})")
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_{concurrency}concurrent_{total_calls}total_{timestamp}.json"
    filepath = os.path.join("data", filename)
    
    # Make sure data directory exists
    os.makedirs("data", exist_ok=True)
    
    with open(filepath, "w") as f:
        json.dump({
            "parameters": {
                "concurrency": concurrency,
                "total_calls": total_calls,
                "model": model,
                "timestamp": timestamp
            },
            "results": {
                "total_time_seconds": total_time,
                "avg_time_per_call_seconds": avg_time_per_call,
                "throughput_calls_per_second": total_calls / total_time,
                "success_rate_percent": results['success_count'] / total_calls * 100,
                "success_count": results['success_count'],
                "error_count": results['error_count']
            },
            "detailed_results": results["calls"]
        }, f, indent=2)
    
    print(f"Results saved to {filepath}")
    return results

async def main():
    parser = argparse.ArgumentParser(description="Benchmark async LLM calls")
    parser.add_argument("-c", "--concurrency", type=int, default=3, 
                        help="Number of concurrent LLM calls")
    parser.add_argument("-t", "--total", type=int, default=10,
                        help="Total number of LLM calls to make")
    parser.add_argument("-m", "--model", type=str, default="llama3",
                        help="Ollama model to use")
    
    args = parser.parse_args()
    
    await run_benchmark(args.concurrency, args.total, args.model)

if __name__ == "__main__":
    asyncio.run(main())