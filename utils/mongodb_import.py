#!/usr/bin/env python3
"""
MongoDB Data Import Utility for Customer Support Query Classification

This script allows users to import sample customer support queries into a MongoDB
database for use with the batch processor.
"""

import os
import sys
import json
import argparse
import asyncio
from datetime import datetime, timezone
import motor.motor_asyncio

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Import sample data into MongoDB for batch processing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
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
        "--collection",
        type=str,
        default=os.environ.get("MONGODB_QUERIES_COLLECTION", "queries"),
        help="MongoDB collection name for customer queries"
    )
    
    parser.add_argument(
        "--input-file",
        type=str,
        help="JSON file containing customer queries to import (optional)"
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of sample queries to generate if no input file is provided"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path to save query data (JSON format)"
    )
    
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock MongoDB (no real database connection required)"
    )

    return parser.parse_args()

# Sample customer support queries for demo purposes
SAMPLE_QUERIES = [
    "I can't log into my account after the recent update.",
    "I want to return my recent purchase. It arrived damaged.",
    "How do I change my shipping address for my subscription?",
    "Your customer service is terrible. I've been waiting for a response for days!",
    "When will the new features you promised be available?",
    "Thank you for your prompt response and resolution to my issue.",
    "The app keeps crashing when I try to make a payment.",
    "I'd like to upgrade my subscription to the premium plan.",
    "Can you help me understand how the loyalty points system works?",
    "I found a bug in your website. The checkout page doesn't load correctly.",
    "Do you offer international shipping?",
    "I'm having trouble uploading my profile picture.",
    "My order was supposed to arrive yesterday, but I still haven't received it.",
    "How do I cancel my subscription?",
    "The product I received doesn't match the description on your website.",
    "Is there a way to track my order in real-time?",
    "I'm interested in your enterprise pricing plan.",
    "Your mobile app is great, but I'd like to suggest a feature.",
    "I forgot my password and the reset email never arrived.",
    "Can I speak with a human agent? This chatbot isn't helping me."
]

# Sample sources for metadata
SOURCES = ["email", "chat", "phone", "social_media", "app_feedback", "website_form"]

async def create_sample_document(index):
    """Create a sample document with query text and metadata."""
    query_text = SAMPLE_QUERIES[index % len(SAMPLE_QUERIES)]
    source = SOURCES[index % len(SOURCES)]
    
    return {
        "_id": f"sample_doc_{index}",
        "text": query_text,
        "metadata": {
            "source": source,
            "timestamp": datetime.now(timezone.utc)
        },
        "processed": False,
        "processing_attempts": 0
    }

async def import_sample_data(args):
    """Import sample data into MongoDB."""
    try:
        # Use mock MongoDB if requested
        if args.mock:
            # Generate documents without DB connection
            print("Running in mock mode (no database operations)")
            client = None
            db = None
            collection = None
        else:
            # Connect to real MongoDB
            try:
                client = motor.motor_asyncio.AsyncIOMotorClient(args.mongodb_uri)
                db = client[args.db_name]
                collection = db[args.collection]
                print(f"Connected to MongoDB at {args.mongodb_uri}")
            except Exception as e:
                print(f"Error connecting to MongoDB: {e}")
                print("Use --mock flag to run in mock mode without a real MongoDB connection")
                raise
        
        documents = []
        
        # Use input file if provided
        if args.input_file:
            try:
                with open(args.input_file, 'r') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    for i, item in enumerate(data):
                        if isinstance(item, str):
                            # Simple string format
                            doc = {
                                "_id": f"file_doc_{i}",
                                "text": item,
                                "metadata": {
                                    "source": "imported_file",
                                    "timestamp": datetime.now(timezone.utc)
                                },
                                "processed": False,
                                "processing_attempts": 0
                            }
                            documents.append(doc)
                        elif isinstance(item, dict) and "text" in item:
                            # Dict format with text field
                            doc = {
                                "_id": item.get("id", f"file_doc_{i}"),
                                "text": item["text"],
                                "metadata": item.get("metadata", {
                                    "source": "imported_file",
                                    "timestamp": datetime.now(timezone.utc)
                                }),
                                "processed": False,
                                "processing_attempts": 0
                            }
                            documents.append(doc)
                
                print(f"Loaded {len(documents)} queries from file {args.input_file}")
                
            except Exception as e:
                print(f"Error loading file {args.input_file}: {e}")
                return
        else:
            # Generate sample documents
            count = min(args.count, 100)  # Limit to 100 for safety
            print(f"Generating {count} sample customer support queries")
            
            for i in range(count):
                doc = await create_sample_document(i)
                documents.append(doc)
        
        # Insert documents
        if documents:
            # Insert into database if available
            if collection:
                try:
                    await collection.insert_many(documents)
                    print(f"Successfully imported {len(documents)} documents into {args.db_name}.{args.collection}")
                except Exception as e:
                    print(f"Error inserting documents into MongoDB: {e}")
            else:
                print(f"Generated {len(documents)} sample documents (not saved to database)")
            
            # Show sample of imported queries
            print("\nSample of imported queries:")
            for i, doc in enumerate(documents[:5]):
                print(f"{i+1}. {doc['text']}")
                
            if len(documents) > 5:
                print(f"... and {len(documents) - 5} more")
                
            # Save to output file if requested
            if args.output:
                try:
                    with open(args.output, 'w') as f:
                        json.dump(documents, f, default=str, indent=2)
                    print(f"\nSaved {len(documents)} queries to {args.output}")
                except Exception as e:
                    print(f"Error saving to output file: {e}")
        else:
            print("No documents to import")
    
    except Exception as e:
        print(f"Error importing data: {e}")
    finally:
        # Close MongoDB connection if it exists
        if 'client' in locals() and client is not None:
            client.close()
            print("MongoDB connection closed")

async def main():
    """Main entry point."""
    args = parse_arguments()
    await import_sample_data(args)

if __name__ == "__main__":
    asyncio.run(main())