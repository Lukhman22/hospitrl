import numpy as np

class HospitalEngine:
    def __init__(self):
        self.wards = ['ICU', 'ER', 'General']
        self.patient_counts = {'ICU': 5, 'ER': 10, 'General': 20}
        self.staff_assigned = {'ICU': 4, 'ER': 4, 'General': 4}
        self.staff_fatigue = {'ICU': 0.1, 'ER': 0.1, 'General': 0.1}

    def move_staff(self, source: str, target: str, count: int):
        if self.staff_assigned[source] >= count:
            self.staff_assigned[source] -= count
            self.staff_assigned[target] += count

    def update_state(self):
        for ward in self.wards:
            # Patients arrive (Poisson)
            arrival = np.random.poisson(0.5)
            self.patient_counts[ward] += arrival
            # Fatigue increases
            self.staff_fatigue[ward] = min(1.0, self.staff_fatigue[ward] + 0.05)

    def get_safety_ratio(self, ward: str) -> float:
        if self.patient_counts[ward] == 0: return 1.0
        return self.staff_assigned[ward] / self.patient_counts[ward]