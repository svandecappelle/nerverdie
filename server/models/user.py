from peewee import CharField, DoesNotExist
from werkzeug.security import check_password_hash, generate_password_hash

from server.models.base import BaseModel

# Hash checked when the username is unknown, so that response time does
# not reveal whether an account exists.
_DUMMY_HASH = generate_password_hash('neverdie-dummy-password')


class User(BaseModel):
    username = CharField(unique=True)
    password_hash = CharField(null=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @classmethod
    def authenticate(cls, username, password):
        """Return the matching user, or None if the credentials are invalid."""
        if not isinstance(username, str) or not isinstance(password, str):
            return None
        try:
            user = cls.get(cls.username == username)
        except DoesNotExist:
            check_password_hash(_DUMMY_HASH, password)
            return None
        return user if user.check_password(password) else None
