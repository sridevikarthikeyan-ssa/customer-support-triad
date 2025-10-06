"""
check_source_documents.py
Script to check which documents would be selected from the source collection.
"""
import asyncio
from mongo_client import MongoClient
import json
from bson import ObjectId

# Custom JSON encoder to handle ObjectId
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

async def check_source_documents():
    # Initialize MongoDB client using environment variables
    import os
    mongo_client = MongoClient(
        db_name=os.getenv("MONGODB_DB", "customer_support_triad"),
        source_collection=os.getenv("MONGODB_SOURCE_COLLECTION", "conversation_set"),
        target_collection=os.getenv("MONGODB_TARGET_COLLECTION", "sentimental_analysis")
    )
    
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        await mongo_client.connect()
        print("Connected successfully")
        
        # Fetch documents that would be processed
        batch_size = 5  # Show more than just 2 to give a better picture
        print(f"Checking the first {batch_size} unprocessed documents...")
        documents, first_id, last_id = await mongo_client.fetch_unprocessed_documents(batch_size=batch_size)
        
        print(f"Found {len(documents)} unprocessed documents")
        
        if documents:
            print("\nDocuments that would be processed:")
            for i, doc in enumerate(documents):
                doc_id = str(doc["_id"])
                conversation_number = doc.get("conversation_number", "unknown")
                tweets_count = len(doc.get("tweets", []))
                
                print(f"{i+1}. Document ID: {doc_id}")
                print(f"   Conversation Number: {conversation_number}")
                print(f"   Number of tweets: {tweets_count}")
                
                # Show sample of first tweet
                tweets = doc.get("tweets", [])
                if tweets:
                    first_tweet = tweets[0]
                    if isinstance(first_tweet, dict) and "text" in first_tweet:
                        print(f"   First tweet sample: {first_tweet['text'][:70]}...")
                    
                print()
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close connection
        await mongo_client.close()
        print("Connection closed")

if __name__ == "__main__":
    asyncio.run(check_source_documents())