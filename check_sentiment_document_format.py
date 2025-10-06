"""
check_sentiment_document_format.py
Script to show the complete document format of entries in the sentimental_analysis collection.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json
from bson import ObjectId
from datetime import datetime

# Create a custom JSON encoder to handle MongoDB-specific types
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def check_document_format():
    """Check the full document structure in the sentimental_analysis collection."""
    
    # Connect to MongoDB
    print("Connecting to MongoDB...")
    import os
    mongodb_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongodb_uri)
    
    # Connect to the database and collection
    db_name = os.getenv("MONGODB_DB", "customer_support_triad")
    collection_name = os.getenv("MONGODB_TARGET_COLLECTION", "sentimental_analysis")
    db = client[db_name]
    collection = db[collection_name]
    
    # Count documents
    count = await collection.count_documents({})
    print(f"Found {count} documents in sentimental_analysis collection")
    
    if count > 0:
        # Get the most recent documents
        cursor = collection.find().sort("processed_at", -1).limit(2)
        
        print("\n=== RECENT DOCUMENT FORMAT ===")
        documents = []
        async for doc in cursor:
            documents.append(doc)
        
        # Print the full document structure
        for i, doc in enumerate(documents):
            print(f"\n--- Document {i+1} ---")
            # Convert to JSON with indentation for better readability
            # Use custom encoder to handle MongoDB types
            doc_json = json.dumps(doc, cls=MongoJSONEncoder, indent=2)
            print(doc_json)
            
        # Get older documents for comparison
        print("\n=== OLDER DOCUMENT FORMAT ===")
        cursor = collection.find().sort("processed_at", 1).limit(1)
        async for doc in cursor:
            print("\n--- Older Document ---")
            doc_json = json.dumps(doc, cls=MongoJSONEncoder, indent=2)
            print(doc_json)
    
    else:
        print("No documents found in the collection")

if __name__ == '__main__':
    asyncio.run(check_document_format())