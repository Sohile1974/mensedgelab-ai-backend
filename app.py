from flask import Flask, request, make_response, send_from_directory, jsonify
import openai
import os
import re
import pdfkit
from datetime import datetime
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "data")  # dynamic local folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # ensure folder exists

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

        # Step 1 – Image analysis (DO NOT TOUCH)
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

        # Step 2 – Final Report
        step2_prompt = f"""You are a professional AI fitness coach. Based on the visual summary and user data below, write a customized HTML report using <strong>, <br>, <ul>, <li> (no markdown). Structure it strictly with the following sections:

<strong>User Profile</strong><br>
Age: {user_age or 'Not provided'}<br>
Height: {user_height or 'Not provided'} cm<br>
Weight: {user_weight or 'Not provided'} kg<br>
BMI: {bmi:.1f} {'(calculated)' if bmi else ''}<br><br>

<strong>Image Summary</strong><br>
Break it into 3 lines:<br>
1. Muscularity: Describe muscle tone/definition and symmetry.<br>
2. Fat Distribution: Focus on where fat is visible (abdomen, sides, chest, etc).<br>
3. Posture & Shape: Evaluate alignment, stance, proportions.<br><br>

<strong>Physique Score (Out of 100)</strong><br>
Assign a number from 0–100 based on physique quality and BMI. Explain why in 2 sentences.<br><br>

<strong>Overall Impression</strong><br>
1–2 lines summarizing the overall potential and what is most urgent to improve.<br><br>

<strong>Health Risk Analysis</strong><br>
List 2–3 bullet points about how current body composition or posture might pose risks.<br><br>

<strong>Fat vs. Muscle Assessment</strong><br>
Customize observations by zone (abs, chest, back, legs) in 3–4 bullet points.<br><br>

<strong>Customized Goals</strong><br>
Give 3 specific goals based on the user's physique.<br><br>

<strong>Physique Refinement & Shape Optimization</strong><br>
Give 3–4 training recommendations focused on improving shape/symmetry.<br><br>

<strong>Recommended Nutrition</strong><br>
Give actionable guidelines on calorie intake, macros, and foods to avoid.<br><br>

<strong>Next Steps</strong><br>
Give 3–5 checklist-style habits they must follow to improve physique.
<br><br>
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
