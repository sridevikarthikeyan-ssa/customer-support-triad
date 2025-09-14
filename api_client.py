"""
api_client.py
Sample API client for E2E testing with FastAPI server and actual Ollama/Llama3 model.
"""
import requests
import json

API_URL = "http://localhost:8000/classify"




conversations = [
    {
        "conversation_number": "debug-multiturn-001",
        "messages": [
            {"sender": "customer", "text": "Thank you for your quick help! Everything is working now."},
            {"sender": "agent", "text": "Glad to hear that! Let us know if you need anything else."},
            {"sender": "customer", "text": "Will you send a follow-up email?"},
            {"sender": "agent", "text": "Yes, you will receive a confirmation email shortly."},
            {"sender": "customer", "text": "Can I get a transcript of this chat?"},
            {"sender": "agent", "text": "Of course, we will email you the transcript within 24 hours."}
        ]
    },
    {
        "conversation_number": "debug-multiturn-002",
        "messages": [
            {"sender": "customer", "text": "My internet is down since yesterday. I tried restarting the router."},
            {"sender": "agent", "text": "I'm sorry for the trouble. Let me run a remote diagnostic."},
            {"sender": "customer", "text": "Thanks. Will I be compensated for the downtime?"},
            {"sender": "agent", "text": "Yes, you will receive a credit on your next bill."},
            {"sender": "customer", "text": "Can you confirm when service will be restored?"},
            {"sender": "agent", "text": "It should be back within 2 hours. We'll notify you by SMS."}
        ]
    },
    {
        "conversation_number": "debug-multiturn-003",
        "messages": [
            {"sender": "customer", "text": "I received the wrong item in my order."},
            {"sender": "agent", "text": "I'm sorry for the mistake. Can you send a photo of the item?"},
            {"sender": "customer", "text": "Sure, I just sent it by email."},
            {"sender": "agent", "text": "Thank you. We'll arrange a pickup and send the correct item."},
            {"sender": "customer", "text": "Will I get a refund if the correct item is out of stock?"},
            {"sender": "agent", "text": "Yes, you'll receive a full refund if we can't fulfill the order."}
        ]
    }
]

for conversation in conversations:
    print(f"\nTesting conversation: {conversation['conversation_number']}")
    response = requests.post(API_URL, json=conversation)
    print("Status Code:", response.status_code)
    try:
        print("Response JSON:", json.dumps(response.json(), indent=2))
    except Exception:
        print("Response Text:", response.text)
