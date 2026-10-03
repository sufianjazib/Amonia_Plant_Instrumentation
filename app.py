### File 10: `app.py`
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from plant_model import AmmoniaPlantModel
from instruments import initialize_instruments
from pid_controller import initialize_controllers
from faults import FaultEngine, FAULT_CATALOG
from alarms import AlarmSystem
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_engineer import run_ai_diagnostics, run_ai_chat
from ai_engineer import run_ai_diagnostics, run_ai_chat

# Page Config
st.set_page_config(
    page_title="AI Twin Ammonia Plant",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "plant_model" not in st.session_state:
    st.session_state.plant_model = AmmoniaPlantModel()
    st.session_state.instruments = initialize_instruments()
    st.session_state.controllers = initialize_controllers()
    st.session_state.fault_engine = FaultEngine()
    st.session_state.alarm_system = AlarmSystem()
    st.session_state.history = []
    st.session_state.ai_diagnosis = ""
    st.session_state.chat_messages = []
    st.session_state.last_time = time.time()
    st.session_state.auto_run = True

# Helper simulation tick
def step_simulation():
    pm = st.session_state.plant_model
    insts = st.session_state.instruments
    ctrls = st.session_state.controllers
    fe = st.session_state.fault_engine
    alarms = st.session_state.alarm_system

    # Apply faults
    fe.apply_faults(insts, ctrls, pm.state)

    # Controller updates
    for ctrl in ctrls.values():
        pv_val = insts[ctrl.pv_tag].indicated_value if ctrl.pv_tag in insts else 0.0
        ctrl.update(pv_val)

    # Process physics step
    pm.step(ctrls)
    pm.update_instrument_objects(insts)

    # Alarm evaluation
    alarms.evaluate(insts)

    # Log telemetry history
    timestamp = pd.Timestamp.now()
    record = {"Timestamp": timestamp}
    for tag, inst in insts.items():
        record[tag] = inst.indicated_value
    for tag, ctrl in ctrls.items():
        record[f"{tag}_OUT"] = ctrl.output
    st.session_state.history.append(record)
    if len(st.session_state.history) > 3600:
        st.session_state.history.pop(0)

# Advance simulation on tick
step_simulation()

# Health Calculator
def calculate_health():
    insts = st.session_state.instruments
    ctrls = st.session_state.controllers
    faults = st.session_state.fault_engine.active_faults
    
    inst_health = 100 - (sum(1 for i in insts.values() if i.status != "NORMAL") * 15)
    ctrl_health = 100 - (sum(1 for c in ctrls.values() if c.stuck_valve or c.air_failure) * 25)
    proc_health = 100 - (len(faults) * 20)
    comm_health = 100.0
    return max(0, inst_health), max(0, proc_health), max(0, ctrl_health), comm_health

inst_h, proc_h, ctrl_h, comm_h = calculate_health()

# UI HEADER
st.markdown("""
<style>
.metric-card {
    background-color: #1E293B;
    padding: 12px;
    border-radius: 8px;
    border-left: 4px solid #3B82F6;
}
.status-normal { color: #10B981; font-weight: bold; }
.status-alarm { color: #EF4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🏭 AI Twin Instrumentation Plant — Ammonia Unit")
st.caption("🚨 SIMULATION ONLY — NOT FOR REAL PLANT CONTROL | Digital Twin & AI Diagnostics Engine")

# KPI Top Bar
kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
with kpi1:
    st.metric("NH3 Production", f"{st.session_state.instruments['FT-701'].indicated_value:.1f} t/h")
with kpi2:
    st.metric("Reformer Temp", f"{st.session_state.instruments['TT-201'].indicated_value:.0f} °C")
with kpi3:
    st.metric("Reactor Temp", f"{st.session_state.instruments['TT-601'].indicated_value:.0f} °C")
with kpi4:
    st.metric("SynGas Press", f"{st.session_state.instruments['PT-501'].indicated_value:.0f} bar")
with kpi5:
    n_alarms = len(st.session_state.alarm_system.active_alarms)
    st.metric("Active Alarms", f"{n_alarms}", delta_color="inverse", delta=f"{n_alarms} active" if n_alarms > 0 else "Normal")
with kpi6:
    st.metric("Overall Health", f"{int((inst_h+proc_h+ctrl_h)/3)}%")

# SIDEBAR CONTROLS
st.sidebar.header("🕹️ Plant Control Center")

op_mode = st.sidebar.radio(
    "Operating Mode",
    ["NORMAL OPERATION", "FAULT SIMULATION", "ENGINEERING DIAGNOSTICS", "🤖 AI ENGINEER", "HISTORICAL TRENDS", "ALARM MANAGEMENT"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("🚀 Predefined Fault Scenarios")

if st.sidebar.button("🔥 Scenario 1: TT-601 Temp Bias (+60°C)"):
    st.session_state.fault_engine.clear_all()
    st.session_state.fault_engine.inject_fault("TT-601", "INSTRUMENT_BIAS", 60.0)
    st.sidebar.success("Injected: TT-601 Sensor Bias +60°C")

if st.sidebar.button("💥 Scenario 2: Compressor Trip"):
    st.session_state.fault_engine.clear_all()
    st.session_state.fault_engine.inject_fault("C-501", "COMPRESSOR_TRIP", 1.0, "PROCESS")
    st.sidebar.error("Injected: SynGas Compressor Trip")

if st.sidebar.button("🔒 Scenario 3: Reformer Valve Stuck"):
    st.session_state.fault_engine.clear_all()
    st.session_state.fault_engine.inject_fault("TIC-201", "VALVE_STUCK", 15.0, "VALVE")
    st.sidebar.warning("Injected: Reformer Fuel Valve Stuck at 15%")

if st.sidebar.button("🧊 Scenario 4: PT-501 Frozen Line"):
    st.session_state.fault_engine.clear_all()
    st.session_state.fault_engine.inject_fault("PT-501", "INSTRUMENT_FROZEN", 0.0)
    st.sidebar.warning("Injected: PT-501 Impulse Line Blocked")

if st.sidebar.button("🧹 Clear All Faults"):
    st.session_state.fault_engine.clear_all()
    st.sidebar.info("All plant faults cleared.")

# MAIN CONTENT ROUTING
if op_mode == "NORMAL OPERATION" or op_mode == "FAULT SIMULATION":
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🖼️ Ammonia Unit PFD Digital Twin Screen")
        
        # PFD Visual Component
        fig_pfd = go.Figure()
        
        # Block shapes
        equipment = [
            ("D-101\nDesulfurizer", 1, 3, "#1E293B"),
            ("F-101\nPrimary Ref.", 3, 3, "#1E293B"),
            ("R-201\nSec. Ref.", 5, 3, "#1E293B"),
            ("R-301/302\nShift Conv.", 7, 3, "#1E293B"),
            ("A-401\nCO2 Absorber", 9, 3, "#1E293B"),
            ("R-401\nMethanator", 11, 3, "#1E293B"),
            ("C-501\nCompressor", 13, 3, "#1E293B"),
            ("R-501\nNH3 Converter", 15, 3, "#1E293B"),
            ("V-601\nSeparator", 17, 3, "#1E293B"),
        ]

        for name, x, y, col in equipment:
            fig_pfd.add_trace(go.Scatter(
                x=[x], y=[y],
                mode="markers+text",
                marker=dict(size=55, symbol="square", color=col, line=dict(width=2, color="#3B82F6")),
                text=[name],
                textposition="middle center",
                textfont=dict(color="white", size=9),
                hoverinfo="none"
            ))

        # Connecting process flowlines
        fig_pfd.add_trace(go.Scatter(
            x=[0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19],
            y=[3]*11,
            mode="lines",
            line=dict(color="#10B981", width=3),
            hoverinfo="none"
        ))

        # Live telemetry overlay badges
        tt601_pv = st.session_state.instruments["TT-601"].indicated_value
        pt501_pv = st.session_state.instruments["PT-501"].indicated_value
        ft701_pv = st.session_state.instruments["FT-701"].indicated_value

        fig_pfd.add_annotation(x=15, y=3.8, text=f"TT-601: {tt601_pv:.1f} °C", showarrow=False, bgcolor="#0F172A", bordercolor="#3B82F6", font=dict(color="#F8FAFC"))
        fig_pfd.add_annotation(x=13, y=2.2, text=f"PT-501: {pt501_pv:.1f} bar", showarrow=False, bgcolor="#0F172A", bordercolor="#3B82F6", font=dict(color="#F8FAFC"))
        fig_pfd.add_annotation(x=17, y=2.2, text=f"FT-701: {ft701_pv:.1f} t/h", showarrow=False, bgcolor="#0F172A", bordercolor="#3B82F6", font=dict(color="#F8FAFC"))

        fig_pfd.update_layout(
            xaxis=dict(visible=False, range=[-1, 20]),
            yaxis=dict(visible=False, range=[0, 5]),
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False
        )
        st.plotly_chart(fig_pfd, use_container_width=True)

        # Quick Live Telemetry Grid
        st.subheader("📊 Primary Process Parameters")
        inst_df = pd.DataFrame([
            {
                "Tag": inst.tag,
                "Description": inst.description,
                "Indicated PV": f"{inst.indicated_value:.2f} {inst.unit}",
                "Status": inst.status,
                "Loop": inst.control_loop or "-"
            }
            for inst in st.session_state.instruments.values()
        ])
        st.dataframe(inst_df, use_container_width=True, height=280)

    with col_right:
        st.subheader("⚡ Fault Injector Panel")
        with st.form("fault_form"):
            target_inst = st.selectbox("Select Tag", list(st.session_state.instruments.keys()) + list(st.session_state.controllers.keys()))
            fault_kind = st.selectbox("Select Fault Type", list(FAULT_CATALOG.keys()))
            severity = st.slider("Fault Severity / Value Shift", -100.0, 100.0, 50.0)
            
            if st.form_submit_button("🚨 INJECT FAULT"):
                st.session_state.fault_engine.inject_fault(target_inst, fault_kind, severity)
                st.success(f"Injected {fault_kind} on {target_inst}")

        st.subheader("🔴 Active Faults List")
        active_f = st.session_state.fault_engine.active_faults
        if active_f:
            for fid, f in list(active_f.items()):
                st.error(f"{f.description}")
                if st.button(f"Clear {fid}", key=fid):
                    st.session_state.fault_engine.clear_fault(fid)
                    st.rerun()
        else:
            st.info("No active faults injected. Plant running normally.")

elif op_mode == "ENGINEERING DIAGNOSTICS":
    st.subheader("🛠️ Engineering & Health Diagnostics")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Instrument Health", f"{inst_h}%")
    c2.metric("Process Health", f"{proc_h}%")
    c3.metric("Control Health", f"{ctrl_h}%")
    c4.metric("Communication Health", f"{comm_h}%")

    st.markdown("---")
    st.subheader("🎛️ Control Loop Tuning & Status")
    for tag, ctrl in st.session_state.controllers.items():
        with st.expander(f"Control Loop: {tag} - {ctrl.name} (PV: {st.session_state.instruments[ctrl.pv_tag].indicated_value:.1f})"):
            col_a, col_b, col_c = st.columns(3)
            ctrl.mode = col_a.radio(f"Mode {tag}", ["AUTO", "MANUAL"], index=0 if ctrl.mode == "AUTO" else 1, key=f"m_{tag}")
            ctrl.sp = col_b.number_input(f"Setpoint (SP)", value=float(ctrl.sp), key=f"sp_{tag}")
            ctrl.output = col_c.slider(f"Output %", 0.0, 100.0, float(ctrl.output), key=f"out_{tag}")

elif op_mode == "🤖 AI ENGINEER":
    st.subheader("🤖 AI Instrumentation Engineer Diagnostic Center")
    st.caption("Powered by Groq LLM — Real-time Process Diagnostics & Differential Reasoning")

    col_ai1, col_ai2 = st.columns([2, 1])

    with col_ai1:
        if st.button("🔍 RUN DIAGNOSE PLANT NOW", type="primary"):
            with st.spinner("AI Instrumentation Engineer analyzing plant telemetry and control loops..."):
                st.session_state.ai_diagnosis = run_ai_diagnostics(
                    st.session_state.instruments,
                    st.session_state.controllers,
                    st.session_state.alarm_system.active_alarms,
                    st.session_state.fault_engine.active_faults,
                    st.session_state.plant_model.state
                )

        if st.session_state.ai_diagnosis:
            st.markdown(st.session_state.ai_diagnosis)
        else:
            st.info("Click **RUN DIAGNOSE PLANT NOW** to generate an AI diagnostic report.")

    with col_ai2:
        st.subheader("💬 Ask AI Engineer")
        for msg in st.session_state.chat_messages:
            st.chat_message(msg["role"]).write(msg["content"])

        if user_q := st.chat_input("Ask a question about the plant..."):
            st.session_state.chat_messages.append({"role": "user", "content": user_q})
            st.chat_message("user").write(user_q)

            with st.spinner("Thinking..."):
                reply = run_ai_chat(user_q, st.session_state.chat_messages, st.session_state.instruments, st.session_state.controllers)
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                st.chat_message("assistant").write(reply)

elif op_mode == "HISTORICAL TRENDS":
    st.subheader("📈 Real-Time Multi-Variable Trends")
    if len(st.session_state.history) > 2:
        df_hist = pd.DataFrame(st.session_state.history)
        
        selected_tags = st.multiselect(
            "Select Trend Tags",
            options=[c for c in df_hist.columns if c != "Timestamp"],
            default=["TT-601", "TT-201", "PT-501", "FT-701"]
        )

        if selected_tags:
            fig_trend = go.Figure()
            for tag in selected_tags:
                fig_trend.add_trace(go.Scatter(x=df_hist["Timestamp"], y=df_hist[tag], name=tag, mode="lines"))
            fig_trend.update_layout(height=450, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", template="plotly_dark")
            st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Collecting trend data... Please wait a few seconds.")

elif op_mode == "ALARM MANAGEMENT":
    st.subheader("🚨 Alarm Management Console")
    if st.button("ACKNOWLEDGE ALL ALARMS"):
        st.session_state.alarm_system.acknowledge_all()
        st.success("All active alarms acknowledged.")

    st.subheader("Active Alarms")
    active_a = st.session_state.alarm_system.active_alarms
    if active_a:
        a_df = pd.DataFrame([
            {
                "Time": a.timestamp,
                "Tag": a.tag,
                "Alarm Description": a.description,
                "Priority": a.priority,
                "Indicated PV": f"{a.pv:.2f}",
                "Limit": a.limit,
                "Acknowledged": a.acknowledged
            }
            for a in active_a.values()
        ])
        st.dataframe(a_df, use_container_width=True)
    else:
        st.info("No active alarms.")

# Rerun loop for real-time tick (1 second period)
time.sleep(1.0)
st.rerun()
