class User:
    def __init__(self, id, username, role, full_name):
        self.id = id
        self.username = username
        self.role = role
        self.full_name = full_name

    def is_admin(self):
        return self.role == "admin"

    def is_teacher(self):
        return self.role == "enseignant"

    def is_student(self):
        return self.role == "etudiant"
