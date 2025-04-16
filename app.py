print("REMI is live — time to talk money!")

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import requests
import yfinance as yf
from dotenv import load_dotenv
import spacy

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

# Extract financial goal
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

# Check if user mentioned key facts
def extract_facts(message):
    facts = {}
    if "age" in session:
        facts["age"] = session["age"]
    if "savings" in session:
        facts["savings"] = session["savings"]

    # Extract basic new info
    doc = nlp(message.lower())
    for ent in doc.ents:
        if ent.label_ == "AGE" or ("years old" in message):
            try:
                age_value = int(''.join(filter(str.isdigit, ent.text)))
                session["age"] = age_value
                facts["age"] = age_value
            except:
                pass
        if "$" in ent.text or "k" in ent.text:
            try:
                text = ent.text.replace("$", "").replace("k", "000")
                savings_value = int(''.join(filter(str.isdigit, text)))
                session["savings"] = savings_value
                facts["savings"] = savings_value
            except:
                pass
    return facts

# Handle stock queries
def get_stock_price(message):
    tickers = {
        "apple": "AAPL",
        "tesla": "TSLA",
        "amazon": "AMZN",
        "google": "GOOGL",
        "meta": "META",
        "microsoft": "MSFT"
    }
    for key, symbol in tickers.items():
        if key in message.lower():
            try:
                stock = yf.Ticker(symbol)
                todays_data = stock.history(period='1d')
                price = todays_data['Close'].iloc[-1]
                return f"{key.capitalize()} (ticker {symbol}) is trading at around ${price:.2f} today."
            except:
                return f"Couldn't fetch real-time data for {key.capitalize()} right now."
    return None

@app.route("/analyze_budget", methods=["POST"])
def analyze_budget():
    try:
        data = request.json
        message = data.get("message")

        if "chat_history" not in session:
            session["chat_history"] = []

        if message:
            guessed_goal = extract_goal(message)
            extracted_facts = extract_facts(message)
            stock_info = get_stock_price(message)

            market_snippet = market_insights.get(guessed_goal, market_insights["unspecified"])
            user_message = f"{message}"
            if extracted_facts:
                facts_str = ", ".join(f"{k}: {v}" for k, v in extracted_facts.items())
                user_message += f" (Extracted facts: {facts_str})"

            if stock_info:
                session["chat_history"].append({"role": "assistant", "content": stock_info})

            session["chat_history"].append({"role": "user", "content": user_message})

        else:
            return jsonify({"response": "I didn't get a message to analyze!"})

        # System prompt
        system_prompt = (
            "You are REMI (Real-time Economic & Money Insights), an AI financial advisor with a sharp, New York edge. "
            "You don’t sugarcoat, and you don’t ramble. Be concise, witty, and give real strategies. "
            "Use real-time facts if available. NEVER assume facts the user hasn’t given you. "
            "If information is missing, ask for it instead of guessing. "
            f"Latest Market Insight: {market_snippet} "
            "Always end with a follow-up question."
        )

        # Groq API call
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







