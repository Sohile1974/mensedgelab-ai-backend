from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/evaluate-photo", methods=["POST"])
def analyze_photo():
    data = request.get_json()
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=data["messages"]
    )
    return jsonify(response["choices"][0]["message"])

@app.route("/", methods=["GET"])
def index():
    return "Men's Edge Lab AI backend is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

