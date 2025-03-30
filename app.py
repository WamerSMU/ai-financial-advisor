print("Hello from the AI Financial Advisor!")

from dotenv import load_dotenv
import os
import requests
from flask import Flask, request, jsonify, session
from flask_cors import CORS

# Load API Key
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# Initialize Flask
app = Flask(__name__)
CORS(app)
app.secret_key = "supersecretkey"  # Needed for session tracking

@app.route("/")
def home():
    return jsonify({"message": "Welcome to the AI Financial Advisor API!"})

@app.route("/analyze_budget", methods=["POST"])
def analyze_budget():
    try:
        data = request.json

        # Extract user input
        income = data.get("income", 0)
        expenses = data.get("expenses", 0)
        savings_goal = data.get("savings_goal", 0)
        risk_tolerance = data.get("risk_tolerance", "medium")
        age = data.get("age")
        monthly_debt = data.get("monthly_debt")
        existing_savings = data.get("existing_savings")
        financial_goal = data.get("financial_goal")  # e.g., retirement, house, vacation

        disposable_income = income - expenses
        savings_rate = round((disposable_income / income) * 100, 2) if income else 0
        debt_to_income = round((monthly_debt / (income / 12)) * 100, 2) if monthly_debt and income else None

        if "chat_history" not in session:
            session["chat_history"] = []

        # Compose the user's financial summary
        user_message = (
            f"User earns ${income} annually, spends ${expenses}, with a savings goal of ${savings_goal}. "
            f"Their disposable income is ${disposable_income} and savings rate is {savings_rate}%. "
        )

        if age:
            user_message += f"They are {age} years old. "
        if debt_to_income is not None:
            user_message += f"Their debt-to-income ratio is {debt_to_income}%. "
        if existing_savings:
            user_message += f"They have ${existing_savings} in current savings. "
        if financial_goal:
            user_message += f"Their financial goal is: {financial_goal}. "

        user_message += f"Risk tolerance is {risk_tolerance}. Provide detailed, goal-specific, blunt financial advice."

        session["chat_history"].append({"role": "user", "content": user_message})

        # Optional market trend snippet (static or from another script)
        market_summary = (
            "Current market trends: Interest rates are high, tech stocks are volatile, and index funds remain stable."
        )

        # Prepare request for Groq
        groq_response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": (
                        "You are a sharp, straightforward AI financial advisor. "
                        "Give practical budgeting and investing advice based on the user's profile. "
                        f"Here is a snapshot of current market context: {market_summary}"
                    )}
                ] + session["chat_history"]
            }
        )

        ai_reply = groq_response.json().get("choices", [{}])[0].get("message", {}).get("content", "No response.")
        session["chat_history"].append({"role": "assistant", "content": ai_reply})

        return jsonify({"response": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render assigns this dynamically
    app.run(host="0.0.0.0", port=port)

