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

        user_age = int(re.search(r"user is (\d+)", user_prompt, re.IGNORECASE).group(1)) if re.search(r"user is (\d+)", user_prompt, re.IGNORECASE) else None
        user_height = int(re.search(r"(\d+)\s*cm", user_prompt).group(1)) if re.search(r"(\d+)\s*cm", user_prompt) else None
        user_weight = int(re.search(r"weighs (\d+)", user_prompt, re.IGNORECASE).group(1)) if re.search(r"weighs (\d+)", user_prompt, re.IGNORECASE) else None
        bmi = round(user_weight / ((user_height / 100) ** 2), 1) if user_height and user_weight else 0.0

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # 🔒 Step 1 – Image analysis (DO NOT TOUCH)
        step1_prompt_primary = (
            """Describe the person’s physique in this image for a fitness evaluation. This is a professional submission intended for body composition analysis. Focus on posture, muscle tone, and fat distribution. Do not make assumptions about identity or context. Do not refuse unless the image is clearly inappropriate or unviewable."""
        )
        step1_prompt_fallback = (
            "Describe the person in this image, including general body type, stance, posture, and muscle/fat visibility. "
            "Keep the tone factual and observational only."
        )

        def build_step1(prompt_text):
            return [{"role": "user", "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]}]

        print("⏳ Calling GPT Step 1...")
        try:
            step1_response = client.chat.completions.create(
                model="gpt-4o",
                messages=build_step1(step1_prompt_primary),
                timeout=12
            )
            visual_summary = step1_response.choices[0].message.content.strip()

            if "i'm sorry" in visual_summary.lower() or "cannot" in visual_summary.lower():
                print("⚠️ Primary prompt failed, retrying with fallback...")
                step1_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=build_step1(step1_prompt_fallback),
                    timeout=12
                )
                visual_summary = step1_response.choices[0].message.content.strip()

        except Exception as e:
            print("🔥 GPT Step 1 failed:", str(e))
            return make_response("⚠️ Image analysis failed. Please submit a clear, full-body fitness-style photo.", 200)

        if "i'm sorry" in visual_summary.lower() or "cannot" in visual_summary.lower():
            return make_response("⚠️ The submitted photo could not be evaluated. Please ensure it is well-lit, does not include sensitive content, and clearly shows your physique.", 200)

        # ✅ Step 2 – With Clean Formatting and Physique Score
        step2_prompt = f"""You are a professional AI fitness coach. Write a structured HTML report using only <strong>, <br>, <ul>, <li>. Do NOT use markdown, numbered lists, or divs. Format each section cleanly using consistent structure.

<strong>User Profile</strong><br>
Age: {user_age or 'Not provided'}<br>
Height: {user_height or 'Not provided'} cm<br>
Weight: {user_weight or 'Not provided'} kg<br>
BMI: {bmi:.1f} {'(calculated)' if bmi else ''}<br><br>

<strong>Image Summary</strong><br>
{visual_summary}<br><br>

<strong>Physique Score (Out of 100)</strong><br>
Assign a score between 0–100 based on visible fat, posture, symmetry, muscle definition, and BMI. Be strict but constructive. Justify the score in 1–2 sentences.<br><br>

<strong>Overall Impression</strong><br>
<ul>
<li>Evaluate posture, visual tone, and body proportions.</li>
<li>Identify key areas where improvement will produce biggest impact visually and medically.</li>
</ul><br>

<strong>Health Risk Analysis</strong><br>
<ul>
<li>BMI of {bmi:.1f} places you in the {'overweight' if bmi >= 25 else 'normal' if bmi >= 18.5 else 'underweight'} category.</li>
<li>Abdominal fat and postural imbalances raise risks for insulin resistance and back strain — act early.</li>
</ul><br>

<strong>Fat vs. Muscle Assessment</strong><br>
<ul>
<li><strong>Abdomen:</strong> Fat reduction here is top priority.</li>
<li><strong>Chest & Shoulders:</strong> Muscle tone exists — build on it to improve visual width and symmetry.</li>
<li><strong>Back & Legs:</strong> Add strength training to build posterior support and balance.</li>
</ul><br>

<strong>Customized Goals</strong><br>
<ul>
<li><strong>Fat Loss:</strong> Drop 6–8 kg to reach BMI 23–24.</li>
<li><strong>Muscle Gain:</strong> Prioritize shoulders, upper chest, and lats.</li>
<li><strong>Posture:</strong> Mobilize hips and strengthen glutes to fix anterior tilt.</li>
</ul><br>

<strong>Physique Refinement & Shape Optimization</strong><br>
<ul>
<li>Focus on upper torso width for stronger V-taper.</li>
<li>Train hamstrings and glutes to complete back profile.</li>
<li>Postural symmetry + muscle balance = visual authority.</li>
</ul><br>

<strong>Recommended Nutrition</strong><br>
<ul>
<li>Calorie deficit of ~500/day. Stay consistent for 3–4 weeks before adjusting.</li>
<li>Macros: 1.8–2.2 g/kg protein, moderate carbs, healthy fats.</li>
<li>Avoid sugars, oils, and fried foods. Track everything.</li>
</ul><br>

<strong>Next Steps</strong><br>
<ul>
<li>Train full-body 3×/week using compound lifts.</li>
<li>Do fasted walks or HIIT 2×/week — be consistent.</li>
<li>Track waist (cm), weight, and weekly photos.</li>
<li>Expect visible change in posture and waistline within 4–5 weeks.</li>
</ul><br>

<strong>Disclaimer</strong><br>
This report is generated by AI for educational purposes only. It does not constitute medical advice or replace consultation with a licensed professional.
"""

        print("⏳ Calling GPT Step 2...")
        try:
            step2_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [{"type": "text", "text": step2_prompt}]}],
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
