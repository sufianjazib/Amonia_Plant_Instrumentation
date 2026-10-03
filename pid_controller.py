from dataclasses import dataclass
from typing import Literal

ControllerMode = Literal["AUTO", "MANUAL"]

@dataclass
class PIDController:
    tag: str
    name: str
    pv_tag: str
    sp: float
    kp: float
    ki: float
    kd: float
    output_min: float = 0.0
    output_max: float = 100.0
    mode: ControllerMode = "AUTO"
    manual_output: float = 50.0
    integral: float = 0.0
    last_error: float = 0.0
    output: float = 50.0
    
    # Valve/Actuator Fault overrides
    stuck_valve: bool = False
    stuck_position: float = 50.0
    air_failure: bool = False

    def update(self, pv: float, dt: float = 1.0) -> float:
        if self.air_failure:
            self.output = 0.0  # Fail Closed valve assumption
            return self.output

        if self.stuck_valve:
            self.output = self.stuck_position
            return self.output

        if self.mode == "MANUAL":
            self.output = max(self.output_min, min(self.output_max, self.manual_output))
            return self.output

        error = self.sp - pv
        self.integral += error * dt
        
        # Anti-windup clamping
        max_integral = 100.0 / max(0.001, self.ki)
        self.integral = max(-max_integral, min(max_integral, self.integral))

        derivative = (error - self.last_error) / dt if dt > 0 else 0.0
        
        raw_output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        self.output = max(self.output_min, min(self.output_max, raw_output))
        
        self.last_error = error
        return round(self.output, 2)


def initialize_controllers() -> dict[str, PIDController]:
    return {
        "FIC-101": PIDController("FIC-101", "Feed Flow Control", "FT-101", sp=100.0, kp=0.8, ki=0.2, kd=0.05),
        "TIC-201": PIDController("TIC-201", "Reformer Temp Control", "TT-201", sp=850.0, kp=1.2, ki=0.1, kd=0.2),
        "PIC-301": PIDController("PIC-301", "Secondary Reformer Press", "PT-301", sp=27.5, kp=1.5, ki=0.25, kd=0.1),
        "TIC-601": PIDController("TIC-601", "Reactor Temp Control", "TT-601", sp=480.0, kp=1.0, ki=0.15, kd=0.1),
        "PIC-601": PIDController("PIC-601", "Reactor Press Control", "PT-601", sp=175.0, kp=1.1, ki=0.2, kd=0.05),
        "LIC-601": PIDController("LIC-601", "Separator Level Control", "LT-601", sp=50.0, kp=2.0, ki=0.3, kd=0.0),
        "FIC-701": PIDController("FIC-701", "Product Flow Control", "FT-701", sp=45.0, kp=0.9, ki=0.1, kd=0.02),
    }
