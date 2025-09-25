"""
check_sentiment_collections.py
Script to specifically check sentiment analysis collections in MongoDB.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json
from datetime import datetime

async def check_sentiment_collections():
    """Check specifically for sentiment analysis collections."""
    
    # Connect to MongoDB
    print("Connecting to MongoDB...")
    mongodb_uri = 'mongodb+srv://cia_db_user:qG5hStEqWkvAHrVJ@capstone-project.yyfpvqh.mongodb.net/?retryWrites=true&w=majority&appName=CAPSTONE-PROJECT'
    client = AsyncIOMotorClient(mongodb_uri)
    
    # Check both possible databases
    db_names = ["customer_support_triad", "customer_support"] 
    
    for db_name in db_names:
        print(f"\n=== Checking database: {db_name} ===")
        db = client[db_name]
        
        try:
            # Get collections
            collections = await db.list_collection_names()
            
            # Find collections related to sentiment
            sentiment_collections = [c for c in collections if "sentiment" in c.lower()]
            
            if sentiment_collections:
                print(f"Found {len(sentiment_collections)} sentiment-related collections:")
                for collection in sentiment_collections:
                    count = await db[collection].count_documents({})
                    print(f"- {collection}: {count} documents")
                    
                    # Show most recent document if any exist
                    if count > 0:
                        print(f"\nMost recent document in {collection}:")
                        cursor = db[collection].find().sort("processed_at", -1).limit(1)
                        async for doc in cursor:
                            print(f"  ID: {doc.get('_id')}")
                            print(f"  Source ID: {doc.get('source_object_id', 'N/A')}")
                            print(f"  Processed at: {doc.get('processed_at', 'N/A')}")
                            
                            # Check classification data
                            classification = doc.get('classification', {})
                            if classification:
                                print("  Classification data:")
                                for key, value in classification.items():
                                    print(f"    {key}: {value}")
            else:
                print(f"No sentiment-related collections found in {db_name}")
                
            # Check source collections
            source_collections = ["conversation_set"]
            for source in source_collections:
                if source in collections:
                    print(f"\nSource collection '{source}':")
                    count = await db[source].count_documents({})
                    processed = await db[source].count_documents({"status": "processed"})
                    print(f"  Total documents: {count}")
                    print(f"  Processed documents: {processed}")
                    
                    # Check one processed document
                    if processed > 0:
                        print("\nSample processed document:")
                        cursor = db[source].find({"status": "processed"}).sort("last_processed_at", -1).limit(1)
                        async for doc in cursor:
                            print(f"  ID: {doc.get('_id')}")
                            print(f"  Result ID: {doc.get('result_id', 'Not set')}")
                            print(f"  Last processed: {doc.get('last_processed_at', 'N/A')}")
        
        except Exception as e:
            print(f"Error checking database {db_name}: {str(e)}")
    
    print("\nDone checking MongoDB collections")

if __name__ == '__main__':
    asyncio.run(check_sentiment_collections())