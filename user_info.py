from datetime import datetime
class UserInfo:
    def __init__(self, username, pronoun=None, email=None, bio=None, join_date=None):
        self.username = username
        self.pronoun = pronoun
        self.email = email
        self.join_date = join_date if join_date else datetime.now()
        self.bio = bio

    def get_username(self):
        return self.username
    
    def get_pronoun(self):
        return self.pronoun

    def get_email(self):
        return self.email

    def get_join_date(self):
        return self.join_date.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_bio(self):
        return self.bio
    
    def set_username(self, username):
        if username != "":
            self.username = username    

    def set_pronoun(self, pronoun):
        if pronoun != "":
            self.pronoun = pronoun  
    
    def set_email(self, email):
        if email != "":
            self.email = email

    def set_bio(self, bio):
        if bio != "":
            self.bio = bio

    def __str__(self):
        return (f"Username: {self.username}\n"
                f"Pronoun: {self.pronoun or 'N/A'}\n"
                f"Email: {self.email or 'N/A'}\n"
                f"Join Date: {self.get_join_date()}\n"
                f"Bio: {self.bio or 'N/A'}\n")
    
    # Serialize user info to a dictionary   
    # ability to easily convert to JSON if needed
    def to_dict(self):
        return {
            "username": self.username,
            "pronoun": self.pronoun,
            "email": self.email,
            "join_date": self.get_join_date(),
            "bio": self.bio
        }