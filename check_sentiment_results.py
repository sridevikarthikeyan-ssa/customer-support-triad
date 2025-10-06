"""
check_sentiment_results.py
Script to check for results in the sentimental_analysis collection.
"""
import asyncio
import dotenv
import os
from bson import ObjectId
from mongo_client import MongoClient
import json
from datetime import datetime

# Custom JSON encoder to handle MongoDB-specific types
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

dotenv.load_dotenv(dotenv_path=".env", override=True)

async def check_sentiment_results():
    """Check for classification results in the sentimental_analysis collection."""
    print("Checking sentimental_analysis collection for classification results...")
    
    # Initialize MongoDB client using environment variables
    mongo_client = MongoClient(
        mongodb_uri=os.getenv("MONGODB_URI"),
        db_name=os.getenv("MONGODB_DB", "customer_support_triad"),
        source_collection=os.getenv("MONGODB_SOURCE_COLLECTION", "conversation_set"),
        target_collection=os.getenv("MONGODB_TARGET_COLLECTION", "sentimental_analysis")
    )
    
    try:
        # Connect to MongoDB
        await mongo_client.connect()
        print("Connected to MongoDB successfully")
        
        # Query the latest results in sentimental_analysis
        limit = 20  # Increased to show more results (can view the latest 20 out of 100)
        
        target_collection = mongo_client.db[mongo_client.target_collection_name]
        cursor = target_collection.find({}).sort("processed_at", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            results.append(doc)
        
        if results:
            print(f"Found {len(results)} classification results in sentimental_analysis collection:")
            print("\n=== FULL DOCUMENT FORMAT ===")
            
            # Show complete document format for the first result
            first_doc = results[0]
            print("\n--- Complete Document Structure ---")
            doc_json = json.dumps(first_doc, cls=MongoJSONEncoder, indent=2)
            print(doc_json)
            
            # Show summary of all results
            print("\n=== RESULTS SUMMARY ===")
            for i, result in enumerate(results):
                print(f"\n--- Result {i+1} ---")
                print(f"ID: {result.get('_id')}")
                print(f"Source Object ID: {result.get('source_object_id')}")
                print(f"Processed At: {result.get('processed_at')}")
                
                # Extract classification results
                classification = result.get('classification', {})
                if classification:
                    print(f"Categorization: {classification.get('categorization', 'Not set')}")
                    print(f"Intent: {classification.get('intent')}")
                    print(f"Topic: {classification.get('topic')}")
                    print(f"Sentiment: {classification.get('sentiment')}")
                
        else:
            print("No results found in sentimental_analysis collection.")
            
        # Check the source collection for processed documents
        print("\nChecking source collection for processed documents...")
        source_collection = mongo_client.db[mongo_client.source_collection_name]
        processed_count = await source_collection.count_documents({"status": "processed"})
        print(f"Total processed documents in source collection: {processed_count}")
        
        # Get the latest processed documents
        cursor = source_collection.find({"status": "processed"}).sort("last_processed_at", -1).limit(limit)
        processed_docs = []
        async for doc in cursor:
            processed_docs.append(doc)
        
        if processed_docs:
            print(f"\nLatest {len(processed_docs)} processed documents:")
            for i, doc in enumerate(processed_docs):
                print(f"ID: {doc.get('_id')}, Last Processed: {doc.get('last_processed_at')}")
                print(f"Result ID: {doc.get('result_id', 'Not set')}")
        else:
            print("No processed documents found.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close MongoDB connection
        await mongo_client.close()
        print("\nConnection closed")

if __name__ == "__main__":
    asyncio.run(check_sentiment_results())