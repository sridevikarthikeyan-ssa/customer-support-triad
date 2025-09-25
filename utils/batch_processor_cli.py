#!/usr/bin/env python
"""
batch_processor_cli.py
Command-line tool to run the batch processor for customer support queries.
"""
import os
import asyncio
import argparse
from datetime import datetime
import json

from batch_processor import BatchProcessor
from logger import logger


async def run_batch_processor(args):
    """
    Run the batch processor with the given arguments.
    
    Args:
        args: Command-line arguments
    """
    logger.info(f"Starting batch processor with batch size {args.batch_size} and max concurrent {args.concurrent}")
    
    # Create the batch processor
    processor = BatchProcessor(
        mongodb_uri=args.mongodb_uri,
        source_collection=args.source,
        target_collection=args.target,
        batch_size=args.batch_size,
        max_concurrent=args.concurrent
    )
    
    try:
        # Run the processor
        stats = await processor.run(
            continuous=args.continuous,
            wait_time=args.wait_time
        )
        
        # Print the results
        logger.info("Batch processing completed")
        print(json.dumps(stats, indent=2, default=str))
        
        # Write results to file if requested
        if args.output:
            output_path = args.output
            with open(output_path, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            logger.info(f"Results written to {output_path}")
    
    except KeyboardInterrupt:
        logger.info("Batch processor interrupted by user")
    
    except Exception as e:
        logger.error(f"Error running batch processor: {str(e)}")
        raise


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Process customer support queries in batches using MongoDB and LLM"
    )
    
    # MongoDB connection options
    parser.add_argument("--mongodb-uri", type=str, 
                       help="MongoDB connection URI (defaults to MONGODB_URI env var)")
    parser.add_argument("--source", type=str, default="conversation_set",
                       help="Source collection name (default: conversation_set)")
    parser.add_argument("--target", type=str, default="sentimental_analysis",
                       help="Target collection name (default: sentimental_analysis)")
    
    # Processing options
    parser.add_argument("--batch-size", type=int, default=10,
                       help="Number of documents to process in each batch (default: 10)")
    parser.add_argument("--concurrent", type=int, default=5,
                       help="Maximum number of concurrent LLM calls (default: 5)")
    parser.add_argument("--continuous", action="store_true",
                       help="Run in continuous mode, processing new documents as they arrive")
    parser.add_argument("--wait-time", type=int, default=60,
                       help="Wait time in seconds between batches in continuous mode (default: 60)")
    
    # Output options
    parser.add_argument("--output", type=str,
                       help="Write processing statistics to the specified file")
    
    args = parser.parse_args()
    
    # Run the batch processor
    asyncio.run(run_batch_processor(args))


if __name__ == "__main__":
    main()