import asyncio
import json
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

async def check_mongodb():
    # Connect to MongoDB
    mongodb_uri = 'mongodb+srv://cia_db_user:qG5hStEqWkvAHrVJ@capstone-project.yyfpvqh.mongodb.net/?retryWrites=true&w=majority&appName=CAPSTONE-PROJECT'
    
    print(f"Connecting to MongoDB: {mongodb_uri}")
    client = AsyncIOMotorClient(mongodb_uri)
    
    # Check server info
    try:
        server_info = await client.server_info()
        print(f"Connected to MongoDB version: {server_info.get('version')}")
    except Exception as e:
        print(f"Failed to get server info: {str(e)}")
        return
    
    # Check database names
    try:
        db_names = await client.list_database_names()
        print('Available databases:')
        for db in db_names:
            if db not in ['admin', 'local', 'config']:  # Skip system dbs
                print(f'- {db}')
    except Exception as e:
        print(f"Failed to list databases: {str(e)}")
        return
    
    # Try to access specific database
    for db_name in ["customer_support", "customer_support_triad"]:
        try:
            db = client[db_name]
            collection_names = await db.list_collection_names()
            print(f'\nCollections in {db_name}:')
            for collection in collection_names:
                print(f'- {collection}')
                
                # Count documents in each collection
                try:
                    count = await db[collection].count_documents({})
                    print(f'  {collection}: {count} documents')
                    
                    # Get one sample document
                    if count > 0:
                        sample = await db[collection].find_one({})
                        print(f"  Sample document fields: {list(sample.keys())}")
                except Exception as e:
                    print(f"  Error counting documents in {collection}: {str(e)}")
        except Exception as e:
            print(f"Error accessing database {db_name}: {str(e)}")

if __name__ == '__main__':
    asyncio.run(check_mongodb())