step2_prompt = f"""You are generating a personalized HTML fitness report based on a user's image and physical data.

User Profile:
- Age: {user_age or 'Not provided'}
- Height: {user_height or 'Not provided'} cm
- Weight: {user_weight or 'Not provided'} kg
- BMI: {bmi:.1f} {"(calculated)" if bmi else ""}

Image Summary:
"{visual_summary}"

Now write a clear, HTML-formatted fitness evaluation report using the structure below. Use <strong> for titles, <br> for spacing, and <ul>/<li> for bullet points.

<strong>Overall Impression</strong><br>
[Short summary of posture, body shape, and muscle tone.]<br><br>

<strong>Health Risk Analysis</strong><br>
[Evaluate age, weight, BMI risks. Mention visceral fat, lifestyle risks.]<br><br>

<strong>Fat vs. Muscle Assessment</strong><br>
[Compare visible body fat and muscular development. What’s missing?]<br><br>

<strong>Customized Goals</strong><br>
<ul>
<li>Set realistic fitness goals for the user.</li>
<li>Include fat loss %, muscle gain, or mobility targets.</li>
</ul><br>

<strong>Recommended Nutrition</strong><br>
<ul>
<li>Calories range (e.g., 500–700 kcal deficit if needed)</li>
<li>Macronutrient tips (e.g., protein intake, fiber, carbs)</li>
<li>Food types to increase/avoid</li>
</ul><br>

<strong>Next Steps</strong><br>
<ul>
<li>Workout type, frequency, focus</li>
<li>Key metrics to track</li>
<li>Suggested schedule or tools</li>
</ul>

Be strict but motivational. Keep tone serious, direct, and no unnecessary disclaimers.
"""
