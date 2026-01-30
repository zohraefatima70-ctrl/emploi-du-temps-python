class TimetableSlot:
    def __init__(self, id, course_id, instructor_id, group_id, room_id, day, start_hour, duration):
        self.id = id
        self.course_id = course_id
        self.instructor_id = instructor_id
        self.group_id = group_id
        self.room_id = room_id
        self.day = day
        self.start_hour = start_hour
        self.duration = duration

    def get_end_hour(self):
        return self.start_hour + self.duration
