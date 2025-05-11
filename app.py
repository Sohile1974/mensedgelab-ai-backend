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

        # ✅ Step 2 – Enhanced Report with Advanced Sections
        step2_prompt = f"""You are a professional AI fitness coach. Write a structured HTML report using <strong>, <br>, <ul>, <li> only (no markdown). Your tone should be clear, confident, direct, and medically realistic.

<strong>User Profile</strong><br>
Age: {user_age or 'Not provided'}<br>
Height: {user_height or 'Not provided'} cm<br>
Weight: {user_weight or 'Not provided'} kg<br>
BMI: {bmi:.1f} {'(calculated)' if bmi else ''}<br><br>

<strong>Image Summary</strong><br>
{visual_summary}<br><br>

<strong>Overall Impression</strong><br>
Describe posture, body shape, visible muscle tone, symmetry, and fat distribution.<br><br>

<strong>Health Risk Analysis</strong><br>
Based on the BMI of {bmi:.1f} and age {user_age or '?'}:
<ul>
<li>Explain clearly whether BMI falls in normal, overweight, or obese range.</li>
<li>Mention how this affects risk for cardiovascular, metabolic, or orthopedic issues (e.g., posture-related pain, diabetes risk).</li>
</ul><br>

<strong>Fat vs. Muscle Assessment</strong><br>
<ul>
<li><strong>Abdomen:</strong> fat presence or tone visibility</li>
<li><strong>Chest/Shoulders:</strong> muscle size and symmetry</li>
<li><strong>Back and Legs:</strong> development or imbalances</li>
</ul><br>

<strong>Customized Goals</strong><br>
<ul>
<li><strong>Fat Loss:</strong> Suggest realistic target (e.g., 5–10% body fat or kg range)</li>
<li><strong>Muscle Development:</strong> Emphasize visible weak points (chest, arms, glutes, etc.)</li>
<li><strong>Postural Corrections:</strong> Recommend rehab or mobility work if posture is off</li>
</ul><br>

<strong>What Still Needs Improvement</strong><br>
<ul>
<li>Highlight remaining weaknesses in symmetry, posture, or body proportions</li>
<li>Call out any region still underdeveloped or with excess fat, even if minor</li>
<li>Point out the pace of progress and areas needing more discipline or structure</li>
</ul><br>

<strong>Physique Refinement & Shape Optimization</strong><br>
<ul>
<li>Explain how to visually enhance V-taper, chest fullness, or midsection tightening</li>
<li>Include recommendations for exercises or angles to improve silhouette</li>
<li>Reinforce shape-driven strategies for men 40+ (e.g. posture, shoulder rounding, glute activation)</li>
</ul><br>

<strong>Recommended Nutrition</strong><br>
<ul>
<li><strong>Calorie Plan:</strong> Recommend deficit or maintenance</li>
<li><strong>Macros:</strong> Protein 1.6–2.2 g/kg, moderate carbs, healthy fats</li>
<li><strong>Foods:</strong> Lean meats, greens, legumes, oats, avoid sugar and fried oils</li>
</ul><br>

<strong>Next Steps</strong><br>
<ul>
<li><strong>Strength Training:</strong> 3×/week full-body with compound lifts</li>
<li><strong>Cardio:</strong> 2×/week HIIT or fasted walking</li>
<li><strong>Tracking:</strong> Weekly waist/weight/photos</li>
<li><strong>Support:</strong> Optional whey, creatine, D3</li>
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
