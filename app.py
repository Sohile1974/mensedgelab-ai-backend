from flask import Flask, request, make_response
import openai
import os
import re

app = Flask(__name__)

def extract_number_from_text(text, key):
    pattern = rf"{key}[^0-9]*(\d+)"
    match = re.search(pattern, text, re.IGNORECASE)
    return int(match.group(1)) if match else None

@app.route("/evaluate-photo", methods=["POST"])
def evaluate_photo():
    try:
        print("✅ Received POST request to /evaluate-photo")

        data = request.get_json(force=True)
        print("🧩 Received data:", data)

        if not data or "messages" not in data:
            print("❌ 'messages' field is missing.")
            return make_response("❌ 'messages' field is missing.", 400)

        # Extract text + image from OpenAI chat format
        content_items = data["messages"][0]["content"]
        text_block = next(item for item in content_items if item["type"] == "text")
        image_block = next(item for item in content_items if item["type"] == "image_url")

        user_prompt = text_block["text"].strip()
        image_url = image_block["image_url"]["url"].strip()

        # Auto-trim overly long inputs
        if len(user_prompt) > 500:
            user_prompt = user_prompt[:500] + "..."

        # Extract metrics from user input if available
        user_age = extract_number_from_text(user_prompt, "age")
        user_height = extract_number_from_text(user_prompt, "height")  # in cm
        user_weight = extract_number_from_text(user_prompt, "weight")  # in kg

        bmi = (user_weight / ((user_height / 100) ** 2)) if user_height and user_weight else 0.0

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Step 1 – Image analysis
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
            return make_response("⚠️ Image analysis failed. Please submit a clear, full-body fitness-style photo.", 200)

        # Check if GPT refused to analyze
        if "i'm sorry" in visual_summary.lower() or "cannot" in visual_summary.lower():
            fallback = "⚠️ The submitted photo could not be evaluated. Please ensure it is well-lit, does not include sensitive content, and clearly shows your physique."
            return make_response(fallback, 200)

        # Step 2 – Full evaluation
        step2_prompt = f"""You are generating a personalized body evaluation report based on a submitted photo and user-provided metrics.

User Profile:
- Age: {user_age or 'Not provided'}
- Height: {user_height or 'Not provided'} cm
- Weight: {user_weight or 'Not provided'} kg
- BMI: {bmi:.1f} {"(calculated)" if bmi else ""}

Image Summary:
"{visual_summary}"

Now generate a direct, structured, and medically realistic fitness evaluation using the following format (use line breaks and bold titles):

**Overall Impression**  
[Short summary of posture, body shape, and muscular tone.]

**Health Risk Analysis**  
[Discuss visible risks, BMI interpretation, and lifestyle-related concerns.]

**Fat vs. Muscle Assessment**  
[Evaluate body composition and visible muscle/fat balance.]

**Customized Goals**  
[Define fat-loss, muscle-gain, or recomposition goals.]

**Recommended Nutrition**  
[Provide nutrition guidelines for their goal.]

**Next Steps**  
[Motivating advice with specific training actions.]

Be strict but encouraging. Use bullet points and short paragraphs. Avoid generic disclaimers.
"""

        step2_messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": step2_prompt}]
            }
        ]

        print("⏳ Calling GPT Step 2 (Final Report)...")
        try:
            step2_response = client.chat.completions.create(
                model="gpt-4o",
                messages=step2_messages,
                timeout=15
            )
            final_report = step2_response.choices[0].message.content.strip()
            print("✅ Final Report Generated.")
        except Exception as e:
            print("🔥 GPT Step 2 failed:", str(e))
            final_report = "⚠️ We encountered an error generating your evaluation. Please try again shortly."

        return make_response(final_report, 200)

    except Exception as e:
        print("🔥 Unexpected error:", str(e))
        return make_response(f"⚠️ Internal server error: {str(e)}", 500)

@app.route("/", methods=["GET"])
def index():
    return "Men's Edge Lab AI backend is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
