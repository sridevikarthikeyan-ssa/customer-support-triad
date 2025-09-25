#!/usr/bin/env python3
"""
CLI interface for the Customer Support Query Classification batch processor.
This module provides command-line functionality to run the batch processor with various options.
"""

import os
import sys
import argparse
import asyncio
import logging
from datetime import datetime
import json

from batch_processor import BatchProcessor
import logger

# Setup logger
logger = logging.getLogger("customer_support_query_classification")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Customer Support Query Classification Batch Processor CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of documents to process in each batch"
    )
    
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Maximum number of concurrent processing tasks"
    )
    
    parser.add_argument(
        "--mongodb-uri",
        type=str,
        default=os.environ.get("MONGODB_URI", "mongodb://localhost:27017"),
        help="MongoDB connection URI"
    )
    
    parser.add_argument(
        "--db-name",
        type=str,
        default=os.environ.get("MONGODB_DB", "customer_support"),
        help="MongoDB database name"
    )
    
    parser.add_argument(
        "--queries-collection",
        type=str,
        default=os.environ.get("MONGODB_QUERIES_COLLECTION", "queries"),
        help="MongoDB collection name for customer queries"
    )
    
    parser.add_argument(
        "--results-collection",
        type=str,
        default=os.environ.get("MONGODB_RESULTS_COLLECTION", "results"),
        help="MongoDB collection name for classification results"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path to save processing results (JSON format)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch documents but don't process them or store results"
    )

    return parser.parse_args()

async def run_batch_processor(args):
    """Run the batch processor with the specified arguments."""
    # Configure logging level
    logging.getLogger("customer_support_query_classification").setLevel(
        getattr(logging, args.log_level)
    )
    
    logger.info(f"Starting batch processor with batch size: {args.batch_size}, "
                f"max concurrent: {args.max_concurrent}")
    logger.info(f"Connecting to MongoDB at {args.mongodb_uri}, "
                f"database: {args.db_name}")
    
    try:
        # Create batch processor
        processor = BatchProcessor(
            mongodb_uri=args.mongodb_uri,
            source_collection=args.queries_collection,
            target_collection=args.results_collection,
            batch_size=args.batch_size,
            max_concurrent=args.max_concurrent
        )
        
        if args.dry_run:
            logger.info("Running in dry-run mode (no processing or result storage)")
            try:
                # Connect to MongoDB
                await processor.connect()
                
                # Fetch documents but don't process them
                all_queries = []
                batch_num = 1
                
                while True:
                    try:
                        queries = await processor.fetch_unprocessed_queries()
                        if not queries:
                            break
                            
                        logger.info(f"Batch {batch_num}: Found {len(queries)} unprocessed queries")
                        all_queries.extend(queries)
                        batch_num += 1
                    except Exception as e:
                        logger.error(f"Error fetching batch {batch_num}: {e}")
                        break
                    
                logger.info(f"Total unprocessed queries: {len(all_queries)}")
                
                # Output sample of queries
                if all_queries:
                    logger.info("Sample queries:")
                    for i, query in enumerate(all_queries[:5]):
                        logger.info(f"{i+1}. {query.get('text', 'No text available')}")
                        
                    if args.output:
                        with open(args.output, 'w') as f:
                            json.dump(all_queries, f, default=str, indent=2)
                        logger.info(f"Wrote {len(all_queries)} queries to {args.output}")
            finally:
                # Close MongoDB connection
                try:
                    await processor.close()
                except Exception as e:
                    logger.warning(f"Error closing MongoDB connection: {e}")
        else:
            # Run full batch processing
            try:
                start_time = datetime.now()
                stats = await processor.run()
                end_time = datetime.now()
                
                # Add additional timing information
                stats["start_time"] = start_time.isoformat()
                stats["end_time"] = end_time.isoformat()
                stats["duration_seconds"] = (end_time - start_time).total_seconds()
                
                # Output results
                logger.info("Batch processing completed")
                logger.info(f"Documents processed: {stats['documents_processed']}")
                logger.info(f"Successful: {stats['successful']}, Failed: {stats['failed']}")
                logger.info(f"Total processing time: {stats['duration_seconds']:.2f} seconds")
                
                # Save results to file if requested
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(stats, f, default=str, indent=2)
                    logger.info(f"Saved processing statistics to {args.output}")
            except Exception as e:
                logger.error(f"Error during batch processing: {e}")
                raise
    except Exception as e:
        logger.error(f"Failed to initialize batch processor: {e}")
        raise

def main():
    """Main entry point for the CLI."""
    args = parse_arguments()
    try:
        asyncio.run(run_batch_processor(args))
        return 0
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error running batch processor: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())