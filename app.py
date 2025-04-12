print("REMI is live — time to talk money!")

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import requests
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# Flask setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.secret_key = "supersecretkey"

# Market Insight Snippets
market_insights = {
    "retirement": "Inflation is outpacing traditional savings. Consider Roth IRAs or diversified ETFs.",
    "home": "Mortgage rates are still above average. First-time buyer programs or ARM loans could be a move.",
    "vacation": "Travel prices are up, but points/rewards cards may offset. Smart budgeting = smarter play.",
    "education": "Student loan rates are brutal. 529s and education tax credits are your best friend.",
    "unspecified": "Markets are jittery. Index funds remain stable while tech sees swings."
}

# Helper: Get today's real date
def get_today_date():
    return datetime.now().strftime("%B %d, %Y")

# Helper: Get real-time stock price
def get_stock_price(ticker="AAPL"):
    try:
        data = yf.download(ticker, period="1d", interval="1m", progress=False)
        if not data.empty:
            latest_price = round(data["Close"].iloc[-1], 2)
            return latest_price
        else:
            return None
    except Exception:
        return None

# Main endpoint
@app.route("/analyze_budget", methods=["POST"])
def analyze_budget():
    try:
        data = request.json
        message = data.get("message")

        if "chat_history" not in session:
            session["chat_history"] = []

        if "user_memory" not in session:
            session["user_memory"] = {}

        # Check if user is giving structured data
        if message:
            session["chat_history"].append({
                "role": "user",
                "content": message
            })

            # Try to extract basic info (very simple parsing)
            lowered = message.lower()
            if "i am" in lowered and "years old" in lowered:
                try:
                    age = int([word for word in lowered.split() if word.isdigit()][0])
                    session["user_memory"]["age"] = age
                except:
                    pass
            if "income" in lowered or "make" in lowered:
                try:
                    income = int([word.replace(",", "") for word in lowered.split() if word.replace(",", "").isdigit()][0])
                    session["user_memory"]["income"] = income
                except:
                    pass
            if "saved" in lowered or "savings" in lowered:
                try:
                    savings = int([word.replace(",", "") for word in lowered.split() if word.replace(",", "").isdigit()][0])
                    session["user_memory"]["savings"] = savings
                except:
                    pass

            # Check if they ask about Apple stock
            if "apple stock" in lowered:
                price = get_stock_price("AAPL")
                today = get_today_date()
                if price:
                    stock_message = f"As of {today}, Apple (AAPL) is trading around ${price}."
                else:
                    stock_message = "Sorry, I couldn't fetch real-time Apple stock data at the moment."
                session["chat_history"].append({
                    "role": "assistant",
                    "content": stock_message
                })

        # Build dynamic system prompt
        today = get_today_date()
        user_info = ""
        if session["user_memory"]:
            for k, v in session["user_memory"].items():
                user_info += f"{k.capitalize()}: {v}. "

        system_prompt = (
            f"You are REMI (Real-time Economic & Money Insights), an AI financial advisor with a sharp, New York edge. "
            f"Today is {today}. {user_info}"
            "You don’t sugarcoat, and you don’t ramble. Be concise, witty, and give real strategies. "
            "NEVER assume facts the user hasn’t given you. "
            "NEVER make up numbers. "
            "If you're unsure, ask a clarifying question. "
            "DO NOT guess financial data. "
            "If the input is unclear, ask for more detail. "
            "End every reply with a quick follow-up question to keep the convo going."
        )

        # Make request to Groq
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




