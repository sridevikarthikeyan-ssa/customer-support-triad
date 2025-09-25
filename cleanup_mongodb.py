import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def cleanup_mongodb():
    # Connect to MongoDB
    mongodb_uri = 'mongodb+srv://cia_db_user:qG5hStEqWkvAHrVJ@capstone-project.yyfpvqh.mongodb.net/?retryWrites=true&w=majority&appName=CAPSTONE-PROJECT'
    client = AsyncIOMotorClient(mongodb_uri)
    
    # Use the customer_support_triad database
    db = client['customer_support_triad']
    
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