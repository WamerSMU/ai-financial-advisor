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

@app.route("/analyze_budget", methods=["POST"])
def analyze_budget():
    try:
        data = request.json
        message = data.get("message")

        if "chat_history" not in session:
            session["chat_history"] = []

        if message:
            guessed_goal = extract_goal(message)
            market_snippet = market_insights.get(guessed_goal, market_insights["unspecified"])
            session["chat_history"].append({
                "role": "user",
                "content": f"{message} (Detected goal: {guessed_goal})"
            })
        else:
            # Structured JSON input
            income = data.get("income", 0)
            expenses = data.get("expenses", 0)
            savings_goal = data.get("savings_goal", 0)
            risk_tolerance = data.get("risk_tolerance", "medium")
            age = data.get("age")
            monthly_debt = data.get("monthly_debt")
            existing_savings = data.get("existing_savings")
            financial_goal = data.get("financial_goal", "unspecified")

            disposable_income = income - expenses
            savings_rate = round((disposable_income / income) * 100, 2) if income else 0
            debt_to_income = round((monthly_debt / (income / 12)) * 100, 2) if monthly_debt and income else None

            market_snippet = market_insights.get(financial_goal, market_insights["unspecified"])

            user_message = (
                f"User earns ${income}/yr, spends ${expenses}, wants to save ${savings_goal}. "
                f"Disposable: ${disposable_income}, Savings rate: {savings_rate}%. "
            )
            if age:
                user_message += f"Age: {age}. "
            if debt_to_income is not None:
                user_message += f"DTI: {debt_to_income}%. "
            if existing_savings:
                user_message += f"Current savings: ${existing_savings}. "
            if financial_goal:
                user_message += f"Financial goal: {financial_goal}. "

            user_message += f"Risk: {risk_tolerance}. Be blunt, realistic, helpful."

            session["chat_history"].append({"role": "user", "content": user_message})

        # Enhanced system prompt with hallucination filters
        system_prompt = (
            "You are REMI (Real-time Economic & Money Insights), an AI financial advisor with a sharp, New York edge. "
            "You don’t sugarcoat, and you don’t ramble. Be concise, witty, and give real strategies. "
            f"Market snapshot: {market_snippet} "
            "NEVER assume facts the user hasn’t given you. "
            "NEVER make up numbers. "
            "If you're unsure, ask a clarifying question. "
            "DO NOT guess financial data. "
            "If the input is unclear, ask for more detail. "
            "End every reply with a quick follow-up question to keep the convo going."
        )

        groq_response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama3-8b-8192",
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




