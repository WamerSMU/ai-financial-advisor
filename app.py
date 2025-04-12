print("REMI is live — time to talk money!")

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import requests
import yfinance as yf
from dotenv import load_dotenv
import spacy
from datetime import datetime

# Load environment and NLP
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
nlp = spacy.load("en_core_web_sm")

# Market Insight Snippets
market_insights = {
    "retirement": "Inflation is outpacing traditional savings. Consider Roth IRAs or diversified ETFs.",
    "home": "Mortgage rates are still above average. First-time buyer programs or ARM loans could be a move.",
    "vacation": "Travel prices are up, but points/rewards cards may offset. Smart budgeting = smarter play.",
    "education": "Student loan rates are brutal. 529s and education tax credits are your best friend.",
    "unspecified": "Markets are jittery. Index funds remain stable while tech sees swings."
}

# Flask Setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.secret_key = "supersecretkey"

# Utility: NLP financial goal extraction
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

# Real-time stock price fetch
def get_stock_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        todays_data = ticker.history(period="1d")
        price = todays_data['Close'].iloc[-1]
        return round(price, 2)
    except:
        return None

# Analyze User Request
@app.route("/analyze_budget", methods=["POST"])
def analyze_budget():
    try:
        data = request.json
        message = data.get("message", "").lower()

        if "chat_history" not in session:
            session["chat_history"] = []
        if "user_profile" not in session:
            session["user_profile"] = {}

        # Store structured user data if given
        for field in ["age", "income", "savings", "monthly_expenses", "debt", "risk_tolerance", "financial_goal"]:
            if field in data and data[field]:
                session["user_profile"][field] = data[field]

        # Handle user question about stocks
        if any(keyword in message for keyword in ["stock", "apple", "google", "amazon", "market today", "nasdaq", "s&p"]):
            today = datetime.now().strftime("%B %d, %Y")
            if "apple" in message:
                price = get_stock_price("AAPL")
                if price:
                    reply = f"As of {today}, Apple's stock is trading around ${price}."
                else:
                    reply = "Sorry, I couldn't fetch Apple's current stock price right now."
            elif "google" in message:
                price = get_stock_price("GOOGL")
                if price:
                    reply = f"As of {today}, Google's stock is trading around ${price}."
                else:
                    reply = "Sorry, I couldn't fetch Google's stock price right now."
            elif "amazon" in message:
                price = get_stock_price("AMZN")
                if price:
                    reply = f"As of {today}, Amazon's stock is trading around ${price}."
                else:
                    reply = "Sorry, I couldn't fetch Amazon's stock price right now."
            else:
                reply = f"As of {today}, markets are a bit jittery. Tech stocks are moving, index funds remain steady."
            
            session["chat_history"].append({"role": "assistant", "content": reply})
            return jsonify({"response": reply})

        # Build dynamic system prompt
        profile_summary = " ".join([f"{k.capitalize()}: {v}." for k, v in session["user_profile"].items()])

        market_snippet = market_insights.get(
            extract_goal(message), market_insights["unspecified"]
        )

        system_prompt = (
            f"You are REMI (Real-time Economic & Money Insights), an AI financial advisor with a sharp, New York edge. "
            f"User info: {profile_summary} "
            f"Market update: {market_snippet} "
            "NEVER make up facts. "
            "If you don't know something, ask for more info from the user. "
            "Be realistic, concise, witty, and end each response with a question."
        )

        # Call Groq
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
        session["chat_history"].append({"role": "user", "content": message})
        session["chat_history"].append({"role": "assistant", "content": ai_reply})

        return jsonify({"response": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)





