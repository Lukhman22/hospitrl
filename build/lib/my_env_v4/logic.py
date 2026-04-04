import random

class Ward:
    def __init__(self, name, patients, staff):
        self.name = name
        self.patient_count = patients
        self.staff_count = staff
        self.fatigue = 0.1

    def update(self):
        self.patient_count += random.randint(-2, 5)
        self.patient_count = max(0, self.patient_count)
        if self.staff_count > 0:
            pressure = self.patient_count / self.staff_count
            self.fatigue += pressure * 0.01
        self.fatigue = min(1.0, self.fatigue)

class HospitalEngine:
    def __init__(self):
        self.wards = {
            "ICU": Ward("ICU", 5, 4),
            "ER": Ward("ER", 10, 4),
            "General": Ward("General", 20, 4)
        }
        self.hospital_pressure = 0.5

    def move_staff(self, source_name, target_name, count):
        if source_name in self.wards and target_name in self.wards:
            actual_move = min(count, self.wards[source_name].staff_count)
            self.wards[source_name].staff_count -= actual_move
            self.wards[target_name].staff_count += actual_move

    def update(self):
        total_p = 0
        total_s = 0
        for ward in self.wards.values():
            ward.update()
            total_p += ward.patient_count
            total_s += ward.staff_count
        
        if total_s > 0:
            self.hospital_pressure = min(1.0, total_p / (total_s * 10))
        else:
            self.hospital_pressure = 1.0