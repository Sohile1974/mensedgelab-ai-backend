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

        # ✅ Step 2 – Final Report (strict coach + motivational)
        step2_prompt = f"""You are a professional AI fitness coach. Write a structured HTML report using only <strong>, <br>, <ul>, <li>. Avoid markdown. Speak like a strict but motivating coach. Acknowledge the user’s strengths clearly while giving no-nonsense advice.

<strong>User Profile</strong><br>
Age: {user_age or 'Not provided'}<br>
Height: {user_height or 'Not provided'} cm<br>
Weight: {user_weight or 'Not provided'} kg<br>
BMI: {bmi:.1f} {'(calculated)' if bmi else ''}<br><br>

<strong>Image Summary</strong><br>
{visual_summary}<br><br>

<strong>Overall Impression</strong><br>
You’ve already built a solid foundation. The posture is mostly aligned, and there’s visible tone in key areas. Still, refinement is required. You must bring sharper definition to the midsection and upgrade upper-body balance to unlock full aesthetic potential.<br><br>

<strong>Health Risk Analysis</strong><br>
<ul>
<li>BMI of {bmi:.1f} puts you in the {'overweight' if bmi >= 25 else 'normal' if bmi >= 18.5 else 'underweight'} category — not a red flag yet, but a warning.</li>
<li>Excess fat in the abdomen combined with relaxed posture increases long-term risk of insulin resistance, back strain, and poor metabolic flexibility.</li>
</ul><br>

<strong>Fat vs. Muscle Assessment</strong><br>
<ul>
<li><strong>Abdomen:</strong> Clearly the main storage site for fat. You need to cut here first to improve health and visuals.</li>
<li><strong>Chest & Shoulders:</strong> Muscle tone is present. Push hypertrophy on the upper chest to build width.</li>
<li><strong>Legs/Back:</strong> Proportions are decent. Add hamstring and upper back volume to improve silhouette from the side.</li>
</ul><br>

<strong>Customized Goals</strong><br>
<ul>
<li><strong>Fat Loss:</strong> Drop 6–8 kg to bring your BMI to a leaner 23–24 range.</li>
<li><strong>Muscle Gain:</strong> Upper torso (shoulders/chest/back) needs mass. Focus on symmetry and taper.</li>
<li><strong>Posture:</strong> Use posterior chain strength, core control, and mobility drills to fix any forward rounding or pelvic tilt.</li>
</ul><br>

<strong>Physique Refinement & Shape Optimization</strong><br>
<ul>
<li>To widen your V-taper, train upper chest and shoulders with intensity and precision.</li>
<li>Incorporate glute bridges, Romanian deadlifts, and hamstring curls weekly for posterior balance.</li>
<li>Men over 40 gain visual power from upright, open posture and narrow waists — make these non-negotiable priorities.</li>
</ul><br>

<strong>Recommended Nutrition</strong><br>
<ul>
<li>Start with a 500 kcal/day deficit and hold steady for at least 3 weeks before adjusting.</li>
<li>Macros: 1.8–2.2 g/kg protein, slow carbs (quinoa, oats), and fats from avocado, seeds, or olive oil.</li>
<li>Cut all added sugar, processed snacks, and unnecessary evening calories. No excuses.</li>
</ul><br>

<strong>Next Steps</strong><br>
<ul>
<li><strong>Strength Training:</strong> 3×/week full-body lifts. Prioritize compound moves and progressive overload.</li>
<li><strong>Cardio:</strong> Fasted morning walks or HIIT twice per week. No compromises.</li>
<li><strong>Tracking:</strong> Log weight, waist (cm), and take weekly photos. Progress must be visible or the plan adjusts.</li>
<li><strong>Results:</strong> Expect posture and shape changes in 3–5 weeks — if you follow the plan with discipline.</li>
<li><strong>Supplements:</strong> Use whey, creatine, and D3 only if your diet lacks quality sources.</li>
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
