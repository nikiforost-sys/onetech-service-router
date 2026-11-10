def analyze_rfq_with_llm(full_text):
    prompt = f"""
You are a senior maritime technical operations coordinator. Extract key operational details from the RFQ inquiry below.
Carefully analyze semantic context:
- Do NOT confuse vessel names with equipment makers (e.g. 'HTM Highlander' is a vessel, not the maker Highlander).
- Do NOT confuse sender/receiver company locations with the actual vessel port of call.
- Extract the exact maker requiring service (e.g., YOKOGAWA, SPERRY, JRC, etc.).

Inquiry Text:
\"\"\"{full_text}\"\"\"

Return ONLY a valid JSON object without markdown formatting or code fences, with these exact keys:
{{
  "vessel_name": "String or 'Not specified'",
  "eta": "String or 'Not specified'",
  "port": "String or 'Not specified'",
  "country": "String or 'Not specified' (Target country where attendance is required)",
  "makers": ["List of makers needing service/overhaul/survey, e.g. 'YOKOGAWA', 'SPERRY MARINE'"],
  "scope": "Clear summary of defect, survey, overhaul, or requested scope of work",
  "spares_requested": "Summary of spares requested or 'None explicitly requested'",
  "missing_critical_data": ["List of missing essentials among: Vessel Schedule, Port Agent, Equipment Maker/Model, Clear Scope"]
}}
"""
    model_names = [
        "models/gemini-3.8-flash",
        "gemini-3.8-flash",
        "models/gemini-2.0-flash",
        "gemini-2.0-flash"
    ]
    
    last_error = None
    for name in model_names:
        try:
            active_model = genai.GenerativeModel(name)
            response = active_model.generate_content(prompt)
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            return json.loads(raw_text.strip())
        except Exception as e:
            last_error = e
            continue
            
    st.error(f"Semantic parsing error: {last_error}")
    return None
