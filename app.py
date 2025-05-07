from flask import Flask, request, jsonify, make_response
import openai
import os

app = Flask(__name__)

@app.route("/evaluate-photo", methods=["POST"])
def analyze_photo():
    try:
        data = request.get_json(force=True)
        if not data or "messages" not in data:
            return make_response(jsonify({"error": "Missing 'messages'"}), 400)

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=data["messages"],
            timeout=25
        )

        result = {
            "choices": [
                response.choices[0].message.dict()
            ]
        }

        # Debug print to console (for Render logs)
        print("✅ GPT result:", result)

        # Force JSON response with correct header
        res = make_response(jsonify(result), 200)
        res.headers["Content-Type"] = "application/json"
        return res

    except Exception as e:
        print("❌ Error:", str(e))
        return make_response(jsonify({"error": str(e)}), 500)

@app.route("/", methods=["GET"])
def index():
    return "Men's Edge Lab AI backend is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


