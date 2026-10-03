import numpy as np

class AmmoniaPlantModel:
    def __init__(self):
        # Internal Process State (Real Physical Values)
        self.state = {
            "feed_flow": 100.0,          # t/h
            "feed_pressure": 30.0,        # bar
            "feed_temp": 25.0,            # °C
            "steam_flow": 220.0,          # t/h
            "steam_carbon_ratio": 3.0,
            "furnace_temp": 850.0,        # °C
            "reformer_outlet_temp": 800.0,# °C
            "reformer_pressure": 28.0,    # bar
            "methane_conversion": 68.0,   # %
            "air_flow": 110.0,            # t/h
            "sec_reformer_temp": 980.0,   # °C
            "sec_reformer_press": 27.5,   # bar
            "shift_outlet_temp": 220.0,   # °C
            "co2_absorber_co2": 0.1,      # %
            "methanator_co_co2": 5.0,     # ppm
            "compressor_press": 180.0,    # bar
            "compressor_temp": 140.0,     # °C
            "reactor_temp": 480.0,        # °C
            "reactor_press": 175.0,       # bar
            "separator_level": 50.0,      # %
            "ammonia_flow": 45.0,         # t/h
            "furnace_trip": False,
            "compressor_trip": False,
            "cooling_failure": False,
        }

    def step(self, controllers: dict, dt: float = 1.0):
        # Retrieve actuator settings from controllers
        fic101_v = controllers["FIC-101"].output / 100.0
        tic201_v = controllers["TIC-201"].output / 100.0
        pic301_v = controllers["PIC-301"].output / 100.0
        tic601_v = controllers["TIC-601"].output / 100.0
        pic601_v = controllers["PIC-601"].output / 100.0
        lic601_v = controllers["LIC-601"].output / 100.0
        fic701_v = controllers["FIC-701"].output / 100.0

        # Noise generator
        noise = lambda scale: float(np.random.normal(0, scale))

        # 1. Feed Gas & Steam Dynamics
        self.state["feed_flow"] = max(0.0, 120.0 * fic101_v + noise(0.2))
        self.state["feed_pressure"] = max(0.0, 35.0 - (self.state["feed_flow"] * 0.05) + noise(0.1))
        self.state["steam_flow"] = max(0.0, self.state["feed_flow"] * 2.2 + noise(0.3))
        self.state["steam_carbon_ratio"] = round(self.state["steam_flow"] / max(1.0, self.state["feed_flow"] * 0.7), 2)

        # 2. Primary Reformer Furnace Dynamics
        if self.state["furnace_trip"]:
            target_furnace_temp = 150.0
        else:
            target_furnace_temp = 600.0 + (500.0 * tic201_v) - (self.state["feed_flow"] * 1.2)
        
        self.state["furnace_temp"] += (target_furnace_temp - self.state["furnace_temp"]) * 0.1 + noise(0.3)
        self.state["reformer_outlet_temp"] = self.state["furnace_temp"] - 50.0 + noise(0.2)
        self.state["reformer_pressure"] = max(0.0, 32.0 - (pic301_v * 8.0) + noise(0.1))
        self.state["methane_conversion"] = max(10.0, min(95.0, (self.state["reformer_outlet_temp"] / 11.5) + noise(0.2)))

        # 3. Secondary Reformer
        self.state["air_flow"] = max(0.0, self.state["feed_flow"] * 1.1 + noise(0.2))
        self.state["sec_reformer_temp"] = self.state["reformer_outlet_temp"] + (self.state["air_flow"] * 1.6) + noise(0.4)
        self.state["sec_reformer_press"] = self.state["reformer_pressure"] - 0.5

        # 4. Shift & Methanation Gas Quality
        self.state["shift_outlet_temp"] = 200.0 + (self.state["sec_reformer_temp"] * 0.02) + noise(0.1)
        if self.state["reformer_outlet_temp"] < 750:
            self.state["co2_absorber_co2"] = min(5.0, self.state["co2_absorber_co2"] + 0.05)
            self.state["methanator_co_co2"] = min(80.0, self.state["methanator_co_co2"] + 1.2)
        else:
            self.state["co2_absorber_co2"] = max(0.05, 0.1 + noise(0.01))
            self.state["methanator_co_co2"] = max(2.0, 5.0 + noise(0.2))

        # 5. SynGas Compressor Dynamics
        if self.state["compressor_trip"]:
            target_comp_press = 10.0
        else:
            target_comp_press = 100.0 + (self.state["feed_flow"] * 0.9) - (pic601_v * 15.0)
        
        self.state["compressor_press"] += (target_comp_press - self.state["compressor_press"]) * 0.2 + noise(0.3)
        self.state["compressor_temp"] = 40.0 + (self.state["compressor_press"] * 0.55) + noise(0.2)

        # 6. Ammonia Converter Loop Dynamics
        cool_effect = 120.0 if self.state["cooling_failure"] else 0.0
        target_rx_temp = 350.0 + (180.0 * (1.0 - tic601_v)) + cool_effect + (self.state["compressor_press"] * 0.3)
        self.state["reactor_temp"] += (target_rx_temp - self.state["reactor_temp"]) * 0.08 + noise(0.3)
        self.state["reactor_press"] = self.state["compressor_press"] - 5.0 + noise(0.2)

        # Synthesis conversion efficiency curves (Bell curve centered around 470°C)
        rx_temp = self.state["reactor_temp"]
        eff = max(0.05, np.exp(-((rx_temp - 470.0) ** 2) / 4000.0))
        max_possible_nh3 = (self.state["feed_flow"] * 0.5) * (self.state["reactor_press"] / 175.0) * eff
        
        # 7. Separator & Product Flow Dynamics
        net_prod = max_possible_nh3 - (fic701_v * 50.0)
        self.state["separator_level"] = max(0.0, min(100.0, self.state["separator_level"] + (net_prod * 0.1)))
        self.state["ammonia_flow"] = max(0.0, (lic601_v * 0.6 + fic701_v * 0.4) * max_possible_nh3 + noise(0.2))

    def update_instrument_objects(self, instruments: dict):
        # Synchronize real physics into instrument telemetry pipeline
        mapping = {
            "FT-101": "feed_flow", "PT-101": "feed_pressure", "TT-101": "feed_temp",
            "FT-201": "steam_flow", "TT-201": "furnace_temp", "TT-202": "reformer_outlet_temp",
            "PT-201": "reformer_pressure", "FT-301": "air_flow", "TT-301": "sec_reformer_temp",
            "PT-301": "sec_reformer_press", "TT-401": "shift_outlet_temp", "A-401": "co2_absorber_co2",
            "A-402": "methanator_co_co2", "PT-501": "compressor_press", "TT-501": "compressor_temp",
            "TT-601": "reactor_temp", "PT-601": "reactor_press", "LT-601": "separator_level",
            "FT-701": "ammonia_flow"
        }
        for tag, state_key in mapping.items():
            if tag in instruments:
                real_val = self.state[state_key]
                instruments[tag].update_indicated_value(real_val)
