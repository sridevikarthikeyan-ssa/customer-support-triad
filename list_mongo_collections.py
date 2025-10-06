"""
list_mongo_collections.py
Script to list all collections in the MongoDB database to verify the correct collection name.
"""
import asyncio
from mongo_client import MongoClient
from logger import logger

async def list_collections():
    """List all collections in the MongoDB database."""
    print("Connecting to MongoDB...")
    
    # Initialize MongoDB client - use the same connection parameters as batch_processor
    mongo_client = MongoClient(
        db_name="customer_support_triad",
        source_collection="conversation_set",
        target_collection="sentimental_analysis"
    )
    
    try:
        # Connect to MongoDB
        await mongo_client.connect()
        print("Connected to MongoDB successfully")
        
        # List all collections in the database
        collection_names = await mongo_client.db.list_collection_names()
        
        print(f"\nCollections in database '{mongo_client.db.name}':")
        for idx, collection in enumerate(sorted(collection_names), 1):
            print(f"{idx}. {collection}")
        
        # Get counts for each collection
        print("\nDocument counts:")
        for collection in sorted(collection_names):
            count = await mongo_client.db[collection].count_documents({})
            print(f"{collection}: {count} documents")
            
        # Check for specific collections
        target_collection = mongo_client.target_collection_name
        if target_collection in collection_names:
            print(f"\nTarget collection '{target_collection}' exists with {await mongo_client.db[target_collection].count_documents({})} documents")
            
            # Show the most recent document in the target collection
            cursor = mongo_client.db[target_collection].find({}).sort("processed_at", -1).limit(1)
            async for doc in cursor:
                print(f"\nMost recent document in '{target_collection}':")
                print(f"ID: {doc.get('_id')}")
                print(f"Source Object ID: {doc.get('source_object_id')}")
                print(f"Processed At: {doc.get('processed_at')}")
                
                # Print classification data
                classification = doc.get('classification', {})
                if isinstance(classification, dict):
                    print("Classification data:")
                    for key, value in classification.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"Classification (not a dict): {classification}")
        else:
            print(f"\nWARNING: Target collection '{target_collection}' does not exist!")
            
            # Check for similar named collections
            similar_collections = [coll for coll in collection_names if "sentiment" in coll.lower()]
            if similar_collections:
                print(f"Found similar collections: {', '.join(similar_collections)}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close MongoDB connection
        await mongo_client.close()
        print("\nConnection closed")

if __name__ == "__main__":
    asyncio.run(list_collections())