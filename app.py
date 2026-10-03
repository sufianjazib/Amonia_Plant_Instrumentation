import streamlit as st

st.set_page_config(page_title="Ammonia Plant Digital Twin", layout="wide")

# ==========================================
# 1. SIDEBAR CONTROLS (ONLY DEFINE ONCE!)
# ==========================================
st.sidebar.title("Control Panel & Parameters")

reformer_temp_input = st.sidebar.slider("Reformer Temperature (°C)", min_value=300, max_value=800, value=535, step=5)
synthesis_press_input = st.sidebar.slider("Synthesis Pressure (Bar)", min_value=0, max_value=250, value=65, step=5)
ammonia_flow_input = st.sidebar.slider("Ammonia Output Flow (m³/h)", min_value=0, max_value=120, value=83, step=1)

fault_injection = st.sidebar.multiselect(
    "Inject System Faults",
    ["High Pressure Trip", "Temperature Sensor Drift", "Valve Actuator Lockup"],
    default=[]
)

# ==========================================
# 2. FAULT PROCESSING & PROCESS LOGIC
# ==========================================
reformer_temp = reformer_temp_input
synthesis_press = synthesis_press_input
ammonia_flow = ammonia_flow_input

active_alarms = []

# Fault 1: High Pressure Trip
if "High Pressure Trip" in fault_injection or synthesis_press > 170:
    ammonia_flow = 0  # ESD trips flow to zero
    active_alarms.append("HIGH SYNTHESIS PRESSURE TRIP (ESD-101): Emergency isolation valves closed. Flow forced to 0 m³/h.")

# Fault 2: Temperature Sensor Drift (+50°C offset calibration error)
if "Temperature Sensor Drift" in fault_injection:
    reformer_temp += 50
    active_alarms.append("TEMPERATURE SENSOR DRIFT (TE-204): Instrument output biased by +50°C.")

# Fault 3: Valve Actuator Lockup
if "Valve Actuator Lockup" in fault_injection:
    active_alarms.append("VALVE ACTUATOR LOCKUP (XV-101): Control valve fail-safe lock activated.")

# ==========================================
# 3. MAIN DASHBOARD UI
# ==========================================
st.title("🏭 Ammonia Plant Instrumentation Digital Twin")
st.caption("Real-time telemetry monitoring, PLC fault injection, and AI engineering diagnostics.")

# Display Alarm Banner if any fault/trip exists
if active_alarms:
    for alarm in active_alarms:
        st.error(f"🚨 **PLANT FAULT ACTIVE**: {alarm}")

# Metric Cards
col1, col2, col3 = st.columns(3)

delta_temp = reformer_temp - 500
delta_press = synthesis_press - 140
delta_flow = ammonia_flow - 80

col1.metric("Reformer Temp", f"{reformer_temp} °C", f"{delta_temp:+d} °C")
col2.metric("Synthesis Pressure", f"{synthesis_press} Bar", f"{delta_press:+d} Bar")
col3.metric("Ammonia Flow Rate", f"{ammonia_flow} m³/h", f"{delta_flow:+d} m³/h")
