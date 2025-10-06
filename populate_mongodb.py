import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from bson import ObjectId
import json
import random

async def populate_mongodb():
    # Connect to MongoDB
    import os
    mongodb_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongodb_uri)
    
    # Use the database from environment variable
    db_name = os.getenv("MONGODB_DB", "customer_support_triad")
    db = client[db_name]
    
    # Check if collections exist, create them if not
    collection_names = await db.list_collection_names()
    source_collection_name = os.getenv("MONGODB_SOURCE_COLLECTION", "conversation_set")
    target_collection_name = os.getenv("MONGODB_TARGET_COLLECTION", "sentimental_analysis")
    if source_collection_name not in collection_names:
        await db.create_collection(source_collection_name)
    if target_collection_name not in collection_names:
        await db.create_collection(target_collection_name)
    
    # Create indexes
    await db[source_collection_name].create_index("status")
    await db[source_collection_name].create_index("conversation_number")
    await db[target_collection_name].create_index("source_object_id")
    
    # Create sample conversation documents
    source_collection = db[source_collection_name]
    
    # Check if we already have data
    count = await source_collection.count_documents({})
    if count > 0:
        print(f"Database already has {count} documents. Skipping population.")
        return
    
    # Sample customer queries and topics
    customer_queries = [
        "I haven't received my order that I placed last week. Order #12345.",
        "How do I reset my password on your website?",
        "My subscription was charged twice this month. Please help!",
        "I'm trying to upgrade my plan but getting an error.",
        "Do you ship to international addresses?",
        "The product I received is damaged. How do I return it?",
        "When will the blue sweater be back in stock?",
        "Can I change my delivery address for order #98765?",
        "I need to cancel my order placed yesterday.",
        "Is there a discount for bulk orders?"
    ]
    
    # Create 10 conversation documents
    conversations = []
    for i in range(10):
        query = random.choice(customer_queries)
        conversations.append({
            "conversation_number": f"CONV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{i+1:03d}",
            "messages": [
                {"role": "user", "content": query},
                {"role": "agent", "content": "Thank you for reaching out. Let me help you with that."}
            ],
            "status": "pending",  # Options: pending, processing, processed
            "processing_attempts": 0,
            "created_at": datetime.now(timezone.utc),
            "metadata": {
                "customer_id": f"cust-{random.randint(10000, 99999)}",
                "source": "web_chat",
                "priority": random.choice(["low", "medium", "high"])
            }
        })
    
    # Insert the conversations
    result = await source_collection.insert_many(conversations)
    inserted_ids = result.inserted_ids
    print(f"Inserted {len(inserted_ids)} sample conversations")
    
    # Process a couple to show the workflow
    for i, doc_id in enumerate(inserted_ids[:3]):
        # Update status to processed for the first few documents
        doc = await source_collection.find_one({"_id": doc_id})
        
        # Create a classification result
        classification = {
            "intent": random.choice(["inquiry", "complaint", "request"]),
            "topic": random.choice(["billing", "account", "product", "shipping"]),
            "sentiment": random.choice(["positive", "neutral", "negative"]),
            "priority": random.choice(["low", "medium", "high"])
        }
        
        # Insert the classification result
        result_doc = {
            "conversation_number": doc["conversation_number"],
            "source_object_id": str(doc["_id"]),
            "classification": classification,
            "original_messages": doc["messages"],
            "processed_at": datetime.now(timezone.utc),
            "processing_metadata": {
                "batch_job_id": f"sample-batch-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                "processing_attempts": 1
            }
        }
        
        # Store in target collection
        result = await db[target_collection_name].insert_one(result_doc)
        result_id = str(result.inserted_id)
        
        # Update the source document
        await source_collection.update_one(
            {"_id": doc_id},
            {"$set": {
                "status": "processed",
                "last_processed_at": datetime.now(timezone.utc),
                "result_id": result_id
            }}
        )
        print(f"Processed document {i+1}: {doc['conversation_number']}")
    
    # Verify final state
    pending_count = await source_collection.count_documents({"status": "pending"})
    processed_count = await source_collection.count_documents({"status": "processed"})
    target_count = await db[target_collection_name].count_documents({})
    
    print(f"\nFinal state:")
    print(f"- Pending conversations: {pending_count}")
    print(f"- Processed conversations: {processed_count}")
    print(f"- Classification results: {target_count}")

if __name__ == '__main__':
    asyncio.run(populate_mongodb())