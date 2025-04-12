print("REMI is live — time to talk money!")

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import requests
from dotenv import load_dotenv
import spacy
import yfinance as yf
from datetime import datetime

# Load env & spaCy
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
nlp = spacy.load("en_core_web_sm")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.secret_key = "supersecretkey"

# 🔍 Real-time stock data
def get_stock_price(symbol):
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")
        if not data.empty:
            price = round(data["Close"].iloc[-1], 2)
            return f"{symbol.upper()} is trading at ${price} as of {datetime.now().strftime('%Y-%m-%d')}."
    except Exception:
        pass
    return f"Sorry, I couldn't fetch data for {symbol.upper()}."

# 🧠 Extract goal via NLP
def extract_goal(message):
    doc = nlp(message.lower())
    goal_map = {
        "retirement": ["retire", "retirement"],
        "home": ["house", "home", "mortgage"],
        "vacation": ["trip", "vacation", "travel", "holiday"],
        "education": ["college", "university", "school", "degree"],
    }
    for token in doc:
        for goal, keywords in goal_map.items():
            if token.lemma_ in keywords:
                return goal
    return "unspecified"

# 🧠 Update user memory
def update_user_profile(data):
    if "user_profile" not in session:
        session["user_profile"] = {}

    profile = session["user_profile"]
    fields = ["age", "income", "expenses", "savings_goal", "monthly_debt", "existing_savings", "financial_goal", "risk_tolerance"]
    for field in fields:
        value = data.get(field)
        if value:
            profile[field] = value
    session["user_profile"] = profile

def build_context_string():
    profile = session.get("user_profile", {})
    if not profile:
        return ""
    context = "Here’s what I know so far about the user:\n"
    for k, v in profile.items():
        context += f"- {k.replace('_', ' ').title()}: {v}\n"
    return context.strip()

@app.route("/analyze_budget", methods=["POST"])
def analyze_budget():
    try:
        data = request.json
        message = data.get("message", "")
        if "chat_history" not in session:
            session["chat_history"] = []

        # 🧠 If structured input, update memory
        update_user_profile(data)

        # 🧠 If stock lookup
        if "stock" in data:
            symbol = data["stock"]
            stock_response = get_stock_price(symbol)
            return jsonify({"response": stock_response})

        # 🧠 If chat input, process goal and message
        guessed_goal = extract_goal(message)
        market_insights = {
            "retirement": "Inflation is outpacing traditional savings. Consider Roth IRAs or diversified ETFs.",
            "home": "Mortgage rates are still above average. First-time buyer programs or ARM loans could be a move.",
            "vacation": "Travel prices are up, but points/rewards cards may offset. Smart budgeting = smarter play.",
            "education": "Student loan rates are brutal. 529s and education tax credits are your best friend.",
            "unspecified": "Markets are jittery. Index funds remain stable while tech sees swings."
        }
        market_snippet = market_insights.get(guessed_goal, market_insights["unspecified"])

        # Add message to chat
        session["chat_history"].append({
            "role": "user",
            "content": f"{message} (Detected goal: {guessed_goal})"
        })

        # 🧠 System Prompt with memory + market context
        system_prompt = (
            f"You are REMI, a witty, blunt, New York-style financial advisor. "
            f"{build_context_string()}\n"
            "Never guess anything you don't know. Ask if you're unsure. "
            f"Market snapshot: {market_snippet}\n"
            "Always end with a follow-up question."
        )

        # 🧠 Call Groq
        groq_response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
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






