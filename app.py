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

        # ✅ Step 2 – Final report
        step2_prompt = f"""You are a professional AI fitness coach. Generate a structured HTML report using only <strong>, <br>, <ul>, <li>. Avoid markdown. Make your language motivating, realistic, and tailored to the user's profile.

<strong>User Profile</strong><br>
Age: {user_age or 'Not provided'}<br>
Height: {user_height or 'Not provided'} cm<br>
Weight: {user_weight or 'Not provided'} kg<br>
BMI: {bmi:.1f} {'(calculated)' if bmi else ''}<br><br>

<strong>Image Summary</strong><br>
{visual_summary}<br><br>

<strong>Overall Impression</strong><br>
Summarize the individual’s visible shape, posture alignment, muscle tone, symmetry, and fat distribution. Use confident phrasing.<br><br>

<strong>Health Risk Analysis</strong><br>
<ul>
<li>BMI of {bmi:.1f} places this user in the {'overweight' if bmi >= 25 else 'normal' if bmi >= 18.5 else 'underweight'} category.</li>
<li>Address specific risks for cardiovascular or orthopedic concerns based on abdominal fat or visible postural issues, especially for age {user_age or '?'}.</li>
</ul><br>

<strong>Fat vs. Muscle Assessment</strong><br>
<ul>
<li><strong>Abdomen:</strong> Assess the amount of fat present and whether it should be prioritized for visual and health reasons.</li>
<li><strong>Upper Body:</strong> Evaluate shoulder and chest symmetry and suggest if more hypertrophy is needed.</li>
<li><strong>Legs & Back:</strong> Analyze muscular balance and visual proportion from front and side views.</li>
</ul><br>

<strong>Customized Goals</strong><br>
<ul>
<li><strong>Fat Loss:</strong> With {user_weight} kg and BMI {bmi:.1f}, aim to reduce 6–8 kg to target BMI 23–24 range.</li>
<li><strong>Muscle Gain:</strong> Prioritize upper chest, shoulders, and arms to improve shape and balance.</li>
<li><strong>Posture:</strong> Recommend core training and scapular drills to fix anterior tilt or shoulder rounding.</li>
</ul><br>

<strong>Physique Refinement & Shape Optimization</strong><br>
<ul>
<li>Widen the upper frame with shoulder and upper chest work to enhance V-taper.</li>
<li>Add glute/hamstring training to support symmetry in side view.</li>
<li>Posture and waist taper are top aesthetic priorities for men 40+ — reinforce these.</li>
</ul><br>

<strong>Recommended Nutrition</strong><br>
<ul>
<li>Daily intake: Begin with a ~500 kcal deficit from estimated maintenance.</li>
<li>Macros: 1.8–2.0 g/kg protein, moderate carbs, and healthy fats like olive oil or nuts.</li>
<li>Best foods: Chicken, salmon, eggs, oats, dark greens. Remove fried or sugary options.</li>
</ul><br>

<strong>Next Steps</strong><br>
<ul>
<li>Strength: Train full-body 3×/week with progressive overload on compound movements.</li>
<li>Conditioning: Perform 2×/week HIIT or 30 min fasted walks.</li>
<li>Tracking: Weekly photos, waist (cm), weight. Adjust nutrition if stalled for 3+ weeks.</li>
<li>Expected outcome: Noticeable visual changes in 4 weeks with consistent execution.</li>
<li>Supplemental: Whey, creatine, D3 if not met via diet/lifestyle.</li>
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
