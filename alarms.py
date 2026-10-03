from dataclasses import dataclass
from datetime import datetime
from typing import Literal

PriorityType = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

@dataclass
class Alarm:
    timestamp: str
    tag: str
    description: str
    priority: PriorityType
    pv: float
    limit: float
    condition: str
    acknowledged: bool = False


class AlarmSystem:
    def __init__(self):
        self.active_alarms: dict[str, Alarm] = {}
        self.alarm_history: list[Alarm] = []

    def evaluate(self, instruments: dict):
        now_str = datetime.now().strftime("%H:%M:%S")

        for tag, inst in instruments.items():
            pv = inst.indicated_value
            
            # Check High High / Low Low Criticals
            if inst.alarm_high_high and pv >= inst.alarm_high_high:
                self._raise(now_str, tag, f"HH Alarm - {inst.description}", "CRITICAL", pv, inst.alarm_high_high, "HIGH_HIGH")
            elif inst.alarm_low_low and pv <= inst.alarm_low_low:
                self._raise(now_str, tag, f"LL Alarm - {inst.description}", "CRITICAL", pv, inst.alarm_low_low, "LOW_LOW")
            # Check High / Low Warnings
            elif pv >= inst.alarm_high:
                self._raise(now_str, tag, f"High Alarm - {inst.description}", "HIGH", pv, inst.alarm_high, "HIGH")
            elif pv <= inst.alarm_low:
                self._raise(now_str, tag, f"Low Alarm - {inst.description}", "MEDIUM", pv, inst.alarm_low, "LOW")
            else:
                # Clear active alarm if restored
                if tag in self.active_alarms:
                    del self.active_alarms[tag]

    def _raise(self, time_str: str, tag: str, desc: str, priority: PriorityType, pv: float, limit: float, cond: str):
        if tag not in self.active_alarms or self.active_alarms[tag].condition != cond:
            alarm = Alarm(time_str, tag, desc, priority, pv, limit, cond)
            self.active_alarms[tag] = alarm
            self.alarm_history.insert(0, alarm)
            if len(self.alarm_history) > 100:
                self.alarm_history.pop()

    def acknowledge_all(self):
        for alarm in self.active_alarms.values():
            alarm.acknowledged = True
