class Instructor:
    def __init__(self, id, user_id, name, speciality, unavailable_slots):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.speciality = speciality
        self.unavailable_slots = unavailable_slots.split(",") if unavailable_slots else []

    def is_available(self, day, hour):
        slot = f"{day}_{hour}"
        return slot not in self.unavailable_slots
