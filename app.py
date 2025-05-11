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

        # ✅ Step 2 – Final Report (strict coach + motivational refined)
        step2_prompt = f"""You are a professional AI fitness coach. Write a structured HTML report using only <strong>, <br>, <ul>, <li>. Avoid markdown. Your tone is that of a strict coach who gives honest, motivating feedback. Highlight strengths but give no-nonsense direction for improvement.

<strong>User Profile</strong><br>
Age: {user_age or 'Not provided'}<br>
Height: {user_height or 'Not provided'} cm<br>
Weight: {user_weight or 'Not provided'} kg<br>
BMI: {bmi:.1f} {'(calculated)' if bmi else ''}<br><br>

<strong>Image Summary</strong><br>
{visual_summary}<br><br>

<strong>Overall Impression</strong><br>
There’s clear potential here — posture is reasonably aligned, some muscular tone is visible, and proportions are decent. But don’t settle. To stand out visually and improve long-term health, fat loss around the midsection and upper-body shaping must become top priorities.<br><br>

<strong>Health Risk Analysis</strong><br>
<ul>
<li>BMI of {bmi:.1f} places you in the {'overweight' if bmi >= 25 else 'normal' if bmi >= 18.5 else 'underweight'} category. That’s manageable, but not optimal.</li>
<li>Abdominal fat and posture-related imbalances can raise risks for insulin resistance, lower back strain, and poor metabolic flexibility — especially for age {user_age or '?'}. Act early.</li>
</ul><br>

<strong>Fat vs. Muscle Assessment</strong><br>
<ul>
<li><strong>Abdomen:</strong> Primary fat zone — trimming it will visibly sharpen your frame and reduce health risk.</li>
<li><strong>Chest & Shoulders:</strong> Muscle definition is a good start. Push hypertrophy to create upper-body width.</li>
<li><strong>Back & Legs:</strong> Functional but needs refinement. Focus on posterior chain lifts for better proportion and posture.</li>
</ul><br>

<strong>Customized Goals</strong><br>
<ul>
<li><strong>Fat Loss:</strong> Drop 6–8 kg to bring BMI to 23–24 — this range gives both visual sharpness and metabolic safety.</li>
<li><strong>Muscle Gain:</strong> Prioritize upper chest, shoulders, and lats for a wider, stronger profile.</li>
<li><strong>Posture:</strong> Strengthen glutes and upper back. Mobilize hip flexors and thoracic spine to fix rounding or tilt.</li>
</ul><br>

<strong>Physique Refinement & Shape Optimization</strong><br>
<ul>
<li>Train chest and delts to exaggerate your V-taper and upper-body dominance.</li>
<li>Add Romanian deadlifts, glute bridges, and reverse lunges to strengthen and define lower posterior chain.</li>
<li>Postural strength + visible taper = youthfulness and authority. These are your target visual traits at 40+.</li>
</ul><br>

<strong>Recommended Nutrition</strong><br>
<ul>
<li>Create a ~500 kcal daily deficit. Hold steady for 3–4 weeks before making changes.</li>
<li>Macros: 1.8–2.2 g/kg protein, low GI carbs (quinoa, oats), healthy fats (avocado, nuts, olive oil).</li>
<li>Strictly avoid sugars, oils, fried foods, and excess evening snacking. Discipline wins.</li>
</ul><br>

<strong>Next Steps</strong><br>
<ul>
<li><strong>Training:</strong> 3×/week resistance training — compound lifts only. Log your sets.</li>
<li><strong>Cardio:</strong> 2×/week: 25 min fasted walk or HIIT. Pick one and stay consistent.</li>
<li><strong>Track:</strong> Weekly photos, weight, and waist (cm). Adjust nutrition if no change in 3 weeks.</li>
<li><strong>Expect:</strong> Waist taper and posture gains in 4–5 weeks. Earn it.</li>
<li><strong>Supplements:</strong> Add whey, creatine, or vitamin D3 only if missing from diet.</li>
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
