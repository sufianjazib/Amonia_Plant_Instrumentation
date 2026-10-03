import os
import sys
import streamlit as st
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. Dynamic Path Resolution & Safe AI Import
# -----------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from ai_engineer import run_ai_diagnostics, run_ai_chat
except Exception as e:
    def run_ai_diagnostics(sensor_data):
        return f"AI Module Offline/Error: {e}"
    def run_ai_chat(query, context):
        return f"AI Module Offline/Error: {e}"

# -----------------------------------------------------------------------------
# 2. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Ammonia Plant Digital Twin & SCADA",
    page_icon="🏭",
    layout="wide",
)

# -----------------------------------------------------------------------------
# 3. Sidebar Controls (Single Clean Definition)
# -----------------------------------------------------------------------------
st.sidebar.title("🎛️ SCADA Control Panel")

reformer_temp_input = st.sidebar.slider("Reformer Temperature (°C)", min_value=300, max_value=800, value=535, step=5)
synthesis_press_input = st.sidebar.slider("Synthesis Pressure (Bar)", min_value=0, max_value=250, value=140, step=5)
ammonia_flow_input = st.sidebar.slider("Ammonia Output Flow (m³/h)", min_value=0, max_value=120, value=83, step=1)
tank_level_input = st.sidebar.slider("Ammonia Storage Tank Level (%)", min_value=0, max_value=100, value=65, step=1)

fault_injection = st.sidebar.multiselect(
    "Inject System Faults",
    ["High Pressure Trip", "Temperature Sensor Drift", "Valve Actuator Lockup"],
    default=[]
)

# -----------------------------------------------------------------------------
# 4. Process Safety & ESD Interlock Logic
# -----------------------------------------------------------------------------
reformer_temp = reformer_temp_input
synthesis_press = synthesis_press_input
ammonia_flow = ammonia_flow_input
tank_level = tank_level_input

active_alarms = []

# ESD Trip on High Pressure
if "High Pressure Trip" in fault_injection or synthesis_press > 170:
    ammonia_flow = 0  # Emergency isolation valve XV-101 trips closed
    active_alarms.append("HIGH SYNTHESIS PRESSURE TRIP (ESD-101): XV-101 isolation valve closed. Ammonia flow forced to 0 m³/h.")

# Sensor Drift Bias
if "Temperature Sensor Drift" in fault_injection:
    reformer_temp += 50
    active_alarms.append("TEMPERATURE SENSOR DRIFT (TE-204): Calibration error active (+50°C bias applied).")

# Valve Lockup
if "Valve Actuator Lockup" in fault_injection:
    active_alarms.append("VALVE ACTUATOR LOCKUP (XV-101): Fail-safe valve lock engaged.")

# Tank Level Alarms
if tank_level > 85:
    active_alarms.append("HIGH STORAGE TANK LEVEL (LAH-301): Ammonia storage tank capacity > 85%. Overfill risk.")
elif tank_level < 15:
    active_alarms.append("LOW STORAGE TANK LEVEL (LAL-301): Storage level critical < 15%. Transfer pump cavitating.")

# -----------------------------------------------------------------------------
# 5. Header & Active Alarm Banners
# -----------------------------------------------------------------------------
st.title("🏭 Ammonia Plant Instrumentation Digital Twin")
st.caption("Real-time telemetry, SCADA telemetry gauges, storage tank monitoring, and AI field diagnostics.")

if active_alarms:
    for alarm in active_alarms:
        st.error(f"🚨 **PLANT ALARM/TRIP ACTIVE**: {alarm}")

# Top Metric Summary Cards
col1, col2, col3, col4 = st.columns(4)
col1.metric("Reformer Temp", f"{reformer_temp} °C", f"{reformer_temp - 500:+d} °C")
col2.metric("Synthesis Pressure", f"{synthesis_press} Bar", f"{synthesis_press - 140:+d} Bar")
col3.metric("Ammonia Flow Rate", f"{ammonia_flow} m³/h", f"{ammonia_flow - 80:+d} m³/h")
col4.metric("Storage Tank Inventory", f"{tank_level} %", f"{int(tank_level * 100)} MT")

st.divider()

# -----------------------------------------------------------------------------
# 6. SCADA Telemetry Gauges (Reformer, Pressure, Flow)
# -----------------------------------------------------------------------------
st.subheader("📊 Telemetry Instruments & Gauges")

gauge_col1, gauge_col2, gauge_col3 = st.columns(3)

