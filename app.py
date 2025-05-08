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

        # Extract user content blocks
        content_items = data["messages"][0]["content"]
        text_block = next(item for item in content_items if item["type"] == "text")
        image_block = next(item for item in content_items if item["type"] == "image_url")

        user_prompt = text_block["text"].strip()
        image_url = image_block["image_url"]["url"].strip()

        # Auto-trim excessive user input
        if len(user_prompt) > 500:
            user_prompt = user_prompt[:500] + "..."

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Step 1 – Image-based description
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

        print("⏳ Calling GPT Step 1 (Image Description)...")
        try:
            step1_response = client.chat.completions.create(
                model="gpt-4o",
                messages=step1_messages,
                timeout=12
            )
            visual_summary = step1_response.choices[0].message.content.strip()
            print("📸 Step 1 image summary:", visual_summary)
        except Exception as e:
            print("🔥 GPT Step 1 failed:", str(e))
            fallback = "⚠️ There was a problem analyzing the photo. Please try again with a clearer image."
            return make_response(jsonify({"content": fallback}), 200)

        # Handle GPT refusal
        if "i'm sorry" in visual_summary.lower() or "cannot" in visual_summary.lower():
            fallback = "⚠️ The submitted photo could not be evaluated. Please ensure it is well-lit, does not include sensitive content, and clearly shows your physique in a fitness-appropriate context."
            print("🚫 Image was refused by GPT. Returning fallback.")
            return make_response(jsonify({"content": fallback}), 200)

        # Step 2 – Full fitness evaluation
        step2_prompt = f"""This is a fitness evaluation request. Use the following image-based description to guide your analysis:
"{visual_summary}"

Now, also consider the user's input:
- {user_prompt}

Provide a medically realistic, strict, and goal-focused fitness evaluation structured with the following sections:
1. Overall Impression
2. Health Risk Analysis
3. Fat vs. Muscle Assessment
4. Customized Goals
5. Recommended Nutrition
6. Next Steps

Be direct, detailed, and serious in tone. Use bullet points where helpful. Avoid disclaimers or soft language."""

        step2_messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": step2_prompt
                    }
                ]
            }
        ]

        print("⏳ Calling GPT Step 2 (Final Report)...")
        try:
            step2_response = client.chat.completions.create(
                model="gpt-4o",
                messages=step2_messages,
                timeout=12
            )
            final_report = step2_response.choices[0].message.content.strip()
            print("✅ Final AI Report:", final_report)
        except Exception as e:
            print("🔥 GPT Step 2 failed:", str(e))
            final_report = "⚠️ We encountered an error generating your fitness evaluation. Please try again shortly or submit a new image."

        return make_response(jsonify({"content": final_report}), 200)

    except Exception as e:
        print("🔥 Error occurred:", str(e))
        return make_response(jsonify({"error": str(e)}), 500)

@app.route("/", methods=["GET"])
def index():
    return "Men's Edge Lab AI backend is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
