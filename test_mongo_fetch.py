"""
test_mongo_fetch.py
Test MongoDB connection and document fetching without LLM integration.
"""
import asyncio
import json
from datetime import datetime
from mongo_client import MongoClient
from logger import logger

async def test_mongo_fetch():
    """Test MongoDB connection and document fetching."""
    # Initialize MongoDB client
    mongo_client = MongoClient(
        db_name="customer_support_triad",
        source_collection="conversation_set",
        target_collection="sentimental_analysis"
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