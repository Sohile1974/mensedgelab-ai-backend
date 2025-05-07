from flask import Flask, request, jsonify, make_response
import openai
import os

app = Flask(__name__)

@app.route("/evaluate-photo", methods=["POST"])
def evaluate_photo():
    try:
        print("✅ Received POST request to /evaluate-photo")

        data = request.get_json(force=True)
        print("🧩 Received data:", data)

        if not data or "messages" not in data:
            print("❌ 'messages' field is missing.")
            return make_response(jsonify({"error": "'messages' field is missing."}), 400)

        # Extract user data from the first message
        content_items = data["messages"][0]["content"]
        text_block = next(item for item in content_items if item["type"] == "text")
        image_block = next(item for item in content_items if item["type"] == "image_url")

        user_prompt = text_block["text"]
        image_url = image_block["image_url"]["url"]

        # Step 1 – Describe the body visually (image only)
        step1_messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe the body in this image in terms of visible fat distribution, muscle tone, body shape, and posture. Do not make assumptions about health or identity."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ]

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        print("⏳ Calling GPT Step 1 (Image Description)...")
        step1_response = client.chat.completions.create(
            model="gpt-4o",
            messages=step1_messages,
            timeout=12
        )

        visual_summary = step1_response.choices[0].message.content
        print("📸 Step 1 image summary:", visual_summary)

        # Check for refusal in Step 1
        if "i'm sorry" in visual_summary.lower() or "cannot" in visual_summary.lower():
            fallback = "⚠️ The submitted photo could not be evaluated. Please ensure it is well-lit, does not include sensitive content, and clearly shows your physique in a fitness-appropriate context."
            print("🚫 Image was refused by GPT. Returning fallback.")
            return make_response(jsonify({"content": fallback}), 200)

        # Step 2 – Final fitness evaluation using visual + metrics
        step2_prompt = f"""
T