# Gauge 1: Primary Reformer Temperature
with gauge_col1:
    fig_temp = go.Figure(go.Indicator(
        mode="gauge+number",
        value=reformer_temp,
        number={'suffix': " °C"},
        title={'text': "Primary Reformer Temp (°C)"},
        gauge={
            'axis': {'range': [0, 900]},
            'bar': {'color': "firebrick"},
            'steps': [
                {'range': [0, 450], 'color': "lightgray"},
                {'range': [450, 650], 'color': "limegreen"},
                {'range': [650, 750], 'color': "orange"},
                {'range': [750, 900], 'color': "red"},
            ],
            'threshold': {'line': {'color': "black", 'width': 3}, 'thickness': 0.75, 'value': 750}
        }
    ))
    fig_temp.update_layout(height=280, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_temp, use_container_width=True)

# Gauge 2: Synthesis Pressure
with gauge_col2:
    fig_press = go.Figure(go.Indicator(
        mode="gauge+number",
        value=synthesis_press,
        number={'suffix': " Bar"},
        title={'text': "Synthesis Pressure (Bar)"},
        gauge={
            'axis': {'range': [0, 250]},
            'bar': {'color': "royalblue"},
            'steps': [
                {'range': [0, 100], 'color': "lightgray"},
                {'range': [100, 170], 'color': "limegreen"},
                {'range': [170, 250], 'color': "red"},
            ],
            'threshold': {'line': {'color': "black", 'width': 3}, 'thickness': 0.75, 'value': 170}
        }
    ))
    fig_press.update_layout(height=280, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_press, use_container_width=True)

# Gauge 3: Ammonia Output Flow Rate (Shows exact values)
with gauge_col3:
    fig_flow = go.Figure(go.Indicator(
        mode="gauge+number",
        value=ammonia_flow,
        number={'suffix': " m³/h"},
        title={'text': "Ammonia Output Flow (m³/h)"},
        gauge={
            'axis': {'range': [0, 120]},
            'bar': {'color': "teal" if ammonia_flow > 0 else "darkred"},
            'steps': [
                {'range': [0, 20], 'color': "orange"},
                {'range': [20, 100], 'color': "limegreen"},
                {'range': [100, 120], 'color': "red"},
            ],
            'threshold': {'line': {'color': "black", 'width': 3}, 'thickness': 0.75, 'value': 100}
        }
    ))
    fig_flow.update_layout(height=280, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_flow, use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 7. Ammonia Storage Tank System Visualizer
# -----------------------------------------------------------------------------
st.subheader("🛢️ Refrigerated Liquid Ammonia Storage Tank (TK-301)")

tank_col1, tank_col2 = st.columns([1, 2])

with tank_col1:
    st.markdown(f"""
    **Tank Specifications & Live Level:**
    * **Tank ID:** TK-301 (Atmospheric Liquid Storage)
    * **Operating Temp:** -33 °C
    * **Total Capacity:** 10,000 Metric Tons (MT)
    * **Current Level:** **`{tank_level}%`**
    * **Current Inventory:** **`{int(tank_level * 100)} MT`**
    * **Active Flow:** **`{ammonia_flow} m³/h`**
    """)

with tank_col2:
    # Bullet/Tank Level Visualization Chart
    fig_tank = go.Figure(go.Indicator(
        mode="number+gauge",
        value=tank_level,
        number={'suffix': "% Level"},
        title={'text': "Liquid Level Gauge (LT-301)"},
        gauge={
            'shape': "bullet",
            'axis': {'range': [0, 100]},
            'bar': {'color': "crimson" if tank_level > 85 or tank_level < 15 else "dodgerblue"},
            'steps': [
                {'range': [0, 15], 'color': "coral"},
                {'range': [15, 85], 'color': "lightcyan"},
                {'range': [85, 100], 'color': "coral"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 85
            }
        }
    ))
    fig_tank.update_layout(height=180, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_tank, use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 8. AI Field Engineer Diagnostics
# -----------------------------------------------------------------------------
st.header("🤖 AI Field Engineer Diagnostics")

sensor_data = {
    "temperature": reformer_temp,
    "pressure": synthesis_press,
    "flow_rate": ammonia_flow,
    "tank_level_pct": tank_level,
    "active_faults": fault_injection
}

if st.button("Run AI Plant Analysis"):
    with st.spinner("Analyzing telemetry with Groq LLM..."):
        report = run_ai_diagnostics(sensor_data)
        st.success("Analysis Complete")
        st.text_area("Diagnostic Summary", value=report, height=220)

st.subheader("💬 Ask AI Instrumentation Engineer")
user_query = st.text_input("Ask about alarms, calibration, tank safety, or trip limits:")
if user_query:
    response = run_ai_chat(user_query, sensor_data)
    st.write(f"**AI Response:** {response}")
