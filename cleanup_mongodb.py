import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def cleanup_mongodb():
    # Connect to MongoDB
    import os
    mongodb_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongodb_uri)
    
    # Use the database from environment variable
    db_name = os.getenv("MONGODB_DB", "customer_support_triad")
    db = client[db_name]
    
    print("=== CLEANING UP DATABASE: customer_support_triad ===")
    
    # Check if collections exist
    collection_names = await db.list_collection_names()
    
    for collection_name in collection_names:
        # Get current document count
        count_before = await db[collection_name].count_documents({})
        
        # Delete all documents in the collection
        result = await db[collection_name].delete_many({})
        
        print(f"Collection '{collection_name}': Deleted {result.deleted_count} of {count_before} documents")
    
    # Verify collections are empty
    print("\n=== VERIFICATION ===")
    for collection_name in collection_names:
        count = await db[collection_name].count_documents({})
        print(f"Collection '{collection_name}' now has {count} documents")

if __name__ == "__main__":
    asyncio.run(cleanup_mongodb())