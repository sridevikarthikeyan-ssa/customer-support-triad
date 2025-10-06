import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def list_databases_and_collections():
    # Connect to MongoDB
    import os
    mongodb_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongodb_uri)
    
    # List all databases
    print("=== DATABASES ===")
    db_names = await client.list_database_names()
    for db in db_names:
        if db not in ['admin', 'local', 'config']:  # Skip system dbs
            print(f"Database: {db}")
            
            # List collections in this database
            db_obj = client[db]
            collections = await db_obj.list_collection_names()
            if collections:
                print("  Collections:")
                for coll in collections:
                    count = await db_obj[coll].count_documents({})
                    print(f"    - {coll} ({count} documents)")
            else:
                print("  No collections")
            print()

# Run the async function
if __name__ == "__main__":
    asyncio.run(list_databases_and_collections())