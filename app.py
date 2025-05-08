from flask import Flask, request, make_response
import openai
import os
import re

app = Flask(__name__)

@app.route("/evaluate-photo", methods=["POST"])
def evaluate_photo():
    try:
        print("✅ Received POST request to /evaluate-photo")

        data = request.get_json(force=True)
        print("🧩 Received data:", data)

        if not data or "messages" not in data:
            print("❌ 'messages' field is missing.")
            return make_response("❌ 'messages' field is missing.", 400)

        content_items = data["messages"][0]["content"]
        text_block = next(item for item in content_items if item["type"] == "text")
        image_block = next(item for item in content_items if item["type"] == "image_url")

        user_prompt = text_block["text"].strip()
        image_url = image_block["image_url"]["url"].strip()

        if len(user_prompt) > 500:
            user_prompt = user_prompt[:500] + "..."

        # ✅ Improved metric extraction from natural text
        user_age = int(re.search(r"user is (\d+)", user_prompt).group(1)) if re.search(r"user is (\d+)", user_prompt) else None
        user_height = int(re.search(r"(\d+)\s*cm", user_prompt).group(1)) if re.search(r"(\d+)\s*cm", user_prompt) else None
        user_weight = int(re.search(r"weighs (\d+)", user_prompt).group(1)) if re.search(r"weighs (\d+)", user_prompt) else None
        bmi = (user_weight / ((user_height / 100) ** 2)) if user_height and user_weight else 0.0

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Step 1 – Image description
        step1_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe the body in this image in terms of visible fat distribution, muscle tone, body shape, and posture. Do not make assumptions about health or identity."},
                    {"type": "image_url", "image_url": {"url": image_url}}
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

        if "i'm sorry" in visual_summary.lower() or "cannot" in visual_summary.lower():
            return make_response("⚠️ The submitted photo could not be evaluated. Please ensure it is well-lit, does not include sensitive content, and clearly shows your physique.", 200)

        # Step 2 – Final report generation
        step2_prompt = f"""You are generating a personalized HTML fitness evaluation report based on a user's body image and self-reported physical data.

<strong>User Profile</strong><br>
Age: {user_age or 'Not provided'}<br>
Height: {user_height or 'Not provided'} cm<br>
Weight: {user_weight or 'Not provided'} kg<br>
BMI: {bmi:.1f} {"(calculated)" if bmi else ""}<br><br>

<strong>Image Summary</strong><br>
{visual_summary}<br><br>

Now return only the fitness evaluation body using this exact structure with <strong>, <br>, <ul>, <li>. Do NOT include full HTML like <html>, <head>, or <body> tags.

<strong>Overall Impression</strong><br>
[Summary of posture, body shape, tone]<br><br>

<strong>Health Risk Analysis</strong><br>
[Address age, weight, and BMI risks]<br><br>

<strong>Fat vs. Muscle Assessment</strong><br>
[Evaluate visible composition]<br><br>

<strong>Customized Goals</strong><br>
<ul>
<li>Fat loss target</li>
<li>Muscle gain or tone improvement</li>
<li>Corrective posture or balance</li>
</ul><br>

<strong>Recommended Nutrition</strong><br>
<ul>
<li>Calorie guidelines</li>
<li>Macronutrient balance</li>
<li>Food types to focus on</li>
</ul><br>

<strong>Next Steps</strong><br>
<ul>
<li>Training schedule</li>
<li>Progress tracking tips</li>
<li>Optional coaching or plan refinement</li>
</ul>
"""

        step2_messages = [
            {"role": "user", "content": [{"type": "text", "text": step2_prompt}]}
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
