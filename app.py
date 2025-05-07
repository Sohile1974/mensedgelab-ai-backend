import openai
import os
from flask import Flask, request, jsonify

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/evaluate-photo", methods=["POST"])
def analyze_photo():
    data = request.get_json()

    if not data or "messages" not in data:
        return jsonify({"error": "'messages' field is missing."}), 400

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=data["messages"],
            timeout=25  # set a timeout (in seconds)
        )
        return jsonify(response["choices"][0]["message"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def index():
    return "Men's Edge Lab AI backend is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

