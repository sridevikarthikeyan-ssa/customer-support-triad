
import json
import os
print(f"[DEBUG] Loaded prompt_builder.py from: {os.path.abspath(__file__)}")

# Allowed values for schema fields
INTENT_OPTIONS = [
    "Order Status", "Cancel Order", "Return/Refund", "Product Inquiry", "Technical Support", "Complaint", "Feedback", "Account/Billing", "Shipping", "Shipping/Delivery", "Other"
]
TOPIC_OPTIONS = [
    "Orders", "Payments", "Shipping/Delivery", "Shipping", "Returns", "Refunds", "Warranty", "Product Info", "Account", "Technical", "General"
]
SENTIMENT_OPTIONS = ["Positive", "Neutral", "Negative"]

# Multi-turn few-shot examples (list of messages per example)
FEW_SHOTS = [
    {
        "messages": [
            {"sender": "customer", "text": "I want to cancel my subscription."},
            {"sender": "agent", "text": "I can help you with that."}
        ],
        "output": {
            "categorization": "Request to cancel subscription",
            "intent": "Cancel Order",
            "topic": "Account/Billing",
            "sentiment": "Neutral"
        }
    },
    {
        "messages": [
            {"sender": "customer", "text": "My internet is down since morning."},
            {"sender": "agent", "text": "Let me check your connection status."}
        ],
        "output": {
            "categorization": "Internet connectivity issue",
            "intent": "Technical Support",
            "topic": "Technical",
            "sentiment": "Negative"
        }
    },
    {
        "messages": [
            {"sender": "customer", "text": "Where is my order?"},
            {"sender": "agent", "text": "Let me check for you."}
        ],
        "output": {
            "categorization": "Requesting shipping status",
            "intent": "Order Status",
            "topic": "Shipping/Delivery",
            "sentiment": "Neutral"
        }
    },
    {
        "messages": [
            {"sender": "customer", "text": "I received a damaged product."},
            {"sender": "agent", "text": "I'm sorry to hear that. Would you like a replacement or refund?"}
        ],
        "output": {
            "categorization": "Product received damaged",
            "intent": "Return/Refund",
            "topic": "Returns",
            "sentiment": "Negative"
        }
    }
]

def build_prompt(conversation_number, aggregated_text):
    """
    Constructs the prompt for LLM classification.
    Includes strict instructions and 4 few-shot examples.
    Returns a dict with 'messages' or 'error'.
    """
    try:
        if not conversation_number or not aggregated_text:
            return {"error": "Invalid input: conversation_number and aggregated_text are required"}
        SYSTEM_PROMPT = (
            "You are a highly accurate customer-support query classifier.\n"
            "Your task is to classify the conversation into a short description, intent, topic, and sentiment.\n"
            "IMPORTANT:\n"
            "1. Use the **entire conversation** to determine intent and topic.\n"
            "2. Determine sentiment **ONLY from the customer's messages**.\n"
            "   - Positive: satisfaction, happiness, appreciation.\n"
            "   - Neutral: questions, clarifications, factual statements.\n"
            "   - Negative: frustration, anger, disappointment, urgency.\n"
            "3. Completely ignore the agent's tone for sentiment.\n"
            "4. Return a SINGLE JSON object **exactly** matching this schema:\n"
            "   - categorization: short descriptive summary of the customer issue.\n"
            f"   - intent: one of {INTENT_OPTIONS}\n"
            f"   - topic: one of {TOPIC_OPTIONS}\n"
            f"   - sentiment: one of {SENTIMENT_OPTIONS}\n"
            "5. NO extra keys, NO explanations, NO commentary, ONLY JSON.\n"
            "6. If unsure, make the best judgment based on customer words."
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        # Add few-shot examples as multi-turn user/assistant pairs
        for ex in FEW_SHOTS:
            # Combine all customer/agent messages into a single string for the user turn
            user_msgs = []
            for msg in ex["messages"]:
                if msg["sender"] == "customer":
                    user_msgs.append(f"Customer: {msg['text']}")
                elif msg["sender"] == "agent":
                    user_msgs.append(f"Agent: {msg['text']}")
            user_content = "\n".join(user_msgs)
            messages.append({"role": "user", "content": user_content})
            messages.append({"role": "assistant", "content": json.dumps(ex["output"], ensure_ascii=False)})
        # Add actual conversation
        user_query = f"Customer Query:\n{aggregated_text}\nReturn ONLY JSON:"
        messages.append({"role": "user", "content": user_query})
        return {"messages": messages}
    except Exception as e:
        return {"error": f"Prompt construction error: {str(e)}"}
