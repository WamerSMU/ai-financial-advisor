print("REMI is live — smarter, faster, and sharper!")

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
import spacy
import yfinance as yf

# Load environment and NLP
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
nlp = spacy.load("en_core_web_sm")

# Flask Setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.secret_key = "supersecretkey"

# Financial Goal Keywords
goal_map = {
    "retirement": ["retire", "retirement"],
    "home": ["house", "home", "mortgage"],
    "vacation": ["trip", "vacation", "travel", "holiday"],
    "education": ["college", "university", "school", "degree"]
}

# Get Live Market Data
def get_market_snapshot():
    try:
        sp500 = yf.Ticker("^GSPC").history(period="1d")["Close"].iloc[-1]
        nasdaq = yf.Ticker("^IXIC").history(period="1d")["Close"].iloc[-1]
        dow = yf.Ticker("^DJI").history(period="1d")["Close"].iloc[-1]
        return f"S&P 500: {sp500:.2f}, NASDAQ: {nasdaq:.2f}, Dow Jones: {dow:.2f}"
    except Exception as e:
        return "Markets are currently volatile. Live data unavailable."

# Extract Financial Goal from Message
def extract_goal(message):
    doc = nlp(message.lower())
    for token in doc:
        for goal, keywords in goal_map.items():
            if token.lemma_ in keywords:
                return goal
    return "unspecified"

# Update session with known user facts
def update_user_facts(message):
    if "user_facts" not in session:
        session["user_facts"] = {}

    # Simple rule-based updates
    lowered = message.lower()
    if "i am " in lowered or "i'm " in lowered:
        if "year" in lowered and any(num.isdigit() for num in lowered):
            for word in lowered.split():
                if word.isdigit() and 10 < int(word) < 100:
                    session["user_facts"]["age"] = int(word)

    if "saving" in lowered or "$" in lowered:
        for word in lowered.replace(",", "").split():
            if word.startswith("$") and word[1:].isdigit():
                session["user_facts"]["savings"] = int(word[1:])
            elif word.isdigit():
                session["user_facts"]["savings"] = int(word)

    if "income" in lowered:
        for word in lowered.replace(",", "").split():
            if word.startswith("$") and word[1:].isdigit():
                session["user_facts"]["income"] = int(word[1:])
            elif word.isdigit():
                session["user_facts"]["income"] = int(word)

@app.route("/analyze_budget", methods=["POST"])
def analyze_budget():
    try:
        data = request.json
        message = data.get("message")

        if "chat_history" not in session:
            session["chat_history"] = []

        if message:
            # Update facts
            update_user_facts(message)

            # Detect goal
            guessed_goal = extract_goal(message)

            # Get market live
            market_snippet = get_market_snapshot()

            # Store in chat history
            session["chat_history"].append({
                "role": "user",
                "content": f"{message} (Detected goal: {guessed_goal})"
            })

        else:
            return jsonify({"error": "No message provided"}), 400

        # Build custom system prompt with memory
        user_facts_summary = " | ".join([f"{k}: {v}" for k, v in session.get("user_facts", {}).items()]) if session.get("user_facts") else "None yet."
        
        system_prompt = (
            f"You are REMI (Real-time Economic & Money Insights), an AI financial advisor with a sharp, witty New York edge. "
            f"Be concise, no sugarcoating. "
            f"Market snapshot: {market_snippet}. "
            f"Known user facts: {user_facts_summary}. "
            "Rules: NEVER make up facts. If missing important details, politely ask for them. "
            "NEVER assume savings, age, income unless the user provides it. "
            "End every reply with a short follow-up question to keep the conversation alive."
        )

        # Call Groq API
        groq_response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama3-70b-8192",
                "temperature": 0.3,
                "messages": [
                    {"role": "system", "content": system_prompt}
                ] + session["chat_history"]
            }
        )

        ai_reply = groq_response.json().get("choices", [{}])[0].get("message", {}).get("content", "No response.")
        session["chat_history"].append({"role": "assistant", "content": ai_reply})

        return jsonify({"response": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


