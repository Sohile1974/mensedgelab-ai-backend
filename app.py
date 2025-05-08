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

        user_age = int(re.search(r"user is (\d+)", user_prompt).group(1)) if re.search(r"user is (\d+)", user_prompt) else None
        user_height = int(re.search(r"(\d+)\s*cm", user_prompt).group(1)) if re.search(r"(\d+)\s*cm", user_prompt) else None
        user_weight = int(re.search(r"weighs (\d+)", user_prompt).group(1)) if re.search(r"weighs (\d+)", user_prompt) else None
        bmi = (user_weight / ((user_height / 100) ** 2)) if user_height and user_weight else 0.0

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
                        "image_url": {"url": image_url}
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

        if "i'm sorry" in visual_summary.lower() or "cannot" in visual_summary.lower():
            return make_response("⚠️ The submitted photo could not be evaluated. Please ensure it is well-lit, does not include sensitive content, and clearly shows your physique.", 200)

        step2_prompt = f"""You are an advanced AI fitness expert. Your job is to generate a personalized body evaluation report for a male client based on photo analysis and physical data. Be direct, professional, and goal-focused — like a serious trainer.

<strong>User Profile</strong><br>
Age: {user_age or 'Not provided'}<br>
Height: {user_height or 'Not provided'} cm<br>
Weight: {user_weight or 'Not provided'} kg<br>
BMI: {bmi:.1f} {"(calculated)" if bmi else ""}<br><br>

<strong>Image Summary</strong><br>
{visual_summary}<br><br>

<strong>Overall Impression</strong><br>
Comment on body shape, fat visibility, posture alignment, and general muscle distribution. Mention any noticeable imbalances or symmetry concerns.<br><br>

<strong>Health Risk Analysis</strong><br>
Evaluate BMI and age in relation to potential cardiovascular, metabolic, or mobility-related risks. Clearly state if the user is in an elevated risk zone and what actions should be prioritized.<br><br>

<strong>Visual Risk Markers</strong><br>
List potential physical red flags that may signal hidden risks or performance limitations:
<ul>
<li><strong>Abdominal Protrusion:</strong> Indicates possible visceral fat accumulation, linked to metabolic syndrome.</li>
<li><strong>Shoulder Rounding:</strong> Often reflects weak upper back and tight chest, affecting posture and breathing.</li>
<li><strong>Pelvic Tilt:</strong> May contribute to lower back pain and poor squat mechanics. Suggests mobility work is needed.</li>
</ul><br>

<strong>Fat vs. Muscle Assessment</strong><br>
Break down muscle visibility and fat dominance by region (e.g., chest, arms, abdomen, legs). Highlight weak or overdeveloped areas and note muscle imbalances if seen.<br><br>

<strong>Customized Goals</strong><br>
<ul>
<li><strong>Fat Loss Target:</strong> Aim for ~8–12 kg fat reduction to bring BMI into 23–25 range. Prioritize abdominal fat loss through training and diet.</li>
<li><strong>Muscle Gain Focus:</strong> Increase visible muscle mass in upper chest, shoulders, and arms. Recommend heavy compound movements with progressive overload.</li>
<li><strong>Posture Correction:</strong> Address forward head and shoulder posture with rowing, core, and shoulder stabilizer work.</li>
</ul><br>

<strong>Recommended Nutrition</strong><br>
<ul>
<li>Target a caloric deficit of 500–700 kcal/day based on current weight and goal. Adjust weekly based on results.</li>
<li>Protein: 1.6–2.2g/kg bodyweight daily. Prioritize lean meats, eggs, and whey protein.</li>
<li>Carbs/fats: Choose complex carbs (oats, brown rice), healthy fats (olive oil, avocado), and limit sugars and seed oils.</li>
</ul><br>

<strong>Next Steps</strong><br>
<ul>
<li><strong>Strength Training:</strong> Lift weights 3×/week. Use full-body or push/pull/legs split. Focus on squats, presses, rows, deadlifts.</li>
<li><strong>Cardio:</strong> Do 2 HIIT sessions (20 min) or 30-min fasted walks to enhance fat burning and conditioning.</li>
<li><strong>Progress Tracking:</strong> Track waist circumference, weight, and weekly mirror/photo comparisons. Reassess every 4 weeks.</li>
<li><strong>Supplements:</strong> Consider creatine monohydrate, whey protein, magnesium, and vitamin D based on diet gaps.</li>
</ul><br>

<strong>Estimated Timeline</strong><br>
With consistent effort and adherence:
<ul>
<li><strong>Fat Loss:</strong> Expect 0.5–1 kg/week = ~8–12 weeks for target reduction.</li>
<li><strong>Muscle Definition:</strong> Noticeable strength and shape changes in 6–10 weeks.</li>
<li><strong>Posture Improvements:</strong> Visual posture changes in 4–6 weeks with corrective exercises.</li>
</ul><br>

<strong>Disclaimer</strong><br>
This report is generated by AI for educational purposes only. It does not constitute medical advice or replace consultation with a licensed professional.
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
