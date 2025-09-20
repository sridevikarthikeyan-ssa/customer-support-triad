

import os
import requests
import json

API_URL = "http://localhost:8000/classify"



# One local hardcoded example from Delta_Airline_20250916_150358.json
local_example = {
    "conversation_number": "1",
    "tweets": [
        {"tweet_id": 611, "author_id": "115818", "role": "Customer", "inbound": True, "created_at": "Sat Aug 06 01:31:50 +0000 2016", "text": "@DELTA i booked my flight using delta amex card. Checking in now & was being charged for baggage"},
        {"tweet_id": 609, "author_id": "Delta", "role": "Service Provider", "inbound": False, "created_at": "Sat Aug 06 01:44:03 +0000 2016", "text": "@115818 Glad to check. Pls, DM your confirmation number for assistance.  *QB https://t.co/6iDGBJAc2m"},
        {"tweet_id": 610, "author_id": "115818", "role": "Customer", "inbound": True, "created_at": "Tue Oct 31 22:11:33 +0000 2017", "text": "@Delta DM sent"}
    ]
}


# Load the rest from Delta_Airline_20250916_150358.json
json_path = os.path.join(os.path.dirname(__file__), "Delta_Airline_20250916_150358.json")
with open(json_path, "r", encoding="utf-8") as f:
    all_conversations = json.load(f)


# Remove the local example if present in the file (avoid duplicate)
rest_conversations = [conv for conv in all_conversations if str(conv.get("conversation_number")) != local_example["conversation_number"]]

# Ensure all conversation_number values are strings
for conv in rest_conversations:
    if "conversation_number" in conv:
        conv["conversation_number"] = str(conv["conversation_number"])

# Combine local example and the rest
conversations = [local_example] + rest_conversations

import os
from datetime import datetime, timezone

results = []
for conversation in conversations:
    print(f"\nTesting production-grade conversation: {conversation['conversation_number']}")
    response = requests.post(API_URL, json=conversation)
    print("Status Code:", response.status_code)
    try:
        resp_json = response.json()
        print("Response JSON:", json.dumps(resp_json, indent=2))
        results.append(resp_json)
    except Exception:
        print("Response Text:", response.text)

# Save results to /data/classified_results_<UTC>.json
dt_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
out_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, f"classified_results_{dt_str}.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nSaved classified results to {out_path}")
