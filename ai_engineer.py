import os
from groq import Groq

# Initialize Groq client (uses GROQ_API_KEY from Streamlit secrets or environment variables)
client = Groq(api_key=os.environ.get("GROQ_API_KEY", "your_fallback_api_key_here"))

def run_ai_diagnostics(sensor_data):
    """Generates plant diagnostic reports based on incoming telemetry."""
    prompt = f"""
    You are a Lead Instrumentation & Control Engineer at an Ammonia Plant.
    
    Current Telemetry:
    - Primary Reformer Temperature: {sensor_data.get('temperature')} °C
    - Synthesis Loop Pressure: {sensor_data.get('pressure')} Bar
    - Ammonia Flow Rate: {sensor_data.get('flow_rate')} m³/h
    - Active System Faults: {', '.join(sensor_data.get('active_faults', [])) or 'None'}
    
    Provide a concise operational assessment and action recommendations.
    """
    
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Diagnostic Error: {e}"

def run_ai_chat(user_query, context):
    """Provides interactive assistant support for instrumentation engineers."""
    prompt = f"""
    Context: Plant Temperature={context.get('temperature')}°C, Pressure={context.get('pressure')} Bar.
    User Question: {user_query}
    """
    
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are an expert AI Field Engineer specializing in PLC logic, SCADA, and instrumentation control."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Chat Error: {e}"
