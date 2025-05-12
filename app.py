from flask import Flask, request, make_response, send_from_directory, jsonify
import openai
import os
import re
import pdfkit
from datetime import datetime
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "data")
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

PDF_BASE_URL = "https://mensedgelab-ai-backend.onrender.com/files"

@app.route("/files/<filename>", methods=["GET"])
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/evaluate-photo", methods=["POST"])
def evaluate_photo():
    try:
        print("✅ Received POST request to /evaluate-photo")
        data = request.get_json(force=True)
        print("🧹 Received data:", data)

        if not data or "messages" not in data:
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

        step1_prompt_primary = (
            """Describe the person’s physique in this image for a fitness evaluation. This is a professional submission intended for body composition analysis. Focus on posture, muscle tone, and fat distribution. Do not make assumptions about identity or context. Do not refuse unless the image is clearly inappropriate or unviewable."""
        )
        step1_prompt_fallback = (
            "Describe the person in this image, including general body type, stance, posture, and muscle/fat visibility. Keep the tone factual and observational only."
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

        step2_prompt = f"""You are a professional AI fitness coach. Based on the visual summary and user data below, write a customized HTML report using <strong>, <br>, <ul>, <li> (no markdown). Make each section clear, dynamic, and formatted with bullet points. Include specific numbers, suggestions, and practical advice.

<strong>User Profile</strong><br>
Age: {user_age or 'Not provided'}<br>
Height: {user_height or 'Not provided'} cm<br>
Weight: {user_weight or 'Not provided'} kg<br>
BMI: {bmi:.1f} {'(calculated)' if bmi else ''}<br><br>

<strong>Image Summary</strong><br>
<ul>
<li><strong>Muscularity:</strong> Describe visible muscle tone and symmetry.</li>
<li><strong>Fat Distribution:</strong> Focus on fat accumulation zones (abdomen, chest, etc).</li>
<li><strong>Posture & Shape:</strong> Comment on stance, spine alignment, and visual balance.</li>
</ul><br>

<strong>Physique Score (Out of 100)</strong><br>
<ul>
<li>Give a score from 0–100.</li>
<li>Explain what influenced the score (fat %, definition, proportions).</li>
</ul><br>

<strong>Overall Impression</strong><br>
<ul>
<li>Summarize current condition in 1–2 lines.</li>
<li>Mention what is most urgent or promising.</li>
</ul><br>

<strong>Health Risk Analysis</strong><br>
<ul>
<li>Include risks like insulin resistance, lower back strain, or visceral fat.</li>
<li>Comment on BMI category and related concerns.</li>
</ul><br>

<strong>Fat vs. Muscle Assessment</strong><br>
<ul>
<li><strong>Abs:</strong> Describe visibility or fat retention.</li>
<li><strong>Chest:</strong> State current tone or fat deposits.</li>
<li><strong>Back:</strong> Comment on strength, symmetry.</li>
<li><strong>Legs:</strong> Tone, balance, or missing development.</li>
</ul><br>

<strong>Customized Goals</strong><br>
<ul>
<li>Give 3 concrete goals with numbers (e.g. reduce body fat %, waist size).</li>
</ul><br>

<strong>Physique Refinement & Shape Optimization</strong><br>
<ul>
<li>Give 3–4 training tips (e.g. incline dumbbell press, RDLs, lat pulldowns).</li>
<li>Mention how these improve proportions or posture.</li>
</ul><br>

<strong>Recommended Nutrition</strong><br>
<ul>
<li>Suggest daily kcal target (e.g. 2000–2200 kcal).</li>
<li>Macros: 40% protein, 35% carbs, 25% fat.</li>
<li>Example foods: chicken breast, oats, olive oil, sweet potatoes, Greek yogurt.</li>
<li>Avoid: processed snacks, soda, deep fried foods.</li>
</ul><br>

<strong>Next Steps</strong><br>
<ul>
<li>Train 3–4× per week, log progress.</li>
<li>Do 25 min cardio twice per week (HIIT or fasted walk).</li>
<li>Track weekly weight, waist, and progress photo.</li>
<li>Drink 2.5–3 liters water/day and sleep 7+ hours.</li>
<li>Adjust intake if no changes after 3 weeks.</li>
</ul><br>

<strong>Disclaimer</strong><br>
This report is generated for educational purposes only. It does not constitute medical advice or replace consultation with a licensed professional."""

        print("⏳ Calling GPT Step 2...")
        try:
            step2_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [{"type": "text", "text": step2_prompt}]}],
                timeout=15
            )
            final_report = step2_response.choices[0].message.content.strip()
            print("✅ Final Report Generated.")

            filename = f"mensedge_report_{uuid.uuid4().hex[:8]}.pdf"
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdfkit.from_string(final_report, pdf_path, options={"encoding": "UTF-8"})

            public_url = f"{PDF_BASE_URL}/{filename}"
            print("📄 PDF Generated:", public_url)

            return jsonify({"pdf_url": public_url})

        except Exception as e:
            print("🔥 GPT Step 2 failed:", str(e))
            return make_response("⚠️ We encountered an error generating your evaluation. Please try again shortly.", 200)

    except Exception as e:
        print("🔥 Unexpected error:", str(e))
        return make_response(f"⚠️ Step 2 failed: {str(e)}", 200)

@app.route("/", methods=["GET"])
def index():
    return "Men's Edge Lab AI backend is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
