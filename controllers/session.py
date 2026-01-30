current_user = None

def login_user(user):
    global current_user
    current_user = user

def logout_user():
    global current_user
    current_user = None
