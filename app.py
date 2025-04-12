print("REMI is live — time to talk money!")

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
import spacy

# Load environment and NLP
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
nlp = spacy.load("en_core_web_sm")

# Flask Setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.secret_key = "supersecretkey"

# Initialize user profile
def init_profile():
    return {
        "age": None,
        "income": None,
        "savings": None,
        "expenses": None,
        "retirement_goal": None,
        "location": None
    }

# Extract financial details from user message
def update_profile(message, profile):
    doc = nlp(message.lower())
    for ent in doc.ents:
        if ent.label_ == "MONEY":
            if "income" not in profile or profile["income"] is None:
                profile["income"] = ent.text
            elif "savings" not in profile or profile["savings"] is None:
                profile["savings"] = ent.text
        if ent.label_ == "DATE" and "year" not in ent.text.lower():
            try:
                age_candidate = int(ent.text)
                if 10 < age_candidate < 100:
                    profile["age"] = age_candidate
            except:
                pass
    if "retire" in message and "retirement_goal" not in profile:
        profile["retirement_goal"] = "early retirement"
    return profile

# Build user profile summary
def profile_summary(profile):
    parts = []
    if profile["age"]:
        parts.append(f"Age: {profile['age']}")
    if profile["income"]:
        parts.append(f"Income: {profile['income']}")
    if profile["savings"]:
        parts.append(f"Savings: {profile['savings']}")
    if profile["expenses"]:
        parts.append(f"Expenses: {profile['expenses']}")
    if profile["retirement_goal"]:
        parts.append(f"Goal: {profile['retirement_goal']}")
    return " | ".join(parts) if parts else "No significant financial details provided yet."

@app.route("/analyze_budget", methods=["POST"])
def analyze_budget():
    try:
        data = request.json
        message = data.get("message", "")

        if "chat_history" not in session:
            session["chat_history"] = []
        if "user_profile" not in session:
            session["user_profile"] = init_profile()

        # Update profile
        session["user_profile"] = update_profile(message, session["user_profile"])

        # Handle vague inputs like "not sure"
        if "not sure" in message.lower() or "idk" in message.lower():
            reply = "No worries — let's work it out together! Can you give me a rough idea of your income, savings, or financial goal?"
            return jsonify({"response": reply})

        # Add to history
        session["chat_history"].append({
            "role": "user",
            "content": f"{message} (Current Profile: {profile_summary(session['user_profile'])})"
        })

        # Market insight (optional: you can enhance this part later)
        market_snippet = (
            "Markets are volatile today. The S&P 500 is stable, tech stocks are swinging. "
            "Consider diversification strategies and index funds for stability."
        )

        # Improved system prompt
        system_prompt = (
            "You are REMI (Real-time Economic & Money Insights), an elite AI financial advisor with a no-nonsense, witty, New York attitude. "
            "You do NOT hallucinate numbers. You ONLY reference the user's provided info or ask for clarification. "
            "Use the user's financial profile when answering. If unclear, ask for missing information. "
            f"Current user profile: {profile_summary(session['user_profile'])} "
            f"Market insight: {market_snippet} "
            "End every reply with a follow-up question to gather more useful financial information."
        )

        # Call Groq
        groq_response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}},
            json={
                "model": "llama3-70b-8192",
                "temperature": 0.3,
                "messages": [{"role": "system", "content": system_prompt}] + session["chat_history"]
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



