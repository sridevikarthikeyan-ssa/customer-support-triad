"""
test_mongo_fetch.py
Test MongoDB connection and document fetching without LLM integration.
"""
import asyncio
import json
import os
from datetime import datetime
from mongo_client import MongoClient
from logger import logger
from dotenv import load_dotenv

async def test_mongo_fetch():
    """Test MongoDB connection and document fetching."""
    # Load environment variables from .env
    load_dotenv()
    mongodb_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB")
    source_collection = os.getenv("MONGODB_SOURCE_COLLECTION")
    target_collection = os.getenv("MONGODB_TARGET_COLLECTION")
    print(f"Using MongoDB URI: {mongodb_uri}")
    print(f"Using DB: {db_name}")
    print(f"Using Source Collection: {source_collection}")
    print(f"Using Target Collection: {target_collection}")
    # Initialize MongoDB client
    mongo_client = MongoClient(
        mongodb_uri=mongodb_uri,
        db_name=db_name,
        source_collection=source_collection,
        target_collection=target_collection
    )
    
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        await mongo_client.connect()
        print("Connected successfully")
        
        # Fetch a small batch of documents
        print("Fetching documents...")
        documents, first_id, last_id = await mongo_client.fetch_unprocessed_documents(batch_size=2)
        
        print(f"Fetched {len(documents)} documents")
        
        if documents:
            # Print document information
            for i, doc in enumerate(documents):
                doc_id = str(doc["_id"])
                conversation_number = doc.get("conversation_number", "unknown")
                print(f"Document {i+1}: ID={doc_id}, Conversation Number={conversation_number}")
                
                # Get tweets info
                tweets = doc.get("tweets", [])
                print(f"  - Contains {len(tweets)} tweets")
                
                # Sample first tweet
                if tweets and len(tweets) > 0 and isinstance(tweets[0], dict):
                    print(f"  - First tweet: {tweets[0].get('text', '')[:50]}...")
            
            print("\nSample document structure:")
            print(json.dumps({k: type(v).__name__ for k, v in documents[0].items()}, indent=2))
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close connection
        await mongo_client.close()
        print("Connection closed")

if __name__ == "__main__":
    asyncio.run(test_mongo_fetch())