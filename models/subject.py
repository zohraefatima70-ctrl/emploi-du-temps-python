class Subject:
    def __init__(self, id, name, code, hours_total, subject_type, required_equipment):
        self.id = id
        self.name = name
        self.code = code
        self.hours_total = hours_total
        self.subject_type = subject_type
        self.required_equipment = required_equipment.split(",") if required_equipment else []
