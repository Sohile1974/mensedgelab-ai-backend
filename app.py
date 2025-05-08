from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)

# Set your OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route('/evaluate', methods=['POST'])
def evaluate():
    data = request.json
    image_url = data.get("image_url")
    age = data.get("age")
    height = data.get("height")
    weight = data.get("weight")
    goal = data.get("goal")

    if not image_url:
        return jsonify({"error": "Image URL missing"}), 400

    # Step 1: Image analysis
    step1_prompt = [
        {"role": "system", "content": "You are a fitness assessment expert. Describe the body in the image in neutral, clinical detail (no assumptions)."},
        {"role": "user", "content": f"Describe the body in this image: {image_url}"}
    ]

    step1_response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=step1_prompt
    )
    image_description = step1_response.choices[0].message.content.strip()

    # Step 2: Full evaluation with user inputs
    step2_prompt = [
        {"role": "system", "content": "You are a strict, medically realistic fitness and health coach creating a photo-based evaluation report."},
        {"role": "user", "content": f"""
Image description:
{image_description}

User data:
- Age: {age or 'not provided'}
- Height: {height or 'not provided'}
- Weight: {weight or 'not provided'}
- Goal: {goal or 'not provided'}

Write a personalized body evaluation report based on the image and data. Use bullet points. If the image is unclear or not suitable, return a professional fallback message. If data is missing, use your judgment to give useful advice. The tone should be strict but motivating. Structure it into:
1. Overall Impression
2. Health Risk Analysis
3. Fat vs. Muscle Assessment
4. Customized Goals (generate if user left it blank)
5. Recommended Nutrition
6. Next Steps
"""}]

    step2_response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=step2_prompt
    )
    final_report = step2_response.choices[0].message.content.strip()

    return jsonify({"report": final_report})

if __name__ == '__main__':
    app.run(debug=True)
