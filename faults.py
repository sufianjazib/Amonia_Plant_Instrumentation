from dataclasses import dataclass
from typing import Optional

@dataclass
class ActiveFault:
    fault_id: str
    target_type: str  # "INSTRUMENT", "VALVE", "PROCESS"
    target_tag: str
    fault_type: str
    severity: float  # 0.0 to 1.0 or quantitative scalar
    description: str


FAULT_CATALOG = {
    "INSTRUMENT_BIAS": "Transmitter Calibration Bias / Offset",
    "INSTRUMENT_FROZEN": "Signal Frozen / Impulse Line Blockage",
    "OPEN_CIRCUIT": "4-20mA Loop Open Circuit / Sensor Failure",
    "VALVE_STUCK": "Control Valve Mechanical Jam",
    "VALVE_AIR_FAIL": "Control Valve Loss of Instrument Air",
    "FURNACE_TRIP": "Reformer Furnace Burner Flameout",
    "COMPRESSOR_TRIP": "SynGas Compressor Mechanical Trip",
    "COOLING_FAILURE": "Reactor Condenser Cooling Water Failure"
}


class FaultEngine:
    def __init__(self):
        self.active_faults: dict[str, ActiveFault] = {}

    def inject_fault(self, target_tag: str, fault_type: str, severity: float, target_type: str = "INSTRUMENT"):
        fault_id = f"{target_tag}_{fault_type}"
        desc = f"{FAULT_CATALOG.get(fault_type, fault_type)} on {target_tag} (Sev: {severity})"
        fault = ActiveFault(fault_id, target_type, target_tag, fault_type, severity, desc)
        self.active_faults[fault_id] = fault

    def clear_fault(self, fault_id: str):
        if fault_id in self.active_faults:
            del self.active_faults[fault_id]

    def clear_all(self):
        self.active_faults.clear()

    def apply_faults(self, instruments: dict, controllers: dict, process_state: dict):
        # Reset fault overrides first
        for inst in instruments.values():
            inst.bias = 0.0
            inst.is_frozen = False
            inst.is_open_circuit = False
            inst.lag_factor = 0.0

        for ctrl in controllers.values():
            ctrl.stuck_valve = False
            ctrl.air_failure = False

        process_state["furnace_trip"] = False
        process_state["compressor_trip"] = False
        process_state["cooling_failure"] = False

        # Apply each active fault
        for fault in self.active_faults.values():
            tag = fault.target_tag
            ftype = fault.fault_type
            sev = fault.severity

            if tag in instruments:
                inst = instruments[tag]
                if ftype == "INSTRUMENT_BIAS":
                    inst.bias = sev  # e.g., +60.0 °C
                elif ftype == "INSTRUMENT_FROZEN":
                    inst.is_frozen = True
                    inst.lag_factor = 0.95
                elif ftype == "OPEN_CIRCUIT":
                    inst.is_open_circuit = True

            if tag in controllers:
                ctrl = controllers[tag]
                if ftype == "VALVE_STUCK":
                    ctrl.stuck_valve = True
                    ctrl.stuck_position = sev  # e.g., 20% position
                elif ftype == "VALVE_AIR_FAIL":
                    ctrl.air_failure = True

            if ftype == "FURNACE_TRIP":
                process_state["furnace_trip"] = True
            elif ftype == "COMPRESSOR_TRIP":
                process_state["compressor_trip"] = True
            elif ftype == "COOLING_FAILURE":
                process_state["cooling_failure"] = True
