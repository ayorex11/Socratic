from django.contrib.auth.tokens import PasswordResetTokenGenerator
from six import text_type

class StaticTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # We rely on stable fields: PK, password hash, is_active, and date_joined
        return (
            text_type(user.pk) + text_type(user.password) 
            + text_type(user.is_active) + text_type(user.date_joined)
        )

custom_token_generator = StaticTokenGenerator()