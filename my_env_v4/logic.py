import random

class HospitalEngine:
    def __init__(self):
        # Initial State: 3 Wards, 4 staff each, some patients
        self.wards = [
            {"name": "ICU", "patient_count": 5, "staff_count": 4, "fatigue": 0.1},
            {"name": "ER", "patient_count": 10, "staff_count": 4, "fatigue": 0.1},
            {"name": "General", "patient_count": 20, "staff_count": 4, "fatigue": 0.1}
        ]
        self.time_step = 0

    def apply_surge(self):
        # Every 10 steps, a massive influx happens
        if self.time_step > 0 and self.time_step % 10 == 0:
            surge_patients = random.randint(15, 25)
            # Surge hits the ER first
            self.wards[1]["patient_count"] += surge_patients
            return True
        return False

    def step(self, action):
        self.time_step += 1
        
        # 1. Move Staff based on AI action
        source = action["source_ward"]
        target = action["target_ward"]
        count = action["staff_count"]
        
        if self.wards[source]["staff_count"] >= count:
            self.wards[source]["staff_count"] -= count
            self.wards[target]["staff_count"] += count

        # 2. Random Patient Arrivals + Surge
        self.apply_surge()
        for ward in self.wards:
            ward["patient_count"] += random.randint(-2, 5)
            ward["patient_count"] = max(0, ward["patient_count"])

        # 3. Calculate Pressure and Fatigue
        total_p = sum(w["patient_count"] for w in self.wards)
        total_s = sum(w["staff_count"] for w in self.wards)
        pressure = min(1.0, total_p / (total_s * 10))

        # Update Fatigue based on workload
        for ward in self.wards:
            workload = ward["patient_count"] / (ward["staff_count"] * 10 + 0.1)
            ward["fatigue"] = min(1.0, ward["fatigue"] + (workload * 0.01))

        reward = 1.0 - pressure
        terminated = pressure > 0.9 # Game over if pressure is too high
        
        return self.wards, reward, terminated, pressure