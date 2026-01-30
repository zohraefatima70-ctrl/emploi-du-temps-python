class Room:
    def __init__(self, id, name, room_type, capacity, equipments):
        self.id = id
        self.name = name
        self.room_type = room_type
        self.capacity = capacity
        self.equipments = equipments.split(",") if equipments else []

    def has_equipment(self, equipment):
        return equipment in self.equipments
