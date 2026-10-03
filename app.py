import os
import sys
import streamlit as st
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. Dynamic Path Resolution
# Ensures Streamlit Cloud can locate local modules in the same directory.
# -----------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# -----------------------------------------------------------------------------
# 2. Safe Import of AI Engineer Module
# -----------------------------------------------------------------------------
try:
    from ai_engineer import run_ai_diagnostics, run_ai_chat
except Exception as e:
    st.error(f"⚠️ Could not load `ai_engineer.py`: {e}")
    st.info("Check Streamlit Cloud 'Manage app > Logs' to fix syntax errors inside ai_engineer.py.")
    
    # Fallback dummy functions so the UI still renders safely
    def run_ai_diagnostics(sensor_data):
        return f"AI Module Offline. Error details: {e}"
    
    def run_ai_chat(prompt, context):
        return f"AI Assistant Unavailable: {e}"

# -----------------------------------------------------------------------------
# 3. Streamlit Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Ammonia Plant Instrumentation & AI Engineer",
    page_icon="🏭",
    layout="wide",
)

st.title("🏭 Ammonia Plant Instrumentation Digital Twin")
st.markdown("Real-time telemetry monitoring, PLC fault injection, and AI engineering diagnostics.")

# -----------------------------------------------------------------------------
# 4. Sidebar - Control Panel & Plant Parameters
# -----------------------------------------------------------------------------
st.sidebar.header("Control Panel & Parameters")

reactor_temp = st.sidebar.slider("Reformer Temperature (°C)", min_value=300, max_value=800, value=520, step=5)
system_pressure = st.sidebar.slider("Synthesis Pressure (Bar)", min_value=50, max_value=250, value=150, step=5)
ammonia_flow = st.sidebar.slider("Ammonia Output Flow (m³/h)", min_value=0, max_value=120, value=85, step=1)

fault_injection = st.sidebar.multiselect(
    "Inject System Faults",
    ["High Pressure Trip", "Temperature Sensor Drift", "Valve Actuator Lockup"],
    default=[]
)
# 1. Read values from sidebar
reactor_temp = st.sidebar.slider("Reformer Temperature (°C)", min_value=300, max_value=800, value=640, step=5)
system_pressure = st.sidebar.slider("Synthesis Pressure (Bar)", min_value=50, max_value=250, value=180, step=5)
ammonia_flow_input = st.sidebar.slider("Ammonia Output Flow (m³/h)", min_value=0, max_value=120, value=83, step=1)

fault_injection = st.sidebar.multiselect(
    "Inject System Faults",
    ["High Pressure Trip", "Temperature Sensor Drift", "Valve Actuator Lockup"],
    default=["High Pressure Trip"]
)

# 2. PLC Emergency Shutdown (ESD) Interlock Logic
esd_tripped = False
trip_reasons = []

# Trip logic on high pressure threshold (>170 Bar) or manual fault injection
if system_pressure > 170 or "High Pressure Trip" in fault_injection:
    esd_tripped = True
    trip_reasons.append("HIGH SYNTHESIS PRESSURE TRIP (ESD-101)")

# Apply safety shutdown
if esd_tripped:
    ammonia_flow = 0  # Isolation valve XV-101 closes automatically on trip
    st.error(f"🚨 **PLANT TRIP CONDITION ACTIVE**: {', '.join(trip_reasons)}. Emergency isolation valves closed. Flow forced to 0 m³/h.")
else:
    ammonia_flow = ammonia_flow_input

# -----------------------------------------------------------------------------
# 5. Dashboard Telemetry & Visualizations
# -----------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Reformer Temp", value=f"{reactor_temp} °C", delta=f"{reactor_temp - 500} °C")
with col2:
    st.metric(label="Synthesis Pressure", value=f"{system_pressure} Bar", delta=f"{system_pressure - 140} Bar")
with col3:
    st.metric(label="Ammonia Flow Rate", value=f"{ammonia_flow} m³/h", delta=f"{ammonia_flow - 80} m³/h")

st.divider()

# Plotly Gauge Chart
fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=reactor_temp,
    domain={'x': [0, 1], 'y': [0, 1]},
    title={'text': "Primary Reformer Temperature (°C)"},
    gauge={
        'axis': {'range': [None, 900]},
        'steps': [
            {'range': [0, 450], 'color': "lightgray"},
            {'range': [450, 650], 'color': "gray"},
        ],
        'threshold': {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': 750
        }
    }
))
st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. AI Engineer Diagnostics Section
# -----------------------------------------------------------------------------
st.header("🤖 AI Field Engineer Diagnostics")

sensor_data = {
    "temperature": reactor_temp,
    "pressure": system_pressure,
    "flow_rate": ammonia_flow,
    "active_faults": fault_injection
}

if st.button("Run AI Plant Analysis"):
    with st.spinner("Analyzing plant parameters with Groq/LLM engine..."):
        diagnostic_report = run_ai_diagnostics(sensor_data)
        st.success("Analysis Complete")
        st.text_area("Diagnostic Summary", value=diagnostic_report, height=200)

# Interactive Assistant Chat
st.subheader("💬 Ask AI Instrumentation Engineer")
user_query = st.text_input("Ask about alarms, calibration, or trip limits:")
if user_query:
    response = run_ai_chat(user_query, sensor_data)
    st.write(f"**AI Response:** {response}")
