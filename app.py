def analyze_rfq_with_llm(full_text):
    prompt = f"""
You are an expert technical coordinator in maritime navigation and communication equipment supply.
Parse the following commercial RFQ / technical inquiry and extract all operational facts into JSON.

Strict Operational Guidelines:
1. Contextual Distinction: Distinguish between the vessel's identity and makers. If a vessel is named after a brand (e.g. 'HTM Highlander', 'Sperry Spirit'), do NOT list that brand as a required maker unless that equipment on board is genuinely malfunctioning or being serviced.
2. Port & Country: Identify the destination port where attendance is required, and resolve its country (e.g. Tutunciftlik -> Turkey, Piraeus -> Greece).
3. Equipment Maker: Identify ONLY the equipment maker(s) requiring attendance, overhaul, annual survey, or spares.
4. Scope of Attendance: Accurately summarize the required service, overhaul, or defect.

Inquiry:
\"\"\"{full_text}\"\"\"

Return ONLY a raw JSON dictionary without Markdown formatting or fences, using these exact keys:
{{
  "vessel_name": "Name of vessel or 'Not specified'",
  "eta": "Vessel ETA / attendance schedule or 'Not specified'",
  "port": "Port of attendance or 'Not specified'",
  "country": "Country of attendance or 'Not specified'",
  "makers": ["Maker requiring service, e.g. YOKOGAWA, FURUNO"],
  "scope": "Operational summary of the requested job",
  "spares_requested": "Spares mentioned or 'None explicitly requested'",
  "missing_critical_data": ["List of missing essentials among: Schedule/ETA, Port Agent details, Maker/Model, Scope of attendance"]
}}
"""
    models_to_try = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    for model_name in models_to_try:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                elif raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                return json.loads(raw_text.strip())
            except Exception as e:
                time.sleep((attempt + 1) * 2)  # Περιμένει 2, μετά 4 δευτερόλεπτα
    
    st.error("Server is busy. Please wait 10 seconds and click the button again.")
    return {}
