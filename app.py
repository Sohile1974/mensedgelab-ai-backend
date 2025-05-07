from flask import Flask, request, jsonify, make_response
import openai
import os

app = Flask(__name__)

@app.route("/evaluate-photo", methods=["POST"])
def analyze_photo():
    try:
        print("✅ Received POST request to /evaluate-photo")

        data = request.get_json(force=True)
        print("🧩 Received data:", data)

        if not data or "messages" not in data:
            print("❌ 'messages' field is missing.")
            return make_response(jsonify({"error": "'messages' field is missing."}), 400)

        # Initialize OpenAI client
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        print("⏳ Sending request to OpenAI...")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=data["messages"],
            timeout=25  # Prevent long processing delays
        )

        result = {
            "choices": [
                response.choices[0].message.dict()
            ]
        }

        print("✅ GPT result:", result)

        # Send back a proper JSON response
        res = make_response(jsonify(result), 200)
        res.headers["Content-Type"] = "application/json"
        return res

    except Exception as e:
        print("🔥 Error occurred:", str(e))
        return make_response(jsonify({"error": str(e)}), 500)

@app.route("/", methods=["GET"])
def index():
    return "Men's Edge Lab AI backend is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
