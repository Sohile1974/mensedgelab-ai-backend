from flask import Flask, request, jsonify
import os
import openai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/")
def home():
    return "Men's Edge Lab AI backend is running"

@app.route("/evaluate-photo", methods=["POST"])
def evaluate_photo():
    try:
        data = request.json
        print("🧩 Received data:", data)

        messages = data.get("messages", [])
        if not messages:
            return jsonify({"error": "Missing messages"}), 400

        # Step 1: Get image description
        print("⏳ Calling GPT Step 1 (Image Description)...")
        step1_response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
        image_description = step1_response.choices[0].message.content.strip()
        print("📸 Step 1 image summary:", image_description)

        # Step 2: Generate full evaluation
        print("⏳ Calling GPT Step 2 (Final Report)...")
        step2_prompt = f"""
This is a fitness evaluation request.

Image summary:
{image_description}

User physical data and goals:
{messages[0]['content'][0]['text']}

Please write a structured, medically-informed body photo evaluation focusing on:
1. Posture
2. Visible Fat Distribution
3. Muscle Definition
4. Overall Body Composition

End with a clear conclusion and motivational tone. Be realistic, professional, and detailed.
"""

        step2_response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": step2_prompt}
            ]
        )
        ai_report_content = step2_response.choices[0].message.content.strip()
        print("✅ Final AI Report:", ai_report_content)

        return jsonify({
            "status": "success",
            "report": ai_report_content
        })

    except Exception as e:
        print("❌ Error:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
