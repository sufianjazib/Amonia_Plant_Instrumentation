from dataclasses import dataclass, field
from typing import Optional, Literal

StatusType = Literal["NORMAL", "WARNING", "CRITICAL", "FAULT", "UNAVAILABLE"]

@dataclass
class Instrument:
    tag: str
    description: str
    equipment: str
    measurement: str
    unit: str
    range_min: float
    range_max: float
    current_value: float
    alarm_low: float
    alarm_high: float
    alarm_low_low: Optional[float] = None
    alarm_high_high: Optional[float] = None
    status: StatusType = "NORMAL"
    sensor_type: str = "4-20mA Transmitter"
    signal_type: str = "4-20mA"
    control_loop: Optional[str] = None
    failure_mode: str = "NONE"
    
    # Internal fault parameters
    bias: float = 0.0
    frozen_value: Optional[float] = None
    is_frozen: bool = False
    is_open_circuit: bool = False
    noise_level: float = 0.0
    lag_factor: float = 0.0  # For impulse line block
    
    # Indicated output after fault application
    indicated_value: float = field(init=False)

    def __post_init__(self):
        self.indicated_value = self.current_value

    def update_indicated_value(self, real_value: float, process_noise: float = 0.0) -> float:
        self.current_value = real_value
        
        if self.is_open_circuit:
            self.indicated_value = 0.0  # Burnout/0mA
            self.status = "FAULT"
            return self.indicated_value
            
        if self.is_frozen:
            if self.frozen_value is None:
                self.frozen_value = self.indicated_value
            self.indicated_value = self.frozen_value
            self.status = "FAULT"
            return self.indicated_value

        # Apply impulse line blockage lag
        if self.lag_factor > 0:
            alpha = max(0.01, 1.0 - self.lag_factor)
            raw = (alpha * self.current_value) + ((1.0 - alpha) * self.indicated_value)
        else:
            raw = self.current_value

        # Apply bias and extra noise
        val = raw + self.bias + process_noise
        
        # Clamp to transmitter physical limits (-5% to 105% range)
        span = self.range_max - self.range_min
        min_limit = self.range_min - (0.05 * span)
        max_limit = self.range_max + (0.05 * span)
        self.indicated_value = round(max(min_limit, min(max_limit, val)), 2)

        # Update status based on alarms
        if self.alarm_high_high and self.indicated_value >= self.alarm_high_high:
            self.status = "CRITICAL"
        elif self.alarm_low_low and self.indicated_value <= self.alarm_low_low:
            self.status = "CRITICAL"
        elif self.indicated_value >= self.alarm_high or self.indicated_value <= self.alarm_low:
            self.status = "WARNING"
        else:
            self.status = "NORMAL"

        return self.indicated_value


def initialize_instruments() -> dict[str, Instrument]:
    return {
        "FT-101": Instrument("FT-101", "Feed Gas Flow", "D-101 Feed Gas", "Flow", "t/h", 0, 150, 100.0, 70.0, 130.0, 50.0, 140.0, control_loop="FIC-101"),
        "PT-101": Instrument("PT-101", "Feed Gas Pressure", "D-101 Feed Gas", "Pressure", "bar", 0, 50, 30.0, 20.0, 40.0, 15.0, 45.0, control_loop="PIC-101"),
        "TT-101": Instrument("TT-101", "Feed Gas Temperature", "D-101 Feed Gas", "Temperature", "°C", 0, 100, 25.0, 10.0, 50.0, 5.0, 60.0),
        
        "FT-201": Instrument("FT-201", "Reformer Steam Flow", "F-101 Primary Reformer", "Flow", "t/h", 0, 300, 220.0, 150.0, 280.0, 120.0, 290.0),
        "TT-201": Instrument("TT-201", "Furnace Temperature", "F-101 Primary Reformer", "Temperature", "°C", 0, 1200, 850.0, 750.0, 950.0, 700.0, 1000.0, control_loop="TIC-201"),
        "TT-202": Instrument("TT-202", "Reformer Outlet Temp", "F-101 Primary Reformer", "Temperature", "°C", 0, 1000, 800.0, 700.0, 900.0, 650.0, 950.0),
        "PT-201": Instrument("PT-201", "Reformer Pressure", "F-101 Primary Reformer", "Pressure", "bar", 0, 50, 28.0, 20.0, 35.0, 15.0, 40.0),

        "FT-301": Instrument("FT-301", "Process Air Flow", "R-201 Secondary Reformer", "Flow", "t/h", 0, 200, 110.0, 80.0, 150.0, 60.0, 160.0),
        "TT-301": Instrument("TT-301", "Secondary Reformer Temp", "R-201 Secondary Reformer", "Temperature", "°C", 0, 1200, 980.0, 880.0, 1080.0, 800.0, 1150.0),
        "PT-301": Instrument("PT-301", "Secondary Reformer Press", "R-201 Secondary Reformer", "Pressure", "bar", 0, 50, 27.5, 20.0, 34.0, 15.0, 38.0, control_loop="PIC-301"),

        "TT-401": Instrument("TT-401", "Shift Converter Outlet T", "R-301 HT/LT Shift", "Temperature", "°C", 0, 500, 220.0, 180.0, 280.0, 150.0, 310.0),
        "A-401": Instrument("A-401", "CO2 Absorber CO2 Concentration", "A-401 Absorber", "Concentration", "%", 0, 20, 0.1, 0.0, 0.5, 0.0, 2.0),
        "A-402": Instrument("A-402", "Methanator CO+CO2 Conc", "R-401 Methanator", "Concentration", "ppm", 0, 100, 5.0, 0.0, 20.0, 0.0, 50.0),

        "PT-501": Instrument("PT-501", "Compressor Discharge Press", "C-501 Syn Gas Compressor", "Pressure", "bar", 0, 250, 180.0, 140.0, 210.0, 120.0, 225.0),
        "TT-501": Instrument("TT-501", "Compressor Discharge Temp", "C-501 Syn Gas Compressor", "Temperature", "°C", 0, 250, 140.0, 80.0, 170.0, 60.0, 185.0),

        "TT-601": Instrument("TT-601", "Ammonia Converter Temp", "R-501 Ammonia Converter", "Temperature", "°C", 0, 600, 480.0, 400.0, 520.0, 350.0, 550.0, control_loop="TIC-601"),
        "PT-601": Instrument("PT-601", "Ammonia Converter Press", "R-501 Ammonia Converter", "Pressure", "bar", 0, 250, 175.0, 135.0, 200.0, 115.0, 215.0, control_loop="PIC-601"),
        
        "LT-601": Instrument("LT-601", "Separator Level", "V-601 Separator", "Level", "%", 0, 100, 50.0, 20.0, 80.0, 10.0, 90.0, control_loop="LIC-601"),
        "FT-701": Instrument("FT-701", "Ammonia Product Flow", "Product Storage", "Flow", "t/h", 0, 100, 45.0, 20.0, 70.0, 10.0, 80.0, control_loop="FIC-701"),
    }
